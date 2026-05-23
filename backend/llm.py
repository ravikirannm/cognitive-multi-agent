import os
from typing import Any, Dict, List

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1200) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/v1/chat/completions"

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and body.get("choices"):
            message = body["choices"][0].get("message", {})
            return message.get("content", "").strip()
        return str(body)
    except requests.RequestException as exc:
        return f"[OLLAMA ERROR] {exc}"
