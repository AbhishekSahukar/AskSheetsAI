import io, re
import pandas as pd
import pdfplumber

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r'[^a-z0-9_]+', '_', str(c).strip().lower()) for c in df.columns]
    return df

def read_any(file_bytes: bytes, filename: str):
    name = filename.lower()
    if name.endswith(".pdf"):
        best = None
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                for t in (page.extract_tables() or []):
                    if not t or len(t) < 2: continue
                    df = pd.DataFrame(t[1:], columns=t[0])
                    if best is None or df.size > best.size: best = df
        return (_normalize_df(best), "pdf") if best is not None else (pd.DataFrame(), "pdf")
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
        return _normalize_df(df), "excel"
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
        return _normalize_df(df), "csv"
