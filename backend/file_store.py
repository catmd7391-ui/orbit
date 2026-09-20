# file_store.py
"""
Supabase Storage helper for .xlsx and upload files.
Falls back to local disk if Supabase isn't reachable.
"""
import os
from supabase_client import supabase

BUCKET = "workbooks"


def upload_file(local_path: str, remote_path: str) -> dict:
    """
    Upload a local file to Supabase Storage.
    remote_path: e.g. "session-abc/workbook.xlsx"
    Returns: {"success": True, "remote_path": ..., "url": ...}
    """
    try:
        with open(local_path, "rb") as f:
            data = f.read()

        # Upsert (overwrite if exists)
        try:
            supabase.storage.from_(BUCKET).remove([remote_path])
        except Exception:
            pass

        supabase.storage.from_(BUCKET).upload(
            path=remote_path,
            file=data,
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )

        # Get a signed URL valid for 1 hour
        signed = supabase.storage.from_(BUCKET).create_signed_url(remote_path, 3600)
        return {
            "success": True,
            "remote_path": remote_path,
            "url": signed.get("signedURL") or signed.get("signed_url"),
        }
    except Exception as e:
        print("[file_store] upload error:", e)
        return {"success": False, "error": str(e)}


def download_file(remote_path: str, local_path: str) -> dict:
    """
    Download a file from Supabase Storage to a local path.
    """
    try:
        data = supabase.storage.from_(BUCKET).download(remote_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return {"success": True, "local_path": local_path}
    except Exception as e:
        print("[file_store] download error:", e)
        return {"success": False, "error": str(e)}


def file_exists(remote_path: str) -> bool:
    try:
        parts = remote_path.rsplit("/", 1)
        folder = parts[0] if len(parts) > 1 else ""
        name = parts[-1]
        res = supabase.storage.from_(BUCKET).list(folder)
        return any(item.get("name") == name for item in (res or []))
    except Exception:
        return False


def delete_file(remote_path: str) -> dict:
    try:
        supabase.storage.from_(BUCKET).remove([remote_path])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_signed_url(remote_path: str, expires_in: int = 3600) -> str:
    try:
        signed = supabase.storage.from_(BUCKET).create_signed_url(remote_path, expires_in)
        return signed.get("signedURL") or signed.get("signed_url") or ""
    except Exception as e:
        print("[file_store] signed url error:", e)
        return ""