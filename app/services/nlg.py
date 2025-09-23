
import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

def _llm(temp: float = 0.5):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("Missing OPENROUTER_API_KEY")
    return ChatOpenAI(
        api_key=key, base_url="https://openrouter.ai/api/v1",
        model="mistralai/mixtral-8x7b-instruct", temperature=temp
    )

PARA_SYSTEM = """You are a friendly data assistant.
Write a concise, conversational answer (2–5 sentences) using ONLY the provided RESULT rows or scalars.
- Do not invent details not present in the result.
- If the result is a single number, explain what it represents.
- If the result is a grouped table, summarize the top items explicitly with their values.
"""

def narrate(question: str, sql: str, rows_or_scalar: Any) -> str:
    llm = _llm()
    content = {
        "question": question,
        "sql_used": sql,
        "result": rows_or_scalar
    }
    out = llm.invoke([SystemMessage(content=PARA_SYSTEM), HumanMessage(content=str(content))])
    return out.content or "I wasn’t able to produce a textual summary."
