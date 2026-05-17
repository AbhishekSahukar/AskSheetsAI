import numpy as np
import pandas as pd


def make_json_safe(obj):
    """Recursively convert NumPy and pandas types to plain Python types for JSON serialization."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    if isinstance(obj, (pd.Series, pd.Index)):
        return make_json_safe(obj.to_list())
    if isinstance(obj, pd.DataFrame):
        return [make_json_safe(r) for r in obj.to_dict(orient="records")]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_json_safe(v) for v in obj]
    return str(obj)