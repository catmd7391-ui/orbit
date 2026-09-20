# agent.py
# ORBIT EXCEL AGENT
# INSPECT -> DECIDE -> ACT -> VERIFY -> RECOVER

import inspect
import json
import os
import re

from brain import ask_ai
from excel_agent_tools import EXCEL_TOOLS


# ============================================================
# WORKBOOK PATH — set per task by main.py
# ============================================================

FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "company_report.xlsx"
)


def set_workbook_path(path):
    """Called by main.py before run_agent to point the agent
    at the current session's workbook."""
    global FILE_PATH
    if path:
        FILE_PATH = path


MAX_PLAN_STEPS = 10
MAX_AI_PLAN_RETRIES = 3
MAX_RECOVERY_ATTEMPTS = 3


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def same_value(a, b):
    return normalize(a) == normalize(b)


def file_exists():
    return os.path.exists(FILE_PATH)


def column_number_to_letter(number):
    if number <= 0:
        return "A"
    result = ""
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def calculate_populated_range(headers, rows):
    if not isinstance(headers, list):
        headers = []
    if not isinstance(rows, list):
        rows = []

    row_count = 0
    if headers:
        row_count = 1

    for row in rows:
        if isinstance(row, list):
            row_count += 1

    column_count = len(headers)
    for row in rows:
        if isinstance(row, list):
            column_count = max(column_count, len(row))

    if row_count == 0 or column_count == 0:
        return None

    end_column = column_number_to_letter(column_count)
    return f"A1:{end_column}{row_count}"


# ============================================================
# WORKBOOK STATE
# ============================================================

def normalize_workbook_state(raw_state):
    if not isinstance(raw_state, dict):
        return {"success": False, "error": "Invalid workbook state.", "sheets": {}}

    if "sheets" not in raw_state:
        cleaned = {}
        for sheet_name, rows in raw_state.items():
            if sheet_name in {"success", "error", "message"}:
                continue
            if not isinstance(sheet_name, str):
                continue
            if not isinstance(rows, list):
                rows = []
            cleaned[sheet_name] = rows
        return {"success": True, "sheets": cleaned}

    sheets = raw_state.get("sheets", [])
    normalized = {}

    if isinstance(sheets, dict):
        for sheet_name, rows in sheets.items():
            if not isinstance(sheet_name, str):
                continue
            if not isinstance(rows, list):
                rows = []
            normalized[sheet_name] = rows

    elif isinstance(sheets, list):
        for sheet in sheets:
            if not isinstance(sheet, dict):
                continue
            name = sheet.get("name")
            if not name:
                continue
            rows = sheet.get("rows", [])
            if not isinstance(rows, list):
                rows = []
            normalized[str(name)] = rows

    return {
        "success": raw_state.get("success", True),
        "sheets": normalized,
    }


def load_workbook_state():
    if not file_exists():
        return {
            "success": False,
            "error": f"Workbook not found: {FILE_PATH}",
            "sheets": {},
        }
    try:
        result = EXCEL_TOOLS["read_excel"](FILE_PATH)
    except Exception as error:
        return {"success": False, "error": str(error), "sheets": {}}

    return normalize_workbook_state(result)


# ============================================================
# SHEET HELPERS
# ============================================================

def get_sheet(state, sheet_name):
    if not isinstance(state, dict):
        return None
    if not sheet_name:
        return None

    sheets = state.get("sheets", {})
    if not isinstance(sheets, dict):
        return None

    if sheet_name in sheets:
        return {"name": sheet_name, "rows": sheets[sheet_name]}

    wanted = normalize(sheet_name)
    for actual_name, rows in sheets.items():
        if normalize(actual_name) == wanted:
            return {"name": actual_name, "rows": rows}
    return None


def sheet_exists(state, sheet_name):
    return get_sheet(state, sheet_name) is not None


def get_sheet_rows(state, sheet_name):
    sheet = get_sheet(state, sheet_name)
    if not sheet:
        return []
    rows = sheet.get("rows", [])
    return rows if isinstance(rows, list) else []


