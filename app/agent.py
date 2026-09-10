"""
agent.py -- the agent loop: call the model, run any requested tools, repeat.

Same loop as learn-agents, now choosing between three tools instead of two.
"""

import json
import time

from groq import Groq

from app.tools import TOOLS, FUNCTION_MAP

client = Groq()  # reads GROQ_API_KEY from the environment
MODEL = "openai/gpt-oss-120b"
MAX_STEPS = 6

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to three tools: search_thesis "
    "for questions about the user's own indexed documents, web_search for "
    "current information not in those documents, and calculator for exact "
    "math. Try search_thesis first for anything that could be about the "
    "user's documents. Don't call a tool if you already know the answer "
    "with confidence. Respond directly once you have enough information."
)


def _create_completion(messages):
    """Retry transient provider failures instead of turning them into HTTP 500s."""
    last_error = None
    for attempt in range(3):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Language-model request failed after 3 attempts: {last_error}")


def run_agent(user_message: str, verbose: bool = False) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for step in range(1, MAX_STEPS + 1):
        response = _create_completion(messages)
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(message)

        for call in message.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            if verbose:
                print(f"[step {step}] calling {name}({args})")

            func = FUNCTION_MAP.get(name)
            try:
                result = func(**args) if func else f"Unknown tool: {name}"
            except Exception as exc:
                result = f"Tool {name} failed: {exc}"

            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return "I couldn't finish this within the step limit -- something may be looping."
