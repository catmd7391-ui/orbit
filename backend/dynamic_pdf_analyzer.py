# dynamic_pdf_analyzer.py
import json
import re
from brain import ask_ai


def analyze_any_pdf(pdf_text, filename=""):
    if not pdf_text or len(pdf_text.strip()) < 20:
        return {"success": False, "error": "Text too short", "fields": {}}

    text = pdf_text[:8000]

    prompt = f"""
You are a document analyzer.

Read this document and extract EVERY field as a column, and
EVERY record as a row.

DOCUMENT: {filename}

TEXT:
---
{text}
---

Return ONLY JSON:
{{
  "document_type": "short description",
  "sheet_name": "PascalCase",
  "columns": ["Col1", "Col2", "Col3"],
  "rows": [["val1", "val2", "val3"]],
  "confidence": 0.0
}}

CRITICAL RULES:
1. Every row MUST have EXACTLY the same number of values as columns.
2. If columns = ["Name", "Class", "Marks"], row must be
   ["Ali", "10th", "85"] — THREE values.
3. Do NOT combine two columns into one value.
4. If a field is blank/placeholder, use "" (empty string).
5. Single record → one row (even if some fields are empty).
6. Multiple records → multiple rows.
7. Return ONLY JSON.
"""

    try:
        response = ask_ai(prompt)
        parsed = _parse_json(response)
        if not parsed:
            return {"success": False, "error": "Invalid JSON", "fields": {}}

        columns = parsed.get("columns", [])
        rows = parsed.get("rows", [])
        if not isinstance(columns, list):
            columns = []
        if not isinstance(rows, list):
            rows = []

        clean_columns = [str(c).strip() for c in columns if str(c).strip()]

        clean_rows = []
        for r in rows:
            if isinstance(r, list):
                cleaned = [str(v).strip() if v is not None else "" for v in r]
                if len(cleaned) > len(clean_columns):
                    cleaned = cleaned[: len(clean_columns)]
                elif len(cleaned) < len(clean_columns):
                    cleaned = _split_row_to_match(cleaned, len(clean_columns))
                if any(v for v in cleaned):
                    clean_rows.append(cleaned)

        if clean_columns and not clean_rows:
            clean_rows = [["" for _ in clean_columns]]

        fields = {}
        if clean_columns and clean_rows:
            for i, col in enumerate(clean_columns):
                if i < len(clean_rows[0]) and clean_rows[0][i]:
                    fields[col] = clean_rows[0][i]

        sheet_name = str(parsed.get("sheet_name", "")).strip() or "ExtractedData"
        if len(sheet_name) > 31:
            sheet_name = sheet_name[:31]

        return {
            "success": True,
            "document_type": parsed.get("document_type", "Document"),
            "sheet_name": sheet_name,
            "columns": clean_columns,
            "rows": clean_rows,
            "fields": fields,
            "confidence": parsed.get("confidence", 0.5),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "fields": {}}


def _split_row_to_match(row, target_len):
    if not row:
        return [""] * target_len
    needed = target_len - len(row)
    if needed <= 0:
        return row[:target_len]
    last = row[-1].split()
    if len(last) > 1 and len(last) >= needed + 1:
        keep = " ".join(last[: len(last) - needed])
        new_parts = last[len(last) - needed :]
        return row[:-1] + [keep] + new_parts
    return row + [""] * needed


def _parse_json(text):
    if isinstance(text, dict):
        return text
    if not text:
        return None
    t = str(text).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(t[start : end + 1])
        except Exception:
            pass
    return None