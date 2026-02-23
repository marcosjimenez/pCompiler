"""
Compilation tracer.

Records every step of the compilation pipeline for auditing
and reproducibility.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TraceStep:
    """A single step in the compilation trace."""
    phase: str
    description: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompilationTrace:
    """Full trace of a compilation run."""

    spec_hash: str = ""
    model_target: str = ""
    compiler_version: str = ""
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    steps: list[TraceStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # -- Recording ---------------------------------------------------------

    def start_step(self, phase: str, description: str, **data: Any) -> TraceStep:
        """Begin recording a new step. Returns the step for timing."""
        step = TraceStep(phase=phase, description=description, data=data)
        self.steps.append(step)
        return step

    def end_step(self, step: TraceStep) -> None:
        """Mark a step as complete and record its duration."""
        step.duration_ms = round((time.time() - step.timestamp) * 1000, 2)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    # -- Export ------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the trace to a dict (for JSON export)."""
        return {
            "spec_hash": self.spec_hash,
            "model_target": self.model_target,
            "compiler_version": self.compiler_version,
            "started_at": self.started_at,
            "total_steps": len(self.steps),
            "total_warnings": len(self.warnings),
            "steps": [
                {
                    "phase": s.phase,
                    "description": s.description,
                    "duration_ms": s.duration_ms,
                    "data": s.data,
                }
                for s in self.steps
            ],
            "warnings": self.warnings,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def save(self, path: str | Path) -> None:
        """Write the trace to a JSON file."""
        Path(path).write_text(self.to_json(), encoding="utf-8")
