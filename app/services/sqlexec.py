
import duckdb, re
import pandas as pd
from typing import Tuple, Dict, Any

_ONLY_SELECT = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)

def run_sql(df: pd.DataFrame, sql: str) -> Tuple[pd.DataFrame, str]:
    sql = (sql or "").strip().rstrip(";")
    if not _ONLY_SELECT.match(sql):
        
        if "CHAT" in sql.upper():
            return pd.DataFrame([{"smalltalk":"CHAT"}]), sql
        raise ValueError("Only SELECT statements are allowed")

    con = duckdb.connect(database=':memory:')
    try:
        con.register("data", df)
        res = con.execute(sql).fetchdf()
        return res, sql
    finally:
        con.close()

def run_sql_with_retry(df: pd.DataFrame, sql: str, llm_rewrite) -> Tuple[pd.DataFrame, str]:
    try:
        return run_sql(df, sql)
    except Exception as e:
    
        fix = llm_rewrite(sql, str(e))
        return run_sql(df, fix)
