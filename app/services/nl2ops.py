
import os, json
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from .schema import resolve_columns

SYSTEM = """You convert a user message into ONE JSON operation.
Output ONLY a single JSON object. Supported operations:

{"op":"total",        "col":"<numeric_col>", "time":{"col":"<date_col>","window":"this_month|last_month|last_7d|last_30d|last_90d|ytd"}?, "filter":{"column":"<col>","equals":"<value>" }?}
{"op":"average",      "col":"<numeric_col>", "time":{...}?, "filter":{...}?}
{"op":"count",        "col":"<quantity_or_any_col>", "time":{...}?, "filter":{...}?}  // use for "how many"
{"op":"group_sum",    "by":"<category_col>", "col":"<numeric_col>", "time":{...}?, "filter":{...}?, "topk": N?}
{"op":"group_count",  "by":"<category_col>", "col":"<col_to_count>", "time":{...}?, "filter":{...}?, "topk": N?}
{"op":"top_by_sum",   "by":"<category_col>", "col":"<numeric_col>", "time":{...}?, "filter":{...}?, "k": N}
{"op":"top_by_count", "by":"<category_col>", "col":"<col_to_count>", "time":{...}?, "filter":{...}?, "k": N}
{"op":"latest",       "col":"<numeric_col>", "by":"<date_col>"}
{"op":"chat"}  // greetings/thanks/general talk

Rules:
- If the user mentions a PRODUCT or REGION, include {"filter":{"column":..., "equals":...}}.
- For “how many…”, prefer {"op":"count"} using a quantity column when available; else count rows.
- For “which region/product … most”, use {"op":"top_by_count"} or {"op":"top_by_sum"} depending on whether it’s about units (quantity) or revenue.
- Use only columns from the provided list.
- No prose, only JSON.
"""

def _llm():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key: raise RuntimeError("Missing OPENROUTER_API_KEY")
    return ChatOpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        model="mistralai/mixtral-8x7b-instruct",
        temperature=0.7
    )

def _first_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"): return json.loads(text)
    st = 0; start = -1
    for i,ch in enumerate(text):
        if ch == "{":
            if st == 0: start = i
            st += 1
        elif ch == "}":
            st -= 1
            if st == 0 and start != -1: return json.loads(text[start:i+1])
    return {"op":"chat"}

def to_op(user_query: str, columns: List[str]) -> Dict[str, Any]:
    roles = resolve_columns(columns)
    guidance = f"Columns: {columns}\nResolved roles: {roles}\nUser: {user_query}\nRespond ONLY with one JSON operation."
    out = _llm().invoke([SystemMessage(content=SYSTEM), HumanMessage(content=guidance)])
    try:
        return _first_json(out.content or "")
    except Exception:
        return {"op":"chat"}
