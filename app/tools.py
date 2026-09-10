"""
tools.py -- the agent's tools, now including RAG search over your own documents.

This is what "agentic RAG" actually means in practice: the agent has a
choice between multiple tools, and decides which one fits the question --
searching your indexed documents, searching the live web, or doing exact
math -- rather than only ever doing one of those things.
"""

import ast
import operator

from ddgs import DDGS

from app.embed_store import search as vector_search

# ---------------------------------------------------------------------------
# Tool 1: calculator (safe AST-based evaluation, never raw eval())
# ---------------------------------------------------------------------------
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def calculator(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree.body))
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


# ---------------------------------------------------------------------------
# Tool 2: web search
# ---------------------------------------------------------------------------
def web_search(query: str, max_results: int = 4) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        return "\n".join(
            f"- {r.get('title', 'Untitled')}: {r.get('body', '')} ({r.get('href', '')})"
            for r in results
        )
    except Exception as e:
        return f"Search failed: {e}"


# ---------------------------------------------------------------------------
# Tool 3: search your own documents (the RAG piece)
# ---------------------------------------------------------------------------
def search_thesis(query: str) -> str:
    try:
        results = vector_search(query, k=4)
        if not results:
            return "No relevant chunks found in the indexed documents."
        return "\n\n".join(
            f"[{r['source']}, score={r['score']:.2f}]\n{r['text']}" for r in results
        )
    except FileNotFoundError:
        return "The document index hasn't been built yet."


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a basic arithmetic expression. Supports +, -, *, /, ** and parentheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "A math expression, e.g. '15 * 0.2'"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web for current information not found in the indexed documents.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_thesis",
            "description": "Search the indexed documents (e.g. the user's thesis or uploaded files) for relevant passages. Use this first for any question that could be about the user's own documents.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "What to search for in the documents."}},
                "required": ["query"],
            },
        },
    },
]

FUNCTION_MAP = {
    "calculator": calculator,
    "web_search": web_search,
    "search_thesis": search_thesis,
}
