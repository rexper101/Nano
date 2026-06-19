"""
Web Search Tool
================
Searches DuckDuckGo (no API key needed) and summarises
results using the local LLM.

Examples:
  "search for latest Python news"
  "what is quantum computing"
  "look up machine learning trends 2025"
  "find tutorials for FastAPI"
"""

import re
import httpx


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen2.5:7b"

SUMMARISE_SYSTEM = """Summarise these web search results clearly and concisely.
Give a direct answer in 3-4 sentences.
Mention the source domain in brackets where relevant.
No markdown, plain text only."""


class WebSearchTool:
    def run(self, user_text: str) -> str:
        query = self._extract_query(user_text)
        if not query:
            return ""

        print(f"\033[35m[Search] Searching for: {query}\033[0m")
        results = self._search(query)

        if not results:
            return f"No results found for '{query}'."

        summary = self._summarise(query, results)
        return summary

    def _extract_query(self, text: str) -> str:
        patterns = [
            r"search(?:\s+for)?\s+(.+)",
            r"look up\s+(.+)",
            r"find\s+(?:info(?:rmation)?\s+(?:on|about)\s+)?(.+)",
            r"what is\s+(.+)",
            r"who is\s+(.+)",
            r"how (?:do|does|to)\s+(.+)",
            r"tell me about\s+(.+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip().rstrip("?")
        return text.strip()

    def _search(self, query: str) -> list[dict]:
        """DuckDuckGo instant answer API — no key required."""
        try:
            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={
                    "q":      query,
                    "format": "json",
                    "no_redirect": "1",
                    "no_html":     "1",
                },
                timeout=8.0,
                follow_redirects=True,
            )
            data    = resp.json()
            results = []

            # Abstract (direct answer)
            if data.get("AbstractText"):
                results.append({
                    "title":  data.get("Heading", ""),
                    "body":   data["AbstractText"],
                    "source": data.get("AbstractSource", ""),
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:4]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title":  topic.get("Text", "")[:60],
                        "body":   topic.get("Text", ""),
                        "source": topic.get("FirstURL", ""),
                    })

            return results

        except Exception as e:
            print(f"[Search] DuckDuckGo error: {e}")
            return self._fallback_search(query)

    def _fallback_search(self, query: str) -> list[dict]:
        """Fallback: use duckduckgo_search library if installed."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddg:
                raw = list(ddg.text(query, max_results=4))
            return [{"title": r["title"], "body": r["body"],
                     "source": r["href"]} for r in raw]
        except ImportError:
            return []
        except Exception:
            return []

    def _summarise(self, query: str, results: list[dict]) -> str:
        if not results:
            return f"Could not find information about '{query}'."

        # Build context for LLM
        context = "\n\n".join(
            f"[{r.get('source', 'web')}] {r['body']}"
            for r in results[:4]
        )

        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SUMMARISE_SYSTEM},
                        {"role": "user",   "content":
                            f"Query: {query}\n\nResults:\n{context}"},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 256},
                },
                timeout=30.0,
            )
            return resp.json()["message"]["content"].strip()
        except Exception:
            # Return first result as fallback
            return results[0]["body"][:400] if results else ""
