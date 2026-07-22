"""
Nano LLM client
===============

Talks to Ollama and chooses a local model automatically.
It prefers a fast model when available and keeps a short history
window so the assistant remembers the conversation.
"""

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_FAST_MODEL = "phi3:mini"
DEFAULT_MAIN_MODEL = "qwen2.5:7b"

ENGLISH_RULE = (
    "Always reply in English. "
    "Do not use Hindi, Japanese, or any other language. "
    "Keep answers short and easy to read."
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

  