def get_sheet_headers(state, sheet_name):
    rows = get_sheet_rows(state, sheet_name)
    if not rows:
        return []
    first = rows[0]
    return first if isinstance(first, list) else []


# ============================================================
# TARGET SHEET EXTRACTION
# ============================================================

def extract_target_sheet(task):
    task = clean_text(task)
    if not task:
        return None

    patterns = [
        r'\bsheet\s+(?:called|named)\s+["\']([^"\']+)["\']',
        r'\bworksheet\s+(?:called|named)\s+["\']([^"\']+)["\']',
        r'\btab\s+(?:called|named)\s+["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    patterns = [
        r'\bsheet\s+(?:called|named)\s+([A-Za-z0-9][A-Za-z0-9 _-]*?)(?=\s+and\b|\s+with\b|\s+containing\b|\s*,|\s*\.?$)',
        r'\bcreate\s+(?:a\s+)?new\s+sheet\s+([A-Za-z0-9][A-Za-z0-9 _-]*?)(?=\s+and\b|\s+with\b|\s+containing\b|\s*,|\s*\.?$)',
        r'\bcreate\s+(?:a\s+)?sheet\s+([A-Za-z0-9][A-Za-z0-9 _-]*?)(?=\s+and\b|\s+with\b|\s+containing\b|\s*,|\s*\.?$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    known_reports = [
        (r'\bsales\s+report\b', "Sales Report"),
        (r'\bfinancial\s+report\b', "Financial Report"),
        (r'\bcustomer\s+report\b', "Customer Report"),
        (r'\binventory\s+report\b', "Inventory Report"),
        (r'\bemployee\s+report\b', "Employee Report"),
        (r'\bstudent\s+details?\b', "StudentDetails"),
        (r'\bemployee\s+details?\b', "EmployeeDetails"),
    ]
    for pattern, name in known_reports:
        if re.search(pattern, task, re.IGNORECASE):
            return name

    return None


# ============================================================
# COLUMN EXTRACTION
# ============================================================

def clean_column_name(value):
    value = clean_text(value)
    value = re.sub(r'^(?:and|or)\s+', '', value, flags=re.IGNORECASE)
    return value.strip(" ,.;:")


