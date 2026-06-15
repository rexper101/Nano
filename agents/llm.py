"""
LLM Client — Ollama wrapper
============================
Same pattern as reference project's LLM calls.
Uses httpx to call local Ollama API.
"""

import httpx
from pydantic import BaseModel


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen2.5:7b"   # change to phi3:mini for faster responses


class Message(BaseModel):
    role: str
    content: str


class LLMClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def chat(self, user_text: str, history: list[Message]) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in history[-10:]:
            # history items are plain dicts {"role":..., "content":...}
            if isinstance(msg, dict):
                messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_text})

        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 256},
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

        except httpx.ConnectError:
            return "Ollama is not running. Please start it with: ollama serve"
        except Exception as e:
            return f"LLM error: {e}"