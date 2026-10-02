"""
Nano LLM client
===============

Talks to Ollama and chooses a local model automatically.
It prefers a fast model when available and keeps a short history
window so the assistant remembers the conversation.
"""

import os
import subprocess
import time
import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_FAST_MODEL = "qwen2.5:7b"
DEFAULT_MAIN_MODEL = "qwen2.5:7b"
FAST_MODEL = os.getenv("NANO_OLLAMA_MODEL", "qwen2.5:7b")
OFFLINE_FALLBACK = os.getenv("NANO_OFFLINE_FALLBACK", "1").lower() in {"1", "true", "yes", "on"}

ENGLISH_RULE = (
    "Always reply in English. "
    "Do not use Hindi, Japanese, or any other language. "
    "Keep answers short and easy to read."
)


class LLMClient:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt + "\n\n" + ENGLISH_RULE
        self._model        = None

    def _preferred_models(self) -> list[str]:
        return [
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

    def ensure_model_ready(self, auto_pull: bool = True) -> tuple[bool, str | None]:
        """Check whether Ollama is running and a usable local model is installed."""
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            available = [m["name"] for m in r.json().get("models", [])]
            if not available:
                if auto_pull:
                    try:
                        subprocess.run(["ollama", "pull", FAST_MODEL], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        return self.ensure_model_ready(auto_pull=False)
                    except Exception as exc:
                        return False, f"Ollama model not found: {FAST_MODEL}. Run: ollama pull {FAST_MODEL}. Error: {exc}"
                return False, f"Ollama is running but no models are installed. Run: ollama pull {FAST_MODEL}"

            def _match_model(preferred: list[str]) -> str | None:
                for alias in preferred:
                    for name in available:
                        if name == alias or name.startswith(alias + ":") or name.startswith(alias + "-") or alias in name:
                            return name
                return None

            if _match_model(self._preferred_models()) is None:
                if auto_pull:
                    try:
                        subprocess.run(["ollama", "pull", FAST_MODEL], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        return self.ensure_model_ready(auto_pull=False)
                    except Exception as exc:
                        return False, f"Ollama model not found: {FAST_MODEL}. Run: ollama pull {FAST_MODEL}. Error: {exc}"
                return False, f"Ollama model not found: {FAST_MODEL}. Run: ollama pull {FAST_MODEL}"
            return True, None
        except httpx.ConnectError:
            return False, "Ollama is not running. Start it with: ollama serve"
        except Exception as exc:
            return False, f"Ollama error: {exc}"

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

            best_match = _match_model(self._preferred_models())
            if best_match:
                print(f"[LLM] Using model: {best_match}")
                self._model = best_match
                return best_match
        except Exception:
            pass
        self._model = FAST_MODEL
        return self._model
    def _offline_message(self) -> str:
        if not OFFLINE_FALLBACK:
            return "Ollama is not running. Start it with: ollama serve"
        return (
            "Offline mode: Ollama is unavailable. I can still run local commands and file actions, "
            "but advanced AI reasoning is paused until ollama serve is started."
        )
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
                return self._offline_message()
            except httpx.TimeoutException:
                if attempt == 2:
                    return self._offline_message() if OFFLINE_FALLBACK else "Ollama timed out. Try a shorter question."
                time.sleep(1)
            except httpx.HTTPStatusError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    return f"Ollama model not found: {model}. Run: ollama pull {model}"
                return self._offline_message()
            except Exception as e:
                return self._offline_message() if OFFLINE_FALLBACK else f"Ollama error: {e}"
        return "Failed after 3 attempts"