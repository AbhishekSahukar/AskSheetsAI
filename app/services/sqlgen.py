import os
import json
from typing import Dict

import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def _build_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="minimax/minimax-m2.5",
        temperature=temperature,
    )


def _schema_hint(df: pd.DataFrame) -> Dict[str, str]:
    """Map pandas dtypes to coarse SQL types for DuckDB guidance."""
    mapping = {}
    for col, dtype in df.dtypes.items():
        t = str(dtype).lower()
        if "datetime" in t or "date" in t:
            mapping[col] = "TIMESTAMP"
        elif any(x in t for x in ("int", "float", "double", "decimal")):
            mapping[col] = "NUMERIC"
        else:
            mapping[col] = "TEXT"
    return mapping


SYSTEM_PROMPT = """You generate exactly ONE DuckDB SQL SELECT query for a table named `data` based on the user's question.

Use ONLY columns from the provided SCHEMA. Check SAMPLE ROWS to infer each column's meaning.

Rules:
- Output raw SQL only — no prose, no backticks, no explanation.
- Only SELECT statements (no CREATE/INSERT/UPDATE/DELETE).
- Use ILIKE '%term%' for case-insensitive text matching.
- Cast text columns when needed: CAST(col AS DATE), CAST(col AS DOUBLE).
- For time phrases, use CURRENT_DATE with DATE_TRUNC / INTERVAL:
    this month  → DATE_TRUNC('month', CAST(col AS DATE)) = DATE_TRUNC('month', CURRENT_DATE)
    last month  → DATE_TRUNC('month', CAST(col AS DATE)) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH)
    last 30 days → CAST(col AS DATE) >= CURRENT_DATE - INTERVAL 30 DAY
    YTD         → CAST(col AS DATE) >= DATE_TRUNC('year', CURRENT_DATE)
- Add LIMIT 200 on detail queries, LIMIT 50 on grouped results.

Choosing the right measure column:
- For "total" / "summarize": prefer a NUMERIC column whose name suggests a metric
  (revenue, amount, sales, total, price, cost, qty, quantity, score, salary, expense, balance).
- If multiple match, pick the most aggregate-sounding one.
- If none match, fall back to the first NUMERIC column.
- If no NUMERIC columns exist, return COUNT(*).

Small-talk detection:
- If the question is clearly unrelated to the data (greeting, chit-chat), return:
  SELECT 'CHAT' AS smalltalk;

Examples (columns are illustrative — use the actual schema):

Q: summarize the sales
SQL: SELECT COALESCE(SUM(revenue), 0) AS total FROM data;

Q: how many headphones were sold?
SQL: SELECT COALESCE(SUM(quantity), 0) AS total_units
     FROM data
     WHERE CAST(product AS TEXT) ILIKE '%headphones%';

Q: which region had the highest revenue this month?
SQL: SELECT region, SUM(revenue) AS total_revenue
     FROM data
     WHERE DATE_TRUNC('month', CAST(date AS DATE)) = DATE_TRUNC('month', CURRENT_DATE)
     GROUP BY region
     ORDER BY total_revenue DESC
     LIMIT 50;

Q: hi
SQL: SELECT 'CHAT' AS smalltalk;
"""


def _build_user_prompt(question: str, df: pd.DataFrame) -> str:
    schema = _schema_hint(df)
    samples = df.head(3).to_dict(orient="records")
    return (
        f"SCHEMA: {json.dumps(schema, ensure_ascii=False)}\n"
        f"SAMPLES: {json.dumps(samples, ensure_ascii=False)}\n"
        f"QUESTION: {question}\n"
        "Return ONLY the SQL:"
    )


def make_sql(question: str, df: pd.DataFrame) -> str:
    llm = _build_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(question, df)),
    ])
    return (response.content or "").strip()


def rewrite_sql_bad(original_sql: str, error_msg: str, df: pd.DataFrame) -> str:
    """Ask the LLM to fix a SQL query that failed with an error."""
    schema = _schema_hint(df)
    prompt = (
        f"The following DuckDB SQL query returned an error. Fix it and return ONLY the corrected SQL.\n\n"
        f"SCHEMA: {json.dumps(schema, ensure_ascii=False)}\n"
        f"COLUMNS: {list(df.columns)}\n\n"
        f"ORIGINAL SQL:\n{original_sql}\n\n"
        f"ERROR:\n{error_msg}"
    )
    llm = _build_llm(temperature=0)
    response = llm.invoke([HumanMessage(content=prompt)])
    return (response.content or "").strip()