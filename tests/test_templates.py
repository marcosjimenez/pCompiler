import pytest
from pcompiler.templates import TemplateEngine
from jinja2 import UndefinedError

@pytest.fixture
def engine():
    return TemplateEngine()

def test_render_simple(engine):
    template = "Hello {{ name }}!"
    context = {"name": "World"}
    assert engine.render(template, context) == "Hello World!"

def test_render_loop(engine):
    template = "{% for item in items %}- {{ item }}\n{% endfor %}"
    context = {"items": ["apple", "banana", "cherry"]}
    expected = "- apple\n- banana\n- cherry\n"
    assert engine.render(template, context) == expected

def test_render_conditional(engine):
    template = "{% if active %}Active{% else %}Inactive{% endif %}"
    assert engine.render(template, {"active": True}) == "Active"
    assert engine.render(template, {"active": False}) == "Inactive"

def test_missing_variable(engine):
    template = "Hello {{ name }}!"
    with pytest.raises(UndefinedError):
        engine.render(template, {})

def test_syntax_error(engine):
    template = "{% if active %} missing endif"
    with pytest.raises(Exception): # Jinja2 raises TemplateSyntaxError
        engine.render(template, {"active": True})
