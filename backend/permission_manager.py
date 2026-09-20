# permission_manager.py
import time
import uuid

_PENDING = {}


def create_permission_request(session_id, plan, summary, task_message):
    pid = str(uuid.uuid4())
    _PENDING[pid] = {
        "permission_id": pid,
        "session_id": session_id,
        "plan": plan,
        "summary": summary,
        "task_message": task_message,
        "created_at": time.time(),
        "status": "pending",
    }
    return pid


def get_permission_request(pid):
    return _PENDING.get(pid)


def approve_permission(pid):
    req = _PENDING.get(pid)
    if req:
        req["status"] = "approved"
    return req


def reject_permission(pid):
    req = _PENDING.get(pid)
    if req:
        req["status"] = "rejected"
    return req