
from typing import Dict, List

def resolve_columns(columns: List[str]) -> Dict[str, str | None]:
    cols = [c.lower() for c in columns]
    def find(*keys):
        for k in keys:
            for c in cols:
                if k in c: return columns[cols.index(c)]
        return None
    return {
        "date":     find("date", "day", "order_date", "invoice"),
        "amount":   find("revenue", "amount", "sales", "total", "price"),
        "quantity": find("quantity", "qty", "count", "units"),
        "product":  find("product", "item", "sku", "name"),
        "region":   find("region", "area", "zone", "state", "country")
    }
