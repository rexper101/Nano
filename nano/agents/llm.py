"""
LLM Client — Ollama wrapper
============================
Calls local Ollama API. Always enforces English responses.
"""

import httpx


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen2.5:7b"   # change to phi3:mini for faster responses

# Injected into every request to force English output
ENGLISH_REINFORCEMENT = (
    "IMPORTANT: You must always reply in English only. "
    "Never use Hindi, Japanese, or any other language. English only."
)


class LLMClient:
    def __init__(self, system_prompt: str):
        # Inject English enforcement into system prompt
        self.system_prompt = system_prompt + "\n\n" + ENGLISH_REINFORCEMENT

    def chat(self, user_text: str, history: list) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]

        # history items are plain dicts {"role": ..., "content": ...}
        for msg in history[-10:]:
            if isinstance(msg, dict):
                messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_text})

        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model":   MODEL,
                    "messages": messages,
                    "stream":  False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 256,
                    },
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

        except httpx.ConnectError:
            return "Ollama is not running. Please start it with: ollama serve"
        except Exception as e:
            return f"Error: {e}"