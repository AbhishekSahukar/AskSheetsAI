
import os, json
from typing import List, Dict, Any
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage


def _llm(temp=0):
    return ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="mistralai/mixtral-8x7b-instruct",
        temperature=temp,
    )

def _schema_hint(df: pd.DataFrame) -> Dict[str, str]:
    """
    Map pandas dtypes to coarse SQL-ish types for DuckDB guidance.
    """
    mapping = {}
    for c, t in df.dtypes.items():
        st = str(t).lower()
        if "datetime" in st or "date" in st:
            mapping[c] = "TIMESTAMP"
        elif "int" in st or "float" in st or "double" in st or "decimal" in st:
            mapping[c] = "NUMERIC"
        else:
            mapping[c] = "TEXT"
    return mapping


SYSTEM = """You generate exactly ONE DuckDB SQL SELECT query for a table named data based on the user's question.

You MUST use ONLY columns that appear in the provided SCHEMA. You may look at the SAMPLE ROWS to infer meaning (e.g., which column looks like a date, amount, product, department, etc.). Your query must be valid DuckDB SQL.

General rules:
- Output ONLY the raw SQL (no prose, no backticks).
- Query the table named data.
- Use ONLY SELECT statements (no CREATE/INSERT/UPDATE/DELETE).
- Prefer robust text filters using ILIKE '%term%' for case-insensitive containment on TEXT.
- Cast text to appropriate types when needed (e.g., CAST(col AS DATE) / CAST(col AS DOUBLE)).
- For time phrases ("this month", "last month", "last 30 days", "YTD"), use CURRENT_DATE with DATE_TRUNC/INTERVAL.
  Examples:
    DATE_TRUNC('month', CAST(date_col AS DATE)) = DATE_TRUNC('month', CURRENT_DATE)   -- this month
    DATE_TRUNC('month', CAST(date_col AS DATE)) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL 1 MONTH)   -- last month
    CAST(date_col AS DATE) >= CURRENT_DATE - INTERVAL 30 DAY                              -- last 30 days
    CAST(date_col AS DATE) >= DATE_TRUNC('year', CURRENT_DATE)                            -- YTD
- Always include a LIMIT if the result could be large (e.g., detail lists or groupings), typically LIMIT 200.

Dynamic measure selection (NO hardcoding):
- If the user asks to "summarize" or "total" and there is at least one NUMERIC column, pick the most "measure-like" one.
- A "measure-like" column is NUMERIC and its name suggests metrics, e.g., contains one of:
  revenue, amount, sales, total, price, cost, qty, quantity, score, points, salary, expense, balance.
- If multiple such columns exist, choose the most global/aggregate-sounding one (e.g., revenue/amount/total before quantity/score).
- If none of the names match, fall back to the first NUMERIC column in schema order.
- If NO NUMERIC columns exist, do not fabricate numeric aggregations; instead return a row count (COUNT(*)) or a sensible grouping.

Time column selection (NO hardcoding):
- If a date-like column exists (TIMESTAMP type or a TEXT column whose SAMPLE ROWS look like dates), use it for time windows.
- If none exist and the user asks for a time window, ignore the window and still answer without time filtering.

Grouping:
- If the user asks "by X", group by a TEXT column that best matches X by name and/or sample values.
- When ranking (e.g., "top", "highest", "most"), order by an aggregate (SUM/COUNT/AVG) and LIMIT appropriately.

Small talk:
- Only if the message is clearly unrelated to the data (greetings, general chit-chat) return:
  SELECT 'CHAT' AS smalltalk;

Examples (do not assume these exact columns exist, they are illustrative):

Q: summarize the sales
SQL: SELECT COALESCE(SUM(revenue),0) AS total FROM data;

Q: how many headphones were sold?
SQL: SELECT COALESCE(SUM(quantity),0) AS total_units
     FROM data
     WHERE CAST(product AS TEXT) ILIKE '%headphones%';

Q: which region had the highest revenue this month?
SQL: SELECT region, SUM(revenue) AS total_revenue
     FROM data
     WHERE DATE_TRUNC('month', CAST(date AS DATE)) = DATE_TRUNC('month', CURRENT_DATE)
     GROUP BY region
     ORDER BY total_revenue DESC
     LIMIT 50;

Q: list customers in the west with outstanding balance > 1000
SQL: SELECT customer, balance
     FROM data
     WHERE CAST(region AS TEXT) ILIKE '%west%'
       AND CAST(balance AS DOUBLE) > 1000
     LIMIT 200;

Q: hi
SQL: SELECT 'CHAT' AS smalltalk;
"""

def _build_prompt(question: str, df: pd.DataFrame) -> str:
    schema = _schema_hint(df)
    
    samples = df.head(3).to_dict(orient="records")
    return (
        "SCHEMA: " + json.dumps(schema, ensure_ascii=False) + "\n"
        "SAMPLES: " + json.dumps(samples, ensure_ascii=False) + "\n"
        "QUESTION: " + question + "\n"
        "Return ONLY the SQL:"
    )

def make_sql(question: str, df: pd.DataFrame) -> str:
    out = _llm(temp=0).invoke([
        SystemMessage(content=SYSTEM),
        HumanMessage(content=_build_prompt(question, df))
    ])
    return (out.content or "").strip()


def rewrite_sql_bad(original_sql: str, error_msg: str, df: pd.DataFrame) -> str:
    schema = _schema_hint(df)
    prompt = f"""The following DuckDB SQL errored. Fix it and return ONLY corrected SQL.

SCHEMA: {json.dumps(schema, ensure_ascii=False)}
COLUMNS: {list(df.columns)}
ORIGINAL SQL:
{original_sql}

ERROR:
{error_msg}
"""
    out = _llm(temp=0).invoke([HumanMessage(content=prompt)])
    return (out.content or "").strip()
