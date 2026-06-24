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

        # ── CMD — must be explicit run/execute or specific commands ──────
        CMD_PHRASES = [
            "run ", "execute ", "run the command",
            "ipconfig", "git status", "git log", "git pull", "git push",
            "pip install", "pip list", "install using pip",
            "check disk", "disk space", "tasklist", "processes",
            "python version", "python --version",
            "ping ", "dir ", "ls ", "mkdir ",
            "run ipconfig", "run git", "run python",
        ]
        if any(t.startswith(p) or p in t for p in CMD_PHRASES):
            return "cmd"

        # ── APP — open/close specific app names ─────────────────────────
        APP_NAMES = [
            "chrome","firefox","vs code","vscode","notepad",
            "calculator","spotify","discord","whatsapp","explorer",
            "file explorer","terminal","cmd","powershell",
            "word","excel","powerpoint","task manager","paint",
            "vlc","zoom","teams","obs","steam","brave","notion","slack",
        ]
        if re.search(r"\b(open|launch|start|close|quit|kill)\b", t):
            if any(app in t for app in APP_NAMES):
                return "app"
            # "open my downloads" etc
            if any(w in t for w in ["downloads","documents","desktop","pictures",
                                      "music","videos","folder","file"]):
                return "file"

        # ── PLAY MUSIC — open Spotify/YouTube, not code ─────────────────
        if re.search(r"\bplay\b", t):
            if any(w in t for w in ["song","music","track","playlist",
                                      "spotify","youtube","video"]):
                return "app"  # handled by app_tool opening Spotify

        # ── FILE operations ──────────────────────────────────────────────
        FILE_PHRASES = [
            "create a folder","create folder","make a folder","make folder",
            "new folder","create a file","new file","make a file",
            "open the folder","open folder","read the file","read file",
            "open my desktop","open downloads","open documents",
        ]
        if any(p in t for p in FILE_PHRASES):
            return "file"

        # ── CV ───────────────────────────────────────────────────────────
        if any(w in t for w in ["my cv","my resume","update cv","update resume",
                                  "edit cv","edit resume","export cv",
                                  "add to my cv","add to resume","show my cv"]):
            return "cv"

        # ── JOB ─────────────────────────────────────────────────────────
        if any(w in t for w in ["find jobs","search jobs","job openings",
                                  "apply for job","job in pune","linkedin job",
                                  "vacancy","job vacancy","internship"]):
            return "job"

