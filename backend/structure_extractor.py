# structure_extractor.py
import json
import re
from brain import ask_ai


def extract_structure(task, document_context=None):
    task = (task or "").strip()
    if not task and not document_context:
        return {"success": False, "error": "No task"}

    full_input = task
    if document_context:
        full_input = f"{task}\n\n--- Document content ---\n{document_context[:6000]}"

    prompt = f"""
You are the structure extractor for AI 365.

Read the user's request and decide EXACTLY what they want in Excel.

REQUEST:
{full_input}

Return ONLY JSON:
{{
  "action": "create_sheet_with_data" | "add_row" | "add_column" | "edit_cell" | "add_formula" | "format_cells" | "sort_data",
  "sheet_name": "SheetName",
  "columns": ["Col1", "Col2"],
  "rows": [["v1","v2"]],
  "cell": "A1",
  "value": "some value",
  "formula": "=SUM(C2:C10)",
  "column_name": "Total",
  "cell_range": "A1:C10",
  "bold": true,
  "sort_column": 1,
  "descending": false,
  "confidence": 0.0
}}

EXAMPLES:

1) "Create student details with Name, Class, Marks, add rows: Ali 10th 85, Ravi 9th 90"
{{
  "action": "create_sheet_with_data",
  "sheet_name": "StudentDetails",
  "columns": ["Name", "Class", "Marks"],
  "rows": [["Ali", "10th", "85"], ["Ravi", "9th", "90"]],
  "confidence": 0.95
}}

2) "Add another row Priya 11th 92 to StudentDetails"
{{
  "action": "add_row",
  "sheet_name": "StudentDetails",
  "rows": [["Priya", "11th", "92"]],
  "confidence": 0.9
}}

3) "Change C2 in StudentDetails to 99"
{{
  "action": "edit_cell",
  "sheet_name": "StudentDetails",
  "cell": "C2",
  "value": "99",
  "confidence": 0.9
}}

4) "In StudentDetails add a Total column = sum of Marks"
{{
  "action": "add_formula",
  "sheet_name": "StudentDetails",
  "column_name": "Total",
  "cell": "D2",
  "formula": "=SUM(C2:C100)",
  "confidence": 0.9
}}

5) "Calculate average of Marks in StudentDetails"
{{
  "action": "add_formula",
  "sheet_name": "StudentDetails",
  "column_name": "Average",
  "cell": "D2",
  "formula": "=AVERAGE(C2:C100)",
  "confidence": 0.85
}}

6) "Count students in StudentDetails"
{{
  "action": "add_formula",
  "sheet_name": "StudentDetails",
  "column_name": "Count",
  "cell": "D2",
  "formula": "=COUNTA(A2:A100)",
  "confidence": 0.85
}}

7) "Make headers bold in StudentDetails"
{{
  "action": "format_cells",
  "sheet_name": "StudentDetails",
  "cell_range": "A1:C1",
  "bold": true,
  "confidence": 0.9
}}

8) "Sort StudentDetails by Marks descending"
{{
  "action": "sort_data",
  "sheet_name": "StudentDetails",
  "sort_column": 3,
  "descending": true,
  "confidence": 0.9
}}

RULES:
- Every row MUST have EXACTLY the same number of values as columns.
- Return ONLY JSON. No markdown.
"""

    try:
        response = ask_ai(prompt)
        parsed = _parse_json(response)
        if not parsed:
            return {"success": False, "error": "Invalid JSON from LLM"}

        action = str(parsed.get("action", "unknown")).strip()
        sheet_name = str(parsed.get("sheet_name", "")).strip()
        columns = parsed.get("columns", [])
        rows = parsed.get("rows", [])

        if not isinstance(columns, list):
            columns = []
        if not isinstance(rows, list):
            rows = []

        clean_columns = []
        for c in columns:
            name = str(c).strip()
            if name and name not in clean_columns:
                clean_columns.append(name)

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

        if not sheet_name:
            sheet_name = "Data"

        result = {
            "success": True,
            "action": action,
            "sheet_name": sheet_name,
            "columns": clean_columns,
            "rows": clean_rows,
            "confidence": parsed.get("confidence", 0.5),
        }

        # Optional fields
        for key in ("cell", "value", "formula", "column_name",
                    "cell_range", "bold", "sort_column", "descending"):
            if key in parsed:
                result[key] = parsed[key]

        print(f"[extractor] action={action} sheet={sheet_name} "
              f"cols={len(clean_columns)} rows={len(clean_rows)}")

        return result
    except Exception as e:
        print("structure_extractor error:", e)
        return {"success": False, "error": str(e)}


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