def split_columns(text):
    text = clean_text(text)
    if not text:
        return []

    text = re.split(
        r'\b(?:and\s+add|and\s+create|and\s+insert|and\s+include|'
        r'and\s+make|and\s+write|and\s+add\s+these)\b',
        text, maxsplit=1, flags=re.IGNORECASE
    )[0]

    text = text.strip(" .,:;")
    text = re.sub(r'\s+\band\b\s+', ',', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*&\s*', ',', text)
    text = re.sub(r'\s*/\s*', ',', text)

    parts = [clean_column_name(part) for part in text.split(",")]

    result = []
    ignored = {"column", "columns", "field", "fields", "data"}
    for part in parts:
        if not part:
            continue
        if normalize(part) in ignored:
            continue
        result.append(part)

    unique = []
    for column in result:
        if not any(same_value(column, existing) for existing in unique):
            unique.append(column)
    return unique


def extract_requested_columns(task):
    task = clean_text(task)
    if not task:
        return []

    patterns = [
        r'\bwith\s+columns?\s*[:\[]\s*(.+?)(?:\]|\.|\s+and\s+add\b|$)',
        r'\bcolumns?\s*[:\[]\s*(.+?)(?:\]|\.|\s+and\s+add\b|$)',
    ]

    JUNK = {
        "those fields as", "these fields as", "the fields as",
        "those fields", "these fields", "the fields",
        "these columns", "those columns", "the columns",
        "the following", "data", "column", "columns",
        "field", "fields",
    }

    for pattern in patterns:
        match = re.search(pattern, task, re.IGNORECASE | re.DOTALL)
        if not match:
            continue

        raw = match.group(1).strip()

        try:
            parsed = json.loads("[" + raw + "]")
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return [x.strip() for x in parsed if x.strip()]
        except Exception:
            pass

        columns = split_columns(raw)
        clean = []
        for col in columns:
            n = normalize(col)
            if n in JUNK:
                continue
            if len(n) > 40 or len(n) < 2:
                continue
            parts = n.split()
            if parts and parts[0] in {"use", "the", "those", "these", "with", "and"}:
                continue
            clean.append(col)
        if clean:
            return clean

    return []


# ============================================================
# RECORD EXTRACTION
# ============================================================

def parse_record_piece(piece):
    piece = clean_text(piece)
    if not piece:
        return None

    piece = piece.strip(" ,.;:")
    piece = re.sub(r'^[\-\*\u2022]\s*', '', piece)

    if "|" in piece:
        parts = [clean_text(x) for x in piece.split("|")]
        if len(parts) >= 2:
            return [parts[0], parts[1]]

    if "=" in piece:
        parts = [clean_text(x) for x in piece.split("=")]
        if len(parts) >= 2:
            return [parts[0], parts[1]]

    parts = [clean_text(x) for x in piece.split(",")]
    if len(parts) == 2:
        return [parts[0], parts[1]]

    match = re.match(r'^(.+?)\s+(-?\d+(?:\.\d+)?)$', piece)
    if match:
        return [match.group(1).strip(), match.group(2).strip()]

    return None


def extract_requested_records(task):
    task = clean_text(task)
    if not task:
        return []

    # Multi-row JSON: rows: [["A","B"], ["C","D"]]
    multi_row = re.search(
        r'\brows?\s*[:\[]\s*(\[\[.*?\]\])\s*(?:\.|$)',
        task, re.IGNORECASE | re.DOTALL
    )
    if multi_row:
        try:
            parsed = json.loads(multi_row.group(1))
            if isinstance(parsed, list) and all(isinstance(x, list) for x in parsed):
                return [list(r) for r in parsed]
        except Exception:
            pass

    # Single-row JSON: values: ["A", "B"]
    json_match = re.search(
        r'\b(?:values?|data)\s*[:\[]\s*(\[[^\]]+\])\s*(?:\.|$)',
        task, re.IGNORECASE | re.DOTALL
    )
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if isinstance(parsed, list):
                if parsed and all(isinstance(x, list) for x in parsed):
                    return [list(r) for r in parsed]
                return [list(parsed)]
        except Exception:
            pass

    # Natural: records: ...
    match = re.search(
        r'\b(?:records?|data|rows?)\s*:\s*(.+)',
        task, re.IGNORECASE | re.DOTALL
    )
    if not match:
        match = re.search(
            r'\badd\s+(?:these\s+)?(?:records?|rows?)\s*:\s*(.+)',
            task, re.IGNORECASE | re.DOTALL
        )
    if not match:
        return []

    data_text = match.group(1).strip()
    data_text = re.sub(
        r'\b(?:and\s+create\s+(?:a\s+)?table|'
        r'and\s+make\s+(?:a\s+)?table|'
        r'and\s+format.*)$',
        '', data_text, flags=re.IGNORECASE
    )

    pieces = re.split(r'[\r\n]+', data_text)
    if len(pieces) == 1 and ";" in data_text:
        pieces = data_text.split(";")
    if len(pieces) == 1:
        pieces = re.split(r',\s*(?=[A-Za-z][A-Za-z .\'-]*\s+-?\d)', data_text)

    records = []
    for piece in pieces:
        record = parse_record_piece(piece)
        if record:
            records.append(record)
    return records


# ============================================================
# TABLE / SHEET REQUIREMENTS
# ============================================================

def task_requires_table(task):
    task = clean_text(task)
    patterns = [
        r'\bcreate\s+(?:a\s+)?table\b',
        r'\bmake\s+(?:a\s+)?table\b',
        r'\badd\s+(?:a\s+)?table\b',
    ]
    return any(re.search(p, task, re.IGNORECASE) for p in patterns)


def task_requires_new_sheet(task):
    task = clean_text(task)
    patterns = [
        r'\bcreate\s+(?:a\s+)?new\s+sheet\b',
        r'\bcreate\s+(?:a\s+)?new\s+worksheet\b',
        r'\bcreate\s+(?:a\s+)?new\s+tab\b',
        r'\bcreate\s+(?:a\s+)?sheet\b',
        r'\bcreate\s+(?:a\s+)?worksheet\b',
    ]
    return any(re.search(p, task, re.IGNORECASE) for p in patterns)


# ============================================================
# OBJECTIVE (with LLM FALLBACK)
# ============================================================

def llm_extract_objective(task):
    """Use the LLM to understand the task when regex fails."""
    prompt = f"""
You are the objective extractor for Orbit.

USER TASK:
{task}

Extract the sheet name, columns, and rows.

Return ONLY JSON:
{{
  "sheet_name": "Name",
  "columns": ["Col1", "Col2"],
  "rows": [["val1", "val2"]],
  "create_sheet": true
}}

RULES:
- Sheet name must be PascalCase, no spaces.
- If multiple records → multiple rows.
- If only one record → one row.
- Return ONLY JSON.
"""

    try:
        response = ask_ai(prompt)
        text = clean_text(response)

        # Parse JSON
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None

        parsed = json.loads(text[start:end + 1])
        if not isinstance(parsed, dict):
            return None

        return parsed
    except Exception as e:
        print("[llm_extract_objective] error:", e)
        return None


def extract_objective(task):
    target_sheet = extract_target_sheet(task)
    requested_columns = extract_requested_columns(task)
    requested_records = extract_requested_records(task)
    requires_table = task_requires_table(task)
    create_sheet_required = task_requires_new_sheet(task)

    needs_clarification = False
    clarification_message = None

    # If regex failed → ask the LLM
    if not target_sheet or not requested_columns:
        print("\n[agent] Regex insufficient → asking LLM...")
        llm_result = llm_extract_objective(task)

        if llm_result:
            if not target_sheet and llm_result.get("sheet_name"):
                target_sheet = str(llm_result["sheet_name"]).strip()
                create_sheet_required = True

            if not requested_columns and llm_result.get("columns"):
                cols = llm_result["columns"]
                if isinstance(cols, list):
                    requested_columns = [str(c).strip() for c in cols if str(c).strip()]

            if not requested_records and llm_result.get("rows"):
                rows = llm_result["rows"]
                if isinstance(rows, list):
                    clean = []
                    for r in rows:
                        if isinstance(r, list):
                            clean.append([str(v).strip() if v is not None else "" for v in r])
                        elif isinstance(r, dict) and requested_columns:
                            clean.append([str(r.get(c, "")).strip() for c in requested_columns])
                    requested_records = clean

            if llm_result.get("create_sheet"):
                create_sheet_required = True

    # Still no sheet → error
    if target_sheet is None:
        task_lower = task.lower()
        signals = [
            "extract", "pdf", "document", "invoice", "form",
            "application", "the details", "the data",
            "uploaded", "attached", "file",
        ]
        if any(s in task_lower for s in signals):
            target_sheet = "ExtractedData"
            create_sheet_required = True
        else:
            needs_clarification = True
            clarification_message = (
                "Orbit could not determine which worksheet should be used. "
                "Please specify a sheet name, for example: "
                '"Create a new sheet called TestSales".'
            )

    # Still nothing to do → error
    if (
        not requested_columns
        and not requested_records
        and not requires_table
        and not create_sheet_required
        and target_sheet is not None
        and not needs_clarification
    ):
        if not re.search(r'\b(?:create|make|add|fill|put|extract|work|update|edit)\b',
                         task, re.IGNORECASE):
            needs_clarification = True
            clarification_message = "Orbit needs a clearer instruction."

    return {
        "target_sheet": target_sheet,
        "requested_columns": requested_columns,
        "requested_records": requested_records,
        "requires_table": requires_table,
        "create_sheet_required": create_sheet_required,
        "needs_clarification": needs_clarification,
        "clarification_message": clarification_message,
    }


# ============================================================
# RECONCILIATION
# ============================================================

def record_exists(rows, requested_record):
    if not requested_record:
        return False
    for row in rows:
        if not isinstance(row, list):
            continue
        if len(row) < len(requested_record):
            continue
        matches = True
        for index, expected in enumerate(requested_record):
            if not same_value(row[index], expected):
                matches = False
                break
        if matches:
            return True
    return False


def reconcile_objective(state, objective):
    target_sheet = objective.get("target_sheet")

    result = {
        "target_sheet": target_sheet,
        "requested_columns": objective.get("requested_columns", []),
        "requested_records": objective.get("requested_records", []),
        "requires_table": objective.get("requires_table", False),
        "create_sheet_required": objective.get("create_sheet_required", False),
        "current_headers": [],
        "current_records": [],
        "populated_range": None,
        "sheet_exists": False,
        "missing_columns": [],
        "missing_records": [],
        "table_satisfied": True,
        "objective_satisfied": False,
    }

    if not target_sheet:
        return result

    sheet = get_sheet(state, target_sheet)
    if not sheet:
        return result

    result["sheet_exists"] = True

    headers = get_sheet_headers(state, target_sheet)
    rows = get_sheet_rows(state, target_sheet)

    result["current_headers"] = headers
    result["current_records"] = rows
    result["populated_range"] = calculate_populated_range(headers, rows)

    for col in result["requested_columns"]:
        if not any(same_value(col, h) for h in headers if h is not None):
            result["missing_columns"].append(col)

    for rec in result["requested_records"]:
        if not record_exists(rows, rec):
            result["missing_records"].append(rec)

    sheet_ok = True
    if objective.get("create_sheet_required", False):
        sheet_ok = result["sheet_exists"]

    columns_ok = len(result["missing_columns"]) == 0
    records_ok = len(result["missing_records"]) == 0

    result["objective_satisfied"] = (
        sheet_ok and columns_ok and records_ok and result["table_satisfied"]
    )

    return result


# ============================================================
# DETERMINISTIC PLAN
# ============================================================

def build_safe_plan(objective, reconciliation):
    steps = []
    target_sheet = objective.get("target_sheet")
    if not target_sheet:
        return steps

    if (
        objective.get("create_sheet_required", False)
        and not reconciliation.get("sheet_exists", False)
    ):
        steps.append({
            "tool": "create_sheet",
            "arguments": {
                "file_path": FILE_PATH,
                "sheet_name": target_sheet,
            },
        })

    for column in reconciliation.get("missing_columns", []):
        steps.append({
            "tool": "add_column",
            "arguments": {
                "file_path": FILE_PATH,
                "sheet_name": target_sheet,
                "column_name": column,
            },
        })

    for record in reconciliation.get("missing_records", []):
        steps.append({
            "tool": "add_row",
            "arguments": {
                "file_path": FILE_PATH,
                "sheet_name": target_sheet,
                "row_data": record,
            },
        })

    if (
        objective.get("requires_table", False)
        and not reconciliation.get("table_satisfied", True)
    ):
        steps.append({
            "tool": "create_table",
            "arguments": {
                "file_path": FILE_PATH,
                "sheet_name": target_sheet,
                "table_name": "DataTable",
                "range_string": reconciliation.get("populated_range") or "A1:A1",
            },
        })

    return steps


# ============================================================
# VALIDATION
# ============================================================

def validate_arguments(tool_name, arguments):
    if tool_name not in EXCEL_TOOLS:
        return False, f"Unknown Excel tool: {tool_name}"
    if not isinstance(arguments, dict):
        return False, "Tool arguments must be an object."

    tool = EXCEL_TOOLS[tool_name]

    try:
        signature = inspect.signature(tool)
        required = []
        for name, parameter in signature.parameters.items():
            if (
                parameter.default is inspect.Parameter.empty
                and parameter.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
            ):
                required.append(name)

        missing = [n for n in required if n not in arguments]
        if missing:
            return False, f"Missing required arguments: {missing}"
    except Exception:
        pass

    return True, None


def validate_plan(plan):
    if not isinstance(plan, dict):
        return False, "AI plan must be a JSON object."
    steps = plan.get("steps")
    if not isinstance(steps, list):
        return False, "AI plan must contain a 'steps' array."
    if len(steps) > MAX_PLAN_STEPS:
        return False, f"Plan contains more than {MAX_PLAN_STEPS} steps."

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"Step {index + 1} is invalid."
        tool_name = step.get("tool")
        if not isinstance(tool_name, str):
            return False, f"Step {index + 1} has no tool."
        arguments = step.get("arguments", {})
        valid, error = validate_arguments(tool_name, arguments)
        if not valid:
            return False, f"Step {index + 1}: {error}"
    return True, None


# ============================================================
# AI FALLBACK PLANNER
# ============================================================

def build_planner_prompt(task, objective, reconciliation, state):
    sheets = state.get("sheets", {})
    compact_sheets = {}

    if isinstance(sheets, dict):
        for sheet_name, rows in sheets.items():
            if isinstance(rows, list):
                compact_sheets[sheet_name] = rows[:50]
            else:
                compact_sheets[sheet_name] = []

    compact_state = {
        "success": state.get("success", True),
        "sheets": compact_sheets,
    }

    return f"""
You are the planning engine inside Orbit.

USER TASK:
{task}

AUTHORITATIVE OBJECTIVE:
{json.dumps(objective, indent=2, ensure_ascii=False)}

CURRENT RECONCILIATION:
{json.dumps(reconciliation, indent=2, ensure_ascii=False)}

CURRENT WORKBOOK:
{json.dumps(compact_state, indent=2, ensure_ascii=False)}

AVAILABLE TOOLS:
{json.dumps(sorted(EXCEL_TOOLS.keys()), indent=2)}

RULES:
1. Never invent user data.
2. Never invent a target worksheet.
3. Use the exact file path: {FILE_PATH}
4. If the objective is already satisfied, return zero steps.
5. Return JSON only.

Required format:
{{
    "steps": [
        {{
            "tool": "tool_name",
            "arguments": {{ "argument": "value" }}
        }}
    ],
    "message": "short explanation"
}}
"""


def parse_json_from_ai(response):
    if isinstance(response, dict):
        return response
    text = clean_text(response)
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            pass
    return None


def ask_for_valid_plan(task, objective, reconciliation, state):
    prompt = build_planner_prompt(task, objective, reconciliation, state)
    last_error = None

    for _ in range(MAX_AI_PLAN_RETRIES):
        try:
            response = ask_ai(prompt)
            plan = parse_json_from_ai(response)
            if plan is None:
                last_error = "AI did not return valid JSON."
                continue
            valid, error = validate_plan(plan)
            if not valid:
                last_error = error
                continue
            return plan
        except Exception as error:
            last_error = str(error)

    return {
        "steps": [],
        "message": f"Orbit could not generate a valid execution plan: {last_error}",
        "success": False,
    }


# ============================================================
# EXECUTION
# ============================================================

def execute_tool(tool_name, arguments):
    if tool_name not in EXCEL_TOOLS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    tool = EXCEL_TOOLS[tool_name]
    try:
        result = tool(**arguments)
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}
    except Exception as error:
        return {"success": False, "error": str(error)}


