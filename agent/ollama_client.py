from __future__ import annotations

from typing import Any

import requests


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()

        message = data.get("message", {})
        content = message.get("content", "")
        return content.strip()
