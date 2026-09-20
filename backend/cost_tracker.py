# cost_tracker.py
import json
from datetime import datetime
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), "api_costs.jsonl")

MODEL_COSTS = {
    "gpt-4o-mini": {"in": 0.0128, "out": 0.051},
    "gpt-4o": {"in": 0.212, "out": 0.85},
    "gpt-3.5-turbo": {"in": 0.0425, "out": 0.1275},
}


def log_usage(model, input_tokens, output_tokens):
    costs = MODEL_COSTS.get(model, {"in": 0, "out": 0})
    cost = input_tokens / 1000 * costs["in"] + output_tokens / 1000 * costs["out"]
    entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_inr": round(cost, 6),
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print("Cost log error:", e)
    return entry


def monthly_total():
    now = datetime.now()
    total = 0.0
    count = 0
    if not os.path.exists(LOG_FILE):
        return {"total_inr": 0.0, "requests": 0, "month": now.strftime("%Y-%m")}
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts.year == now.year and ts.month == now.month:
                        total += entry.get("cost_inr", 0)
                        count += 1
                except Exception:
                    continue
    except Exception:
        pass
    return {"total_inr": round(total, 2), "requests": count, "month": now.strftime("%Y-%m")}