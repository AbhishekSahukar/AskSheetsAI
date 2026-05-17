import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM_PROMPT = """You are a friendly data assistant.
Write a concise, conversational answer (2–4 sentences) using ONLY the provided result data.
- Do not invent details that aren't in the result.
- If the result is a single number, explain what it represents.
- If the result is a grouped table, summarize the top items with their values.
"""


def _build_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model="minimax/minimax-m2.5",
        temperature=0.5,
    )


def narrate(question: str, sql: str, result: Any) -> str:
    """Turn a query result into a plain-English answer."""
    content = {
        "question": question,
        "sql_used": sql,
        "result": result,
    }
    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=str(content)),
    ])
    return response.content or "I wasn't able to produce a summary."