def execute_plan(plan, objective):
    executed_steps = []
    steps = plan.get("steps", [])

    for index, step in enumerate(steps):
        tool_name = step.get("tool")
        arguments = step.get("arguments", {})

        print(f"\n----- EXECUTING STEP {index + 1} -----")
        print(f"Tool: {tool_name}")
        print("Arguments:", json.dumps(arguments, indent=2, ensure_ascii=False))

        result = execute_tool(tool_name, arguments)

        executed_steps.append({
            "step": index + 1,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })

        if not result.get("success", False):
            return {
                "success": False,
                "executed_steps": executed_steps,
                "error": result.get("error", "Tool execution failed."),
            }

    return {"success": True, "executed_steps": executed_steps}


# ============================================================
# FINAL VERIFICATION
# ============================================================

def final_objective_check(objective):
    state = load_workbook_state()
    if not state.get("success", True):
        return {"success": False, "error": state.get("error")}

    reconciliation = reconcile_objective(state, objective)
    return {
        "success": reconciliation["objective_satisfied"],
        "reconciliation": reconciliation,
    }


# ============================================================
# RUN AGENT
# ============================================================

def run_agent(task):
    task = clean_text(task)
    if not task:
        return {"success": False, "message": "Please provide a task.", "executed_steps": []}

    print("\n========================================")
    print("             ORBIT EXCEL AGENT")
    print("========================================")
    print(f"\nUSER TASK:\n{task}")

    objective = extract_objective(task)
    objective["task"] = task

    print("\n----- EXTRACTED OBJECTIVE -----")
    print(json.dumps(objective, indent=2, ensure_ascii=False))

    if objective.get("needs_clarification", False):
        message = objective.get("clarification_message", "Orbit needs more information.")
        print(f"\n{message}")
        return {"success": False, "message": message, "executed_steps": []}

    print("\n----- INSPECTING WORKBOOK -----")
    state = load_workbook_state()

    if not state.get("success", True):
        error = state.get("error", "Could not read workbook.")
        return {"success": False, "message": error, "executed_steps": []}

    print(json.dumps(state.get("sheets", {}), indent=2, ensure_ascii=False))

    print("\n----- OBJECTIVE RECONCILIATION -----")
    reconciliation = reconcile_objective(state, objective)
    print(json.dumps(reconciliation, indent=2, ensure_ascii=False))

    if reconciliation.get("objective_satisfied", False):
        print("\nOBJECTIVE ALREADY SATISFIED.")
        return {
            "success": True,
            "message": "Orbit verified that the requested work is already complete.",
            "executed_steps": [],
        }

    print("\nObjective is not yet satisfied.")

    deterministic_steps = build_safe_plan(objective, reconciliation)
    plan = {"steps": deterministic_steps, "message": "Deterministic Orbit plan."}

    if not deterministic_steps:
        print("\n----- ASKING AI TO PLAN -----")
        plan = ask_for_valid_plan(task, objective, reconciliation, state)
        if not plan.get("success", True) and not plan.get("steps"):
            return {
                "success": False,
                "message": plan.get("message", "Orbit could not create a plan."),
                "executed_steps": [],
            }

    print("\n============== ORBIT PLAN ==============")
    for index, step in enumerate(plan.get("steps", []), start=1):
        print(f"\nStep {index}")
        print(f"Tool: {step.get('tool')}")
        print("Arguments:", json.dumps(step.get("arguments", {}), indent=2, ensure_ascii=False))

    if not plan.get("steps"):
        return {
            "success": False,
            "message": "Orbit could not determine a safe operation for this request.",
            "executed_steps": [],
        }

    execution = execute_plan(plan, objective)
    executed_steps = execution.get("executed_steps", [])

    if not execution.get("success", False):
        return {
            "success": False,
            "message": "Orbit encountered an error while executing the task: "
                       + str(execution.get("error", "Unknown error")),
            "executed_steps": executed_steps,
        }

    print("\n----- FINAL OBJECTIVE CHECK -----")
    verification = final_objective_check(objective)
    print(json.dumps(verification, indent=2, ensure_ascii=False))

    if verification.get("success", False):
        print("\n========================================")
        print("       ORBIT TASK VERIFIED SUCCESS")
        print("========================================")
        return {
            "success": True,
            "message": "Orbit completed and verified the task.",
            "executed_steps": executed_steps,
        }

    return {
        "success": False,
        "message": "Orbit executed the task but could not verify the result.",
        "executed_steps": executed_steps,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print("\n===== ORBIT TEST MODE =====")
    while True:
        try:
            task = input("\n> ").strip()
        except KeyboardInterrupt:
            break
        if not task:
            continue
        if task.lower() in {"exit", "quit"}:
            break
        result = run_agent(task)
        print(json.dumps(result, indent=2, ensure_ascii=False))