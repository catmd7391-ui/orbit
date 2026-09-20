# session_manager.py
import time
import uuid
import os
import json
import shutil

_SESSIONS = {}
BASE_DIR = os.path.dirname(__file__)
SESSION_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

COMPANY_FOLDERS = ["Finance", "HR", "Projects", "Reports", "Data"]


def _session_path(sid):
    return os.path.join(SESSION_DIR, f"{sid}.json")


def _workbook_path(sid):
    return os.path.join(SESSION_DIR, f"{sid}.xlsx")


def _save_session(sid):
    s = _SESSIONS.get(sid)
    if not s:
        return
    to_save = dict(s)
    doc = to_save.get("last_document")
    if isinstance(doc, dict) and "combined_text" in doc:
        doc = dict(doc)
        doc["combined_text"] = str(doc["combined_text"])[:5000]
        to_save["last_document"] = doc
    try:
        with open(_session_path(sid), "w", encoding="utf-8") as f:
            json.dump(to_save, f, default=str, indent=2)
    except Exception as e:
        print("Session save error:", e)


def _load_session(sid):
    path = _session_path(sid)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Session load error:", e)
        return None


def create_session(workbook):
    sid = str(uuid.uuid4())
    wb_path = _workbook_path(sid)

    from openpyxl import Workbook
    wb = Workbook()

    template_name = (workbook or {}).get("name", "Orbit.xlsx")
    template_columns = (workbook or {}).get("columns") or []
    template_rows = (workbook or {}).get("rows") or []
    template_sheets = (workbook or {}).get("sheets") or ["Sheet1"]

    ws = wb.active
    ws.title = template_sheets[0] if template_sheets else "Sheet1"

    if template_columns:
        ws.append(list(template_columns))

    for row in template_rows:
        if isinstance(row, list):
            padded = list(row)
            while len(padded) < len(template_columns):
                padded.append("")
            ws.append(padded[: len(template_columns)])

    for extra in template_sheets[1:]:
        wb.create_sheet(title=extra)

    wb.save(wb_path)

    _SESSIONS[sid] = {
        "session_id": sid,
        "created_at": time.time(),
        "workbook_path": wb_path,
        "workbook_name": template_name,
        "template": {
            "name": template_name,
            "columns": template_columns,
            "rows": template_rows,
            "sheets": template_sheets,
        },
        "messages": [],
        "files": [],
        "last_uploaded_file": None,
        "last_document": None,
        "last_document_analysis": None,
        "last_agent_result": None,
        "company_folders": {f: [] for f in COMPANY_FOLDERS},
    }
    _save_session(sid)
    return sid


def get_session(sid):
    if sid in _SESSIONS:
        return _SESSIONS[sid]
    loaded = _load_session(sid)
    if loaded:
        _SESSIONS[sid] = loaded
    return loaded


def add_message(sid, role, content):
    s = get_session(sid)
    if s:
        s["messages"].append({"role": role, "content": content, "timestamp": time.time()})
        _save_session(sid)


def add_file(sid, filename, info):
    s = get_session(sid)
    if s:
        s["files"].append({"filename": filename, "info": info})
        s["last_uploaded_file"] = info
        _save_session(sid)


def set_document_context(sid, document, analysis, uploaded_file):
    s = get_session(sid)
    if s:
        trimmed = dict(document or {})
        if "combined_text" in trimmed:
            trimmed["combined_text"] = str(trimmed["combined_text"])[:5000]
        s["last_document"] = trimmed
        s["last_document_analysis"] = analysis
        s["last_uploaded_file"] = uploaded_file
        _save_session(sid)


def set_agent_result(sid, result):
    s = get_session(sid)
    if s:
        s["last_agent_result"] = result
        _save_session(sid)


def save_to_folder(sid, folder, filename, workbook_path):
    s = get_session(sid)
    if not s:
        return {"success": False, "error": "Session not found"}
    if folder not in s["company_folders"]:
        s["company_folders"][folder] = []
    folder_dir = os.path.join(SESSION_DIR, sid, folder)
    os.makedirs(folder_dir, exist_ok=True)
    dest = os.path.join(folder_dir, filename)
    shutil.copy(workbook_path, dest)
    s["company_folders"][folder].append({"filename": filename, "path": dest, "saved_at": time.time()})
    _save_session(sid)
    return {"success": True, "path": dest, "folder": folder}