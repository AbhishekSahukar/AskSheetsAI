import re
from typing import Tuple

import duckdb
import pandas as pd

_SELECT_RE = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)


def run_sql(df: pd.DataFrame, sql: str) -> Tuple[pd.DataFrame, str]:
    sql = (sql or "").strip().rstrip(";")

    if not _SELECT_RE.match(sql):
        if "CHAT" in sql.upper():
            return pd.DataFrame([{"smalltalk": "CHAT"}]), sql
        raise ValueError("Only SELECT statements are allowed")

    con = duckdb.connect(database=":memory:")
    try:
        con.register("data", df)
        result = con.execute(sql).fetchdf()
        return result, sql
    finally:
        con.close()


def run_sql_with_retry(df: pd.DataFrame, sql: str, llm_rewrite) -> Tuple[pd.DataFrame, str]:
    """Run SQL, and if it fails, ask the LLM to fix it and try once more."""
    try:
        return run_sql(df, sql)
    except Exception as e:
        fixed_sql = llm_rewrite(sql, str(e))
        return run_sql(df, fixed_sql)