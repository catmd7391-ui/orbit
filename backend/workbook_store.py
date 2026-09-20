# workbook_store.py
"""
Safe workbook writes:
- File lock (no two writers clobber each other)
- Snapshot before save (undo / history)
- Upload to Supabase Storage (cloud backup)
"""
import os
import shutil
import time
import filelock

_locks = {}


def _get_lock(path: str) -> filelock.FileLock:
    key = os.path.abspath(path)
    if key not in _locks:
        _locks[key] = filelock.FileLock(key + ".lock", timeout=15)
    return _locks[key]


def snapshot(path: str) -> str:
    if not os.path.exists(path):
        return ""
    snap_dir = path + ".versions"
    os.makedirs(snap_dir, exist_ok=True)
    ts = int(time.time() * 1000)
    snap_path = os.path.join(snap_dir, f"{ts}.xlsx")
    shutil.copy(path, snap_path)

    versions = sorted(os.listdir(snap_dir))
    if len(versions) > 30:
        for old in versions[:-30]:
            try:
                os.remove(os.path.join(snap_dir, old))
            except Exception:
                pass
    return snap_path


def list_versions(path: str):
    snap_dir = path + ".versions"
    if not os.path.exists(snap_dir):
        return []
    return sorted(os.listdir(snap_dir), reverse=True)


def restore_version(path: str, version_file: str):
    snap_dir = path + ".versions"
    snap = os.path.join(snap_dir, version_file)
    if not os.path.exists(snap):
        return {"success": False, "error": "Version not found"}
    shutil.copy(snap, path)
    return {"success": True, "restored": version_file}


def safe_save(wb, path: str, session_id: str = None, filename: str = None):
    """
    Snapshot + save under lock.
    If session_id is provided, also uploads the file to Supabase Storage.
    """
    with _get_lock(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        snapshot(path)
        wb.save(path)

        # Upload to Supabase Storage (best-effort — never fail the save)
        if session_id:
            try:
                from file_store import upload_file
                remote_name = filename or os.path.basename(path)
                remote_path = f"{session_id}/{remote_name}"
                result = upload_file(path, remote_path)
                if result.get("success"):
                    print(f"[workbook_store] ☁️  Uploaded to Supabase: {remote_path}")
                else:
                    print(f"[workbook_store] ⚠️  Supabase upload failed: {result.get('error')}")
            except Exception as e:
                print(f"[workbook_store] ⚠️  Supabase upload exception: {e}")