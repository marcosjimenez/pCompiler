"""
Main prompt compiler orchestrator.

Wires together the full pipeline:
  DSL → IR → Analysis → Optimization → Backend Plugin → CompiledPrompt

Usage::

    from pcompiler.compiler import PromptCompiler

    compiler = PromptCompiler()
    result = compiler.compile_file("my_prompt.yaml")
    print(result.prompt_text)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pcompiler import __version__
from pcompiler.analysis.ambiguity import AmbiguityReport, analyze_ambiguity
from pcompiler.analysis.contradiction import ContradictionReport, detect_contradictions
from pcompiler.analysis.injection import InjectionReport, analyze_injection_risk
from pcompiler.analysis.schema_validator import SchemaValidationResult, validate_output_schema
from pcompiler.dsl.examples import get_task_template
from pcompiler.dsl.parser import parse_file, parse_string
from pcompiler.dsl.schema import PromptSpec, SecurityLevel
from pcompiler.ir.nodes import PromptIR, SectionKind
from pcompiler.models.registry import ModelProfile, ModelRegistry
from pcompiler.observability.tracer import CompilationTrace
from pcompiler.observability.versioning import compute_hash, create_version
from pcompiler.optimizer.cache import PromptCache
from pcompiler.optimizer.compress import compress
from pcompiler.optimizer.cot import insert_chain_of_thought
from pcompiler.optimizer.reorder import reorder_sections
from pcompiler.plugins.base import CompiledPrompt, PluginManager
from pcompiler.security.policies import build_policy_set, policy_to_system_lines
from pcompiler.security.sanitizer import build_system_boundary, wrap_user_input
from pcompiler.context_manager import ContextManager


# ---------------------------------------------------------------------------
# Analysis bundle
# ---------------------------------------------------------------------------

class AnalysisResults:
    """Container for all static analysis results."""

    def __init__(
        self,
        ambiguity: AmbiguityReport,
        contradictions: ContradictionReport,
        schema: SchemaValidationResult,
        injection: InjectionReport,
    ) -> None:
        self.ambiguity = ambiguity
        self.contradictions = contradictions
        self.schema = schema
        self.injection = injection

    @property
    def has_errors(self) -> bool:
        return (
            not self.schema.valid
            or any(c.severity == "error" for c in self.contradictions.contradictions)
        )

    @property
    def all_warnings(self) -> list[str]:
        msgs: list[str] = []
        for w in self.ambiguity.warnings:
            msgs.append(f"[ambiguity] {w.section}: {w.message}")
        for c in self.contradictions.contradictions:
            msgs.append(f"[contradiction] {c.message}")
        for e in self.schema.errors:
            msgs.append(f"[schema] {e}")
        for w in self.schema.warnings:
            msgs.append(f"[schema] {w}")
        for f in self.injection.findings:
            msgs.append(f"[injection:{f.risk.value}] {f.pattern_name}: {f.suggestion}")
        return msgs


# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

class PromptCompiler:
    """Main compiler class — orchestrates the full pipeline."""

    def __init__(
        self,
        *,
        plugin_manager: PluginManager | None = None,
        cache: PromptCache | None = None,
        enable_cache: bool = True,
    ) -> None:
        self.registry = ModelRegistry()
        self.plugins = plugin_manager or PluginManager()
        self.cache = cache or (PromptCache() if enable_cache else None)
        self.context_manager = ContextManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile_file(
        self,
        path: str | Path,
        *,
        target: str | None = None,
    ) -> CompiledPrompt:
        """Compile a DSL file into a model-specific prompt."""
        spec = parse_file(path)
        return self.compile(spec, target=target)

    def compile_string(
        self,
        yaml_str: str,
        *,
        target: str | None = None,
    ) -> CompiledPrompt:
        """Compile a YAML string."""
        spec = parse_string(yaml_str)
        return self.compile(spec, target=target)

    def compile(
        self,
        spec: PromptSpec,
        *,
        target: str | None = None,
    ) -> CompiledPrompt:
        """Run the full compilation pipeline on a PromptSpec."""
        model_target = target or spec.model_target
        spec_dict = spec.model_dump(mode="json")

        # --- Cache check ---
        if self.cache:
            key = self.cache.make_key(spec_dict, model_target)
            cached = self.cache.get(key)
            if cached is not None:
                return cached

        # --- Trace ---
        trace = CompilationTrace(
            spec_hash=compute_hash(spec_dict),
            model_target=model_target,
            compiler_version=__version__,
        )

        # --- 1. Resolve model profile ---
        step = trace.start_step("resolve", "Resolving model profile")
        profile = self.registry.get(model_target)
        trace.end_step(step)

        # --- 2. Build IR ---
        step = trace.start_step("ir_build", "Building intermediate representation")
        ir = self._build_ir(spec, profile)
        trace.end_step(step)

        # --- 3. Static analysis ---
        step = trace.start_step("analysis", "Running static analysis")
        analysis = self.analyze(spec, profile, ir)
        for w in analysis.all_warnings:
            trace.add_warning(w)
        trace.end_step(step)

        # --- 4. Optimization ---
        step = trace.start_step("optimization", "Applying optimizations")
        ir = self._optimize(ir, spec, profile)
        trace.end_step(step)

        # --- 5. Backend emission ---
        step = trace.start_step("emit", f"Emitting via plugin for {model_target}")
        plugin = self.plugins.get_plugin_for_model(model_target)
        result = plugin.emit(ir, profile)
        trace.end_step(step)

        # Attach trace & warnings
        result.trace = trace.to_dict()
        result.warnings.extend(analysis.all_warnings)

        # --- Cache store ---
        if self.cache:
            self.cache.put(key, result)

        return result

    def analyze(
        self,
        spec: PromptSpec,
        profile: ModelProfile | None = None,
        ir: PromptIR | None = None,
    ) -> AnalysisResults:
        """Run all static analyses without compiling."""
        if profile is None:
            profile = self.registry.get(spec.model_target)
        if ir is None:
            ir = self._build_ir(spec, profile)

        ambiguity = analyze_ambiguity(ir)
        contradictions = detect_contradictions(spec)
        schema = validate_output_schema(spec.output_schema, profile)

        # Injection analysis on user input template and instructions
        texts_to_scan = []
        if spec.user_input_template:
            texts_to_scan.append(spec.user_input_template)
        for instr in spec.instructions:
            texts_to_scan.append(instr.text)
        injection = analyze_injection_risk(*texts_to_scan) if texts_to_scan else InjectionReport()

        return AnalysisResults(
            ambiguity=ambiguity,
            contradictions=contradictions,
            schema=schema,
            injection=injection,
        )

    def validate_file(self, path: str | Path) -> AnalysisResults:
        """Parse and validate a DSL file (analysis only, no compilation)."""
        spec = parse_file(path)
        return self.analyze(spec)

    # ------------------------------------------------------------------
    # Internal pipeline stages
    # ------------------------------------------------------------------

    def _build_ir(self, spec: PromptSpec, profile: ModelProfile) -> PromptIR:
        """Convert a PromptSpec into the IR."""
        ir = PromptIR(task=spec.task, model_target=profile.name)

        # Metadata for downstream use
        ir.metadata["output_schema"] = (
            spec.output_schema.model_dump(mode="json") if spec.output_schema else None
        )
        if spec.constraints.temperature is not None:
            ir.metadata["temperature"] = spec.constraints.temperature
        else:
            ir.metadata["temperature"] = profile.default_temperature
        if spec.constraints.top_p is not None:
            ir.metadata["top_p"] = spec.constraints.top_p
        else:
            ir.metadata["top_p"] = profile.default_top_p
        if spec.constraints.max_tokens:
            ir.metadata["max_tokens"] = spec.constraints.max_tokens

        # --- Security preamble ---
        policy_set = build_policy_set(spec.security)
        policy_lines = policy_to_system_lines(policy_set)
        if policy_lines:
            ir.add(SectionKind.SECURITY_PREAMBLE, "\n".join(policy_lines), priority=100)

        # --- System prompt (from task template if available) ---
        template = get_task_template(spec.task)
        system_parts: list[str] = []
        if template:
            system_text = template.system_prompt
            if spec.security.level != SecurityLevel.PERMISSIVE:
                system_text = build_system_boundary(system_text, spec.security.level)
            system_parts.append(system_text)

        if spec.description:
            system_parts.append(f"Task description: {spec.description}")

        tone_msg = f"Use a {spec.constraints.tone.value} tone in your response."
        system_parts.append(tone_msg)

        if system_parts:
            ir.add(SectionKind.SYSTEM, "\n\n".join(system_parts), priority=90)

        # --- Context ---
        if spec.context:
            resolved_context = self.context_manager.resolve_context(spec.context)
            if resolved_context:
                ir.add(SectionKind.CONTEXT, resolved_context, priority=70)

        # --- Instructions ---
        # From task template defaults
        if template:
            for instr_text in template.default_instructions:
                ir.add(SectionKind.INSTRUCTIONS, instr_text, priority=50)

        # User-defined instructions (higher priority)
        for instr in sorted(spec.instructions, key=lambda i: i.priority, reverse=True):
            ir.add(SectionKind.INSTRUCTIONS, instr.text, priority=60 + instr.priority // 10)

        # --- Few-shot examples ---
        for ex in spec.few_shot_examples:
            content = f"Input: {ex.input}\nOutput: {ex.output}"
            if ex.explanation:
                content += f"\nExplanation: {ex.explanation}"
            ir.add(SectionKind.EXAMPLES, content, priority=45)

        # --- Output format ---
        if spec.output_schema:
            schema_json = json.dumps(
                {
                    "type": spec.output_schema.type,
                    "properties": spec.output_schema.properties,
                    "required": spec.output_schema.required,
                },
                indent=2,
            )
            ir.add(
                SectionKind.OUTPUT_FORMAT,
                f"Respond with valid JSON matching this schema:\n```json\n{schema_json}\n```",
                priority=55,
            )

        # Extra flags
        extras: list[str] = []
        if spec.constraints.include_risks:
            extras.append("Include a risk assessment in your response.")
        if spec.constraints.include_citations:
            extras.append("Cite your sources.")
        if spec.constraints.include_confidence:
            extras.append("Include a confidence score (0-100) for your answer.")
        if extras:
            ir.add(SectionKind.INSTRUCTIONS, "\n".join(extras), priority=55)

        # --- User input template ---
        if spec.user_input_template:
            user_text = spec.user_input_template
            if spec.security.level != SecurityLevel.PERMISSIVE:
                user_text = wrap_user_input(user_text, spec.security.level)
            ir.add(SectionKind.USER_INPUT, user_text, priority=30)

        return ir

    def _optimize(self, ir: PromptIR, spec: PromptSpec, profile: ModelProfile) -> PromptIR:
        """Apply all optimization passes."""

        # 1. Chain of thought insertion
        ir = insert_chain_of_thought(ir, spec.constraints.cot_policy, spec.task)

        # 2. Reorder sections
        ir = reorder_sections(ir, profile)

        # 3. Compress / deduplicate
        comp_result = compress(ir, profile)
        ir = comp_result.ir

        return ir
