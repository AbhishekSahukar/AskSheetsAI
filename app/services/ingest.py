import io
import re

import pandas as pd
import pdfplumber


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and slugify column names so SQL generation is predictable."""
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-z0-9_]+", "_", str(c).strip().lower())
        for c in df.columns
    ]
    return df


def read_any(file_bytes: bytes, filename: str):
    """
    Parse a CSV, Excel, or PDF file into a DataFrame.
    Returns (DataFrame, file_type_string).
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        best = None
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table or len(table) < 2:
                        continue
                    df = pd.DataFrame(table[1:], columns=table[0])
                    if best is None or df.size > best.size:
                        best = df
        if best is None:
            return pd.DataFrame(), "pdf"
        return _normalize_columns(best), "pdf"

    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
        return _normalize_columns(df), "excel"

    # Default: CSV
    df = pd.read_csv(io.BytesIO(file_bytes))
    return _normalize_columns(df), "csv"