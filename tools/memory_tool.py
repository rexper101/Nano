"""
Memory Tool
============
Remembers facts about the user across sessions.
Stores in a local ChromaDB vector database.

Examples:
  "remember my name is Anike"
  "remember I prefer Python over Java"
  "what do you know about me"
  "forget everything"
"""

import re
import json
import time
import uuid
from pathlib import Path


MEMORY_DIR = Path("data/memory")


class MemoryTool:
    """
    Simple persistent memory using ChromaDB.
    Falls back to a plain JSON file if ChromaDB is not installed.
    """

    def __init__(self):
        self._col   = None
        self._json  = MEMORY_DIR / "memories.json"
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            client    = chromadb.PersistentClient(path=str(MEMORY_DIR / "chroma"))
            self._col = client.get_or_create_collection("nano_memory")
        except ImportError:
            pass   # Use JSON fallback

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, user_text: str) -> str:
        text = user_text.lower()

        if any(w in text for w in ["forget", "clear memory", "delete memory"]):
            return self._clear()

        if any(w in text for w in ["what do you know", "what do you remember",
                                    "recall", "show memory"]):
            return self._recall_all()

        if any(w in text for w in ["remember", "note that", "keep in mind",
                                    "save this", "don't forget"]):
            return self._store(user_text)

        return ""

    def store(self, text: str):
        """Store any fact — called automatically by the router."""
        self._store(text)

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Search memory — called by the LLM to inject context."""
        return self._search(query, top_k)

    # ── Storage ────────────────────────────────────────────────────────────────

    def _store(self, text: str) -> str:
        """Extract the fact and store it."""
        # Strip "remember" prefix
        fact = re.sub(
            r"^(remember|note that|keep in mind|save this|don't forget)\s+",
            "", text, flags=re.IGNORECASE
        ).strip()

        if not fact:
            return "What would you like me to remember?"

        mem_id = str(uuid.uuid4())

        if self._col:
            self._col.add(
                ids=[mem_id],
                documents=[fact],
                metadatas=[{"timestamp": int(time.time())}],
            )
        else:
            # JSON fallback
            memories = self._load_json()
            memories.append({"id": mem_id, "fact": fact, "ts": int(time.time())})
            self._save_json(memories)

        return f"Got it, I'll remember: {fact}"

    def _search(self, query: str, top_k: int = 3) -> list[str]:
        """Semantic search over memories."""
        if self._col and self._col.count() > 0:
            try:
                results = self._col.query(
                    query_texts=[query],
                    n_results=min(top_k, self._col.count()),
                )
                return results["documents"][0]
            except Exception:
                pass

        # JSON fallback — just return all facts
        memories = self._load_json()
        return [m["fact"] for m in memories[-top_k:]]

    def _recall_all(self) -> str:
        if self._col:
            count = self._col.count()
            if count == 0:
                return "I don't have any memories stored yet."
            all_data = self._col.get(include=["documents", "metadatas"])
            facts = all_data["documents"]
        else:
            memories = self._load_json()
            facts = [m["fact"] for m in memories]

        if not facts:
            return "I don't have any memories stored yet."

        result = f"Here's what I remember ({len(facts)} item(s)):\n"
        result += "\n".join(f"• {f}" for f in facts[-10:])
        return result

    def _clear(self) -> str:
        if self._col:
            all_ids = self._col.get()["ids"]
            if all_ids:
                self._col.delete(ids=all_ids)
        self._save_json([])
        return "Memory cleared."

    # ── JSON fallback helpers ─────────────────────────────────────────────────

    def _load_json(self) -> list:
        if self._json.exists():
            try:
                return json.loads(self._json.read_text())
            except Exception:
                pass
        return []

    def _save_json(self, data: list):
        self._json.write_text(json.dumps(data, indent=2))
