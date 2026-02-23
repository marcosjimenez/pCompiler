from pathlib import Path
import pytest
from pcompiler.compiler import PromptCompiler
from pcompiler.dsl.parser import parse_string

@pytest.fixture
def compiler():
    return PromptCompiler(enable_cache=False)

def test_static_context(compiler):
    yaml = """
task: test
context:
  sources:
    - type: static
      value: "This is static context."
"""
    result = compiler.compile_string(yaml)
    assert "This is static context." in result.prompt_text

def test_multiple_context_sources(compiler):
    yaml = """
task: test
context:
  sources:
    - type: static
      value: "Context A"
      priority: 100
    - type: static
      value: "Context B"
      priority: 50
"""
    result = compiler.compile_string(yaml)
    assert "Context A" in result.prompt_text
    assert "Context B" in result.prompt_text
    # Check ordering if possible - by default it joins with \n\n
    assert result.prompt_text.find("Context A") < result.prompt_text.find("Context B")

def test_local_file_context(compiler, tmp_path):
    context_file = tmp_path / "context.txt"
    context_file.write_text("Context from file.")
    file_path = str(context_file).replace('\\', '/')
    
    yaml = f"""
task: test
context:
  sources:
    - type: local_file
      value: "{file_path}"
"""
    result = compiler.compile_string(yaml)
    assert "Context from file." in result.prompt_text

def test_context_pruning_approximation(compiler):
    # max_total_tokens = 10, so char limit approx 40
    long_context = "A" * 1000
    yaml = f"""
task: test
context:
  sources:
    - type: static
      value: "{long_context}"
  max_total_tokens: 10
"""
    result = compiler.compile_string(yaml)
    # The whole prompt will be > 100 due to system messages, etc.
    # But the long_context should definitely be truncated.
    assert long_context not in result.prompt_text
    assert "..." in result.prompt_text
    # Check that some of it is there
    assert "AAAAA" in result.prompt_text

def test_vector_store_retrieval(compiler):
    yaml = """
task: test
context:
  sources:
    - type: vector_store
      query: "How to use pCompiler?"
"""
    result = compiler.compile_string(yaml)
    assert "[Mock Context for: How to use pCompiler?]" in result.prompt_text
