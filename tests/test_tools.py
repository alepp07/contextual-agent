"""
test_tools.py -- tests for the tools the agent can call.

Deliberately offline: no network calls, no API keys required. This is what
lets these run automatically in GitHub Actions on every push, for free,
without needing secrets configured in CI.
"""

from app.tools import calculator, TOOLS, FUNCTION_MAP


def test_calculator_basic_arithmetic():
    assert calculator("2 + 2") == "4"
    assert calculator("10 * 5") == "50"
    assert calculator("(3 + 2) * 4") == "20"


def test_calculator_rejects_unsafe_input():
    # Anything that isn't a number or a basic arithmetic operator should
    # fail safely -- never execute -- since this text can come from the
    # model itself, not just a trusted user.
    result = calculator("__import__('os').system('echo hi')")
    assert result.startswith("Error")


def test_calculator_rejects_non_numeric_constants():
    result = calculator("'a' + 'b'")
    assert result.startswith("Error")


def test_all_tools_have_matching_functions():
    # Every tool schema sent to the model must have a real function behind
    # it, or a tool call would silently do nothing.
    schema_names = {tool["function"]["name"] for tool in TOOLS}
    assert schema_names == set(FUNCTION_MAP.keys())


def test_tool_schemas_have_required_fields():
    for tool in TOOLS:
        fn = tool["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert "required" in fn["parameters"]
