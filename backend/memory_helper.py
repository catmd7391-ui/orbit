# memory_helper.py


def build_memory_context(session, max_messages=20):
    parts = []

    files = session.get("files", [])
    if files:
        parts.append("FILES UPLOADED:")
        for f in files[-5:]:
            parts.append(f"  - {f.get('filename', 'unknown')}")

    analysis = session.get("last_document_analysis")
    if isinstance(analysis, dict) and analysis.get("success"):
        parts.append("\nLAST DOCUMENT:")
        parts.append(f"  Type: {analysis.get('document_type')}")
        parts.append(f"  Sheet: {analysis.get('sheet_name')}")
        if analysis.get("columns"):
            parts.append(f"  Columns: {', '.join(analysis['columns'][:10])}")
        if analysis.get("rows"):
            parts.append(f"  Records: {len(analysis['rows'])}")

    messages = session.get("messages", [])
    if messages:
        parts.append("\nCONVERSATION:")
        for m in messages[-max_messages:]:
            role = m.get("role", "unknown").upper()
            content = str(m.get("content", ""))[:300]
            parts.append(f"  {role}: {content}")

    return "\n".join(parts) if parts else "No memory yet."


def build_chat_prompt(message, session):
    memory = build_memory_context(session)
    return f"""You are Orbit, a friendly AI workplace assistant.

You have memory of this session.
If the user says "it", "them", "that file", resolve using memory.

MEMORY:
{memory}

USER: {message}

Reply naturally in 1–3 sentences.
"""