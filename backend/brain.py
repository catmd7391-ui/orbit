# brain.py
"""
LLM brain for Orbit.
Supports two providers:
- groq:  Groq Cloud API (default in production — free tier)
- local: Ollama running on http://localhost:11434 (for development)

Switch providers by setting LLM_PROVIDER=local or LLM_PROVIDER=groq in .env
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# CONFIG
# ============================================================

# Default to groq so cloud deployments work without extra config.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# --- Ollama (local) ---
try:
    from ollama import Client as OllamaClient
except ImportError:
    OllamaClient = None

OLLAMA_LOCAL_URL = os.getenv("OLLAMA_LOCAL_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# --- Groq (cloud) ---
try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Default to a model that exists on Groq for new accounts
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


# ============================================================
# CLIENTS
# ============================================================

_ollama_client = None
_groq_client = None


def _get_ollama():
    global _ollama_client
    if _ollama_client is None and OllamaClient is not None:
        _ollama_client = OllamaClient(host=OLLAMA_LOCAL_URL)
    return _ollama_client


def _get_groq():
    global _groq_client
    if _groq_client is None and GroqClient is not None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to .env or Render env vars.")
        _groq_client = GroqClient(api_key=GROQ_API_KEY)
    return _groq_client


print(f"[brain] Provider: {LLM_PROVIDER}")
if LLM_PROVIDER == "groq":
    print(f"[brain] Model:    {GROQ_MODEL} (Groq)")
else:
    print(f"[brain] Model:    {OLLAMA_MODEL} (Local Ollama)")


# ============================================================
# PUBLIC API
# ============================================================

def ask_ai(prompt):
    """Send a prompt to the LLM and return the response text."""
    if LLM_PROVIDER == "groq":
        client = _get_groq()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    # local Ollama
    client = _get_ollama()
    if client is None:
        raise RuntimeError("Ollama client not available. Run: pip install ollama")
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]


def ask_ai_json(prompt):
    """Send a prompt and force the LLM to return valid JSON."""
    if LLM_PROVIDER == "groq":
        client = _get_groq()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No explanation."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    # local Ollama
    client = _get_ollama()
    if client is None:
        raise RuntimeError("Ollama client not available. Run: pip install ollama")
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No explanation."},
            {"role": "user", "content": prompt},
        ],
        format="json",
    )
    return response["message"]["content"]


def brain_status():
    return {
        "provider": LLM_PROVIDER,
        "model": GROQ_MODEL if LLM_PROVIDER == "groq" else OLLAMA_MODEL,
        "free": LLM_PROVIDER == "groq",
    }