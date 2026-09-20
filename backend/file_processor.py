# file_processor.py
import os
import time

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_uploaded_file(upload):
    """Save an UploadFile object to disk."""
    filename = upload.filename
    ext = os.path.splitext(filename)[1].lower()

    # Unique name
    unique = f"{int(time.time() * 1000)}_{filename}"
    path = os.path.join(UPLOAD_DIR, unique)

    contents = await upload.read()
    with open(path, "wb") as f:
        f.write(contents)

    return {
        "filename": filename,
        "path": path,
        "extension": ext,
        "size": len(contents),
    }