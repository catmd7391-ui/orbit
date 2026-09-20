# quick_calc.py
"""
Fast natural-language calculator.
Parses phrases like 'sum the amounts' → returns the operation + column.
No LLM involved. Runs in microseconds.
"""

import re

# IMPORTANT: order matters! More specific verbs first.
# "average" must be checked before "sum" so "average the total"
# doesn't match on the word "total".
VERBS = {
    "average": ["average", "avg", "mean"],
    "max":     ["max", "maximum", "biggest", "largest", "highest", "top"],
    "min":     ["min", "minimum", "smallest", "lowest", "least"],
    "count":   ["count", "how many", "number of"],
    "sum":     ["sum", "add up", "add all", "grand total",
                "add everything", "sum of", "total of",
                "total", "subtotal"],
}

NUMERIC_HINTS = [
    "amount", "price", "total", "value", "cost",
    "sales", "salary", "gst", "tax", "profit",
    "revenue", "quantity", "qty", "sum",
]


def parse_calc(message: str, columns: list) -> dict:
    msg = (message or "").lower().strip()

    # 1. Which operation? (ordered dict, so average wins over sum if both appear)
    op = None
    for operation, words in VERBS.items():
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", msg):
                op = operation
                break
        if op:
            break

    if not op:
        return {"matched": False}

    # 2. Which column?
    for col in columns:
        col_lower = str(col).lower().strip()
        if col_lower and col_lower in msg:
            return {"matched": True, "op": op, "column": col, "target": "below"}
        if col_lower and col_lower.rstrip("s") in msg and len(col_lower) > 3:
            return {"matched": True, "op": op, "column": col, "target": "below"}

    for col in columns:
        c = str(col).lower()
        if any(h in c for h in NUMERIC_HINTS):
            return {"matched": True, "op": op, "column": col, "target": "below"}

    return {
        "matched": True,
        "op": op,
        "need_column": True,
        "columns": columns,
    }


if __name__ == "__main__":
    cols = ["Invoice No", "Date", "Customer", "Amount", "GST", "Total"]

    tests = [
        "sum the amounts",
        "total GST",
        "average the total",
        "count rows",
        "max amount",
        "min GST",
        "sum everything",
        "hello world",
    ]

    for t in tests:
        print(f"{t:25} -> {parse_calc(t, cols)}")