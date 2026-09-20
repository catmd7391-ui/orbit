# rag_memory.py
import os
import json
import math
import time

BASE_DIR = os.path.dirname(__file__)
RAG_DIR = os.path.join(BASE_DIR, "rag_store")
os.makedirs(RAG_DIR, exist_ok=True)


def _tokenize(text):
    return [w.lower() for w in str(text).replace("\n", " ").split() if len(w) > 2]


def _vectorize(text, vocab):
    tokens = _tokenize(text)
    vec = {word: 0 for word in vocab}
    for t in tokens:
        if t in vec:
            vec[t] += 1
    return vec


def _cosine(a, b):
    keys = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values())) or 1
    nb = math.sqrt(sum(v * v for v in b.values())) or 1
    return dot / (na * nb)


def _store_path(session_id):
    return os.path.join(RAG_DIR, f"{session_id}.json")


def load_store(session_id):
    path = _store_path(session_id)
    if not os.path.exists(path):
        return {"documents": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"documents": []}


def save_store(session_id, store):
    try:
        with open(_store_path(session_id), "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("RAG save error:", e)


def add_document(session_id, filename, text, analysis=None):
    store = load_store(session_id)

    chunk_size = 800
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)

    entry = {
        "filename": filename,
        "analysis": analysis or {},
        "chunks": chunks,
        "added_at": time.time(),
    }

    store["documents"] = [
        d for d in store["documents"] if d.get("filename") != filename
    ]
    store["documents"].append(entry)
    save_store(session_id, store)
    print(f"[rag] stored {filename} ({len(chunks)} chunks)")
    return entry


def search(session_id, query, top_k=3):
    store = load_store(session_id)
    documents = store.get("documents", [])
    if not documents:
        return []

    all_chunks = []
    for doc in documents:
        for c in doc.get("chunks", []):
            all_chunks.append({"filename": doc.get("filename"), "text": c})

    if not all_chunks:
        return []

    vocab = set()
    for item in all_chunks:
        vocab.update(_tokenize(item["text"]))

    q_vec = _vectorize(query, vocab)

    scored = []
    for item in all_chunks:
        vec = _vectorize(item["text"], vocab)
        score = _cosine(q_vec, vec)
        scored.append({"score": score, "filename": item["filename"], "text": item["text"]})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def get_all_documents(session_id):
    store = load_store(session_id)
    return [
        {
            "filename": d.get("filename"),
            "analysis": d.get("analysis", {}),
            "chunks": len(d.get("chunks", [])),
        }
        for d in store.get("documents", [])
    ]


def build_context(session_id, query, top_k=3):
    results = search(session_id, query, top_k=top_k)
    if not results:
        return ""
    lines = ["RELEVANT CONTEXT FROM UPLOADED FILES:"]
    for r in results:
        lines.append(f"\n[From: {r['filename']} | score={round(r['score'], 2)}]")
        lines.append(r["text"][:600])
    return "\n".join(lines)