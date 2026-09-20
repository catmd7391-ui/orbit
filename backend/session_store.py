# session_store.py
"""
Supabase-backed session storage.
Drop-in replacement for Redis — same function names.
Sessions survive forever and work across any server.
"""
import json
import os
import time
import uuid

from supabase_client import supabase


def _fetch_session(sid: str):
    try:
        res = (
            supabase.table("sessions")
            .select("data")
            .eq("session_id", sid)
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0]["data"]
    except Exception as e:
        print("[session_store] fetch error:", e)
    return None


def _store_session(sid: str, data: dict, company_id: str = None, user_id: str = None):
    try:
        payload = {
            "session_id": sid,
            "data": data,
            "company_id": company_id,
            "user_id": user_id,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        # Upsert: update if exists, insert if not
        supabase.table("sessions").upsert(payload, on_conflict="session_id").execute()
    except Exception as e:
        print("[session_store] store error:", e)


# ============================================================
# PUBLIC API — same names as before
# ============================================================

def create_session(data: dict) -> str:
    sid = str(uuid.uuid4())
    data = dict(data or {})
    data["session_id"] = sid
    data["created_at"] = time.time()
    data.setdefault("messages", [])
    data.setdefault("files", [])
    data.setdefault("company_folders", {})

    # Create local folder + workbook path
    wb_name = data.get("name", "Workbook.xlsx")
    if not wb_name.endswith(".xlsx"):
        wb_name += ".xlsx"
    wb_dir = os.path.join("sessions", sid)
    os.makedirs(wb_dir, exist_ok=True)
    wb_path = os.path.join(wb_dir, wb_name)
    data["workbook_path"] = wb_path
    data["workbook_name"] = wb_name

    _store_session(
        sid,
        data,
        company_id=data.get("company_id"),
        user_id=data.get("user_id"),
    )
    return sid


def get_session(sid: str):
    return _fetch_session(sid)


def update_session(sid: str, updates: dict):
    s = get_session(sid)
    if not s:
        return None
    s.update(updates or {})
    _store_session(
        sid,
        s,
        company_id=s.get("company_id"),
        user_id=s.get("user_id"),
    )
    return s


def add_message(sid: str, role: str, content: str):
    s = get_session(sid)
    if not s:
        return
    s.setdefault("messages", []).append({"role": role, "content": content})
    _store_session(sid, s)


def add_file(sid: str, filename: str, meta: dict):
    s = get_session(sid)
    if not s:
        return
    s.setdefault("files", []).append({"filename": filename, **(meta or {})})
    _store_session(sid, s)


def set_document_context(sid, document, analysis, uploaded):
    update_session(sid, {
        "last_document": document,
        "last_document_analysis": analysis,
        "last_uploaded": uploaded,
    })


def set_agent_result(sid: str, result: dict):
    update_session(sid, {"last_agent_result": result})


def save_to_folder(sid: str, folder: str, filename: str, path: str):
    s = get_session(sid)
    if not s:
        return {"success": False, "error": "Session not found"}
    folders = s.get("company_folders", {})
    folders.setdefault(folder, []).append({
        "filename": filename,
        "path": path,
        "saved_at": time.time(),
    })
    update_session(sid, {"company_folders": folders})
    return {"success": True, "folder": folder, "filename": filename}