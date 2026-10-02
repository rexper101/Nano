"""
Nano LLM client
===============

Talks to Ollama and chooses a local model automatically.
It prefers a fast model when available and keeps a short history
window so the assistant remembers the conversation.
"""

import os
import time
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_FAST_MODEL = "qwen2.5:7b"
DEFAULT_MAIN_MODEL = "qwen2.5:7b"
FAST_MODEL = os.getenv("NANO_OLLAMA_MODEL", "qwen2.5:7b")

ENGLISH_RULE = (
    "Always reply in English. "
    "Do not use Hindi, Japanese, or any other language. "
    "Keep answers short and easy to read."
)


class LLMClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt + "\n\n" + ENGLISH_RULE
        self._model        = None

    def _get_model(self) -> str:
        """Pick a healthy local model, preferring the user-configured choice."""
        if self._model:
            return self._model
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            available = [m["name"] for m in r.json().get("models", [])]

            def _match_model(preferred: list[str]) -> str | None:
                for alias in preferred:
                    for name in available:
                        if name == alias or name.startswith(alias + ":") or name.startswith(alias + "-") or alias in name:
                            return name
                return None

            preferred = [
                FAST_MODEL,
                "qwen2.5:7b",
                "qwen2.5",
                "qwen",
                "llama3.1",
                "llama3.2",
                "llama3",
                "mistral",
                "phi3:mini",
                "phi3",
            ]
            best_match = _match_model(preferred)
            if best_match:
                print(f"[LLM] Using model: {best_match}")
                self._model = best_match
                return best_match
        except Exception:
            pass
        self._model = FAST_MODEL
        return self._model

    def chat(self, user_text: str, history: list) -> str:
        model    = self._get_model()
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in history[-20:]:   # keep more recent messages for better context
            if isinstance(msg, dict):
                messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_text})

        for attempt in range(3):
            try:
                resp = httpx.post(
                    OLLAMA_URL,
                    json={
                        "model":   model,
                        "messages": messages,
                        "stream":  False,
                        "options": {
                            "temperature":   0.7,
                            "num_predict":   200,   # shorter = faster
                            "num_ctx":       2048,  # smaller context = faster
                            "repeat_penalty":1.1,
                        },
                    },
                    timeout=90.0,
                )
                if resp.status_code == 404:
                    payload = resp.json()
                    error_text = str(payload.get("error", "")).lower()
                    if "model" in error_text or "not found" in error_text:
                        return f"Ollama model not found: {model}. Run: ollama pull {model}"
                resp.raise_for_status()
                payload = resp.json()
                content = payload.get("message", {}).get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                for value in payload.values():
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                return "Ollama returned an empty response."

            except httpx.ConnectError:
                return "Ollama is not running. Start it with: ollama serve"
            except httpx.TimeoutException:
                if attempt == 2:
                    return "Ollama timed out. Try a shorter question."
                time.sleep(1)
            except httpx.HTTPStatusError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    return f"Ollama model not found: {model}. Run: ollama pull {model}"
                return f"Ollama error: {exc}"
            except Exception as e:
                return f"Ollama error: {e}"
        return "Failed after 3 attempts"