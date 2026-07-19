"""
LLM Client — Fast Mode
========================
Uses phi3:mini for instant responses (2-3x faster than qwen2.5:7b).
Falls back to qwen2.5:7b if phi3:mini not available.

To pull phi3:mini (one time):
    ollama pull phi3:mini
"""

import httpx


OLLAMA_URL = "http://localhost:11434/api/chat"

# phi3:mini = ~150ms response, great for commands and chat
# qwen2.5:7b = ~800ms, better for complex reasoning
FAST_MODEL = "phi3:mini"
MAIN_MODEL = "qwen2.5:7b"

ENGLISH_RULE = (
    "IMPORTANT: Always reply in English only. "
    "Never use Hindi, Japanese, or any other language. "
    "Keep replies short — under 3 sentences."
)


class LLMClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt + "\n\n" + ENGLISH_RULE
        self._model        = None   # auto-detected on first call

    def _get_model(self) -> str:
        """Pick the fastest available model."""
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

            # Prefer phi3:mini for speed
            fast_match = _match_model(["phi3:mini", "phi3", "phi3:3.8b"])
            if fast_match:
                print(f"[LLM] Using fast model: {fast_match}")
                self._model = fast_match
                return fast_match

            # Fallback to qwen
            main_match = _match_model(["qwen2.5:7b", "qwen2.5", "qwen"])
            if main_match:
                print(f"[LLM] Using model: {main_match}")
                self._model = main_match
                return main_match
        except Exception:
            pass
        self._model = MAIN_MODEL
        return self._model

    def chat(self, user_text: str, history: list) -> str:
        model    = self._get_model()
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in history[-8:]:   # fewer history = faster
            if isinstance(msg, dict):
                messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_text})

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
                timeout=45.0,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()

        except httpx.ConnectError:
            return "Ollama is not running. Start it with: ollama serve"
        except httpx.TimeoutException:
            return "Response timed out. Try a simpler question."
        except Exception as e:
            return f"Error: {e}"