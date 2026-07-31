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

