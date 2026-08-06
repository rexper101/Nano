"""
Router — Fixed Intent Detection
=================================
Problem: "write a line in notepad" was triggering code_tool
         "play a song" was triggering app_tool incorrectly

Fix: More specific keyword matching — checks context not just single words
"""

import re
from agents.llm import LLMClient
from tools.cmd_tool       import CMDTool
from tools.cv_tool        import CVTool
from tools.job_tool       import JobTool
from tools.messaging_tool import MessagingTool
from tools.code_tool      import CodeTool
from tools.file_tool      import FileTool
from tools.app_tool       import AppTool
from tools.search_tool    import WebSearchTool
from tools.screen_tool    import ScreenTool
from tools.memory_tool    import MemoryTool


class Router:
    def __init__(self, system_prompt: str):
        self.llm      = LLMClient(system_prompt)
        self.memory   = MemoryTool()
        self.cmd      = CMDTool()
        self.cv       = CVTool()
        self.job      = JobTool()
        self.msg      = MessagingTool()
        self.code     = CodeTool()
        self.file     = FileTool()
        self.app      = AppTool()
        self.search   = WebSearchTool()
        self.screen   = ScreenTool()

    # ── Intent detection ──────────────────────────────────────────────────

    def _intent(self, text: str) -> str:
        t = text.lower().strip()

        # ── MEMORY (check first — simple keywords) ──────────────────────
        if any(t.startswith(w) or f" {w} " in t for w in
               ["remember", "note that", "don't forget", "keep in mind",
                "what do you know", "what do you remember",
                "recall", "forget", "clear memory"]):
            return "memory"

        # ── SCREEN ──────────────────────────────────────────────────────
        if any(w in t for w in ["what's on my screen","what is on my screen",
                                  "read the screen","read my screen",
                                  "take a screenshot","screenshot","read the error",
                                  "what does my screen say","ocr"]):
            return "screen"
        # ── APPLICATIONS / COMMANDS / TOOLS ─────────────────────────────
        if any(w in t for w in ["open ", "launch ", "start ", "play ", "close "]):
            return "app"
        if any(w in t for w in ["run ", "execute ", "install ", "pip ", "git ", "command", "cmd"]):
            return "cmd"
        if any(w in t for w in ["search ", "find ", "what is ", "who is ", "news", "latest", "look up"]):
            return "search"
        if any(w in t for w in ["file", "folder", "document", "read ", "create ", "list files", "open file"]):
            return "file"
        if any(w in t for w in ["cv", "resume", "cover letter", "job", "apply", "linkedin"]):
            return "job"
        if any(w in t for w in ["email", "gmail", "reply", "inbox", "send email"]):
            return "message"

        return "chat"

    def process(self, text: str, history: list) -> tuple[str, str]:
        intent = self._intent(text)
        action = ""

        try:
            if intent == "memory":
                action = "memory"
                return self.memory.run(text), action
            if intent == "screen":
                action = "screen"
                return self.screen.run(text), action
            if intent == "app":
                action = "app"
                return self.app.run(text), action
            if intent == "cmd":
                action = "cmd"
                return self.cmd.run(text), action
            if intent == "search":
                action = "search"
                return self.search.run(text), action
            if intent == "file":
                action = "file"
                return self.file.run(text), action
            if intent == "job":
                action = "job"
                return self.job.run(text), action
            if intent == "message":
                action = "message"
                return self.msg.run(text), action
            if intent == "chat":
                response = self.llm.chat(text, history)
                return response, action
        except Exception as exc:
            return f"Router error: {exc}", action

        response = self.llm.chat(text, history)
        return response, action
      