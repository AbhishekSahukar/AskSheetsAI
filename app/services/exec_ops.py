
import pandas as pd
from dateutil.relativedelta import relativedelta

def _mask(df, col, window):
    today = pd.Timestamp.today().normalize()
    if window == "this_month":
        start = today.replace(day=1); end = start + relativedelta(months=1)
    elif window == "last_month":
        end = today.replace(day=1); start = end - relativedelta(months=1)
    elif window == "last_7d":
        end = today + pd.Timedelta(days=1); start = end - pd.Timedelta(days=7)
    elif window == "last_30d":
        end = today + pd.Timedelta(days=1); start = end - pd.Timedelta(days=30)
    elif window == "last_90d":
        end = today + pd.Timedelta(days=1); start = end - pd.Timedelta(days=90)
    elif window == "ytd":
        start = today.replace(month=1, day=1); end = today + pd.Timedelta(days=1)
    else:
        return pd.Series(True, index=df.index)
    s = pd.to_datetime(df[col], errors="coerce")
    return (s >= start) & (s < end)

def _apply_time(df, t):
    if not t: return df
    col, win = t.get("col"), t.get("window")
    if col and win and col in df.columns:
        return df[_mask(df, col, win)]
    return df

def _apply_filter(df, f):
    if not f: return df
    col = f.get("column")
    if not col or col not in df.columns: return df
    if "equals" in f:
        val = f["equals"]
       
        if df[col].dtype == object:
            return df[df[col].astype(str).str.lower() == str(val).lower()]
        return df[df[col] == val]
    if "in" in f:
        vals = set([str(v).lower() for v in f["in"]])
        return df[df[col].astype(str).str.lower().isin(vals)]
    if "contains" in f:
        pat = str(f["contains"]).lower()
        return df[df[col].astype(str).str.lower().str.contains(pat, na=False)]
    return df

def execute(df: pd.DataFrame, op: dict):
    work = df.copy()
    work = _apply_time(work, op.get("time"))
    work = _apply_filter(work, op.get("filter"))

    op_type = (op.get("op") or "").lower()

    if op_type == "total":
        col = op.get("col")
        if col not in work.columns: return {"text":"Column not found."}
        val = pd.to_numeric(work[col], errors="coerce").sum(min_count=1)
        return {"text": f"Total {col}: {0 if pd.isna(val) else round(float(val),2)}"}

    if op_type == "average":
        col = op.get("col")
        if col not in work.columns: return {"text":"Column not found."}
        val = pd.to_numeric(work[col], errors="coerce").mean()
        return {"text": f"Average {col}: {0 if pd.isna(val) else round(float(val),2)}"}

    if op_type == "count":
        col = op.get("col")
        if col and col in work.columns:
          
            s = pd.to_numeric(work[col], errors="coerce")
            if s.notna().any():
                return {"text": f"Total {col}: {int(s.fillna(0).sum())}"}
        
        return {"text": f"Row count: {int(len(work))}"}

    if op_type in ("group_sum","top_by_sum"):
        by = op.get("by"); col = op.get("col")
        if by not in work.columns or col not in work.columns:
            return {"text":"Column not found."}
        g = work.groupby(by, dropna=False)[col].apply(lambda s: pd.to_numeric(s, errors="coerce").sum()).reset_index(name=f"{col}_sum")
        g = g.sort_values(f"{col}_sum", ascending=False)
        k = op.get("topk") or op.get("k")
        if k: g = g.head(int(k))
        rows = g.to_dict(orient="records")
        return {"text": f"Sum of {col} by {by}.", "rows": rows}

    if op_type in ("group_count","top_by_count"):
        by = op.get("by"); col = op.get("col")
        if by not in work.columns:
            return {"text":"Column not found."}
        if col and col in work.columns:
            s = pd.to_numeric(work[col], errors="coerce")
            g = work.assign(_q=s.fillna(0)).groupby(by, dropna=False)["_q"].sum().reset_index(name="count_sum")
        else:
            g = work.groupby(by, dropna=False).size().reset_index(name="count_sum")
        g = g.sort_values("count_sum", ascending=False)
        k = op.get("topk") or op.get("k")
        if k: g = g.head(int(k))
        rows = g.to_dict(orient="records")
        return {"text": f"Count by {by}.", "rows": rows}

    if op_type == "latest":
        by = op.get("by"); col = op.get("col")
        if by not in work.columns or col not in work.columns:
            return {"text":"Column not found."}
        s = pd.to_datetime(work[by], errors="coerce")
        idx = s.idxmax()
        if pd.isna(idx): return {"text":"No valid dates found."}
        val = pd.to_numeric(work.loc[idx, col], errors="coerce")
        return {"text": f"Latest {col} on {pd.to_datetime(work.loc[idx, by]).date()}: {0 if pd.isna(val) else float(val)}"}

    return {"text":"Sorry, I couldn't understand the request."}
