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

        # ── EMAIL ────────────────────────────────────────────────────────
        if any(w in t for w in ["read my email","check email","check my email",
                                  "my inbox","unread email","reply to email",
                                  "send email","send an email"]):
            return "email"

        # ── WEB SEARCH ───────────────────────────────────────────────────
        SEARCH_PHRASES = [
            "search for","search the web","look up","find information",
            "what is ","who is ","latest news","news about",
            "tell me about ","google ","how does ","how do ",
        ]
        if any(t.startswith(p) or p in t for p in SEARCH_PHRASES):
            return "search"

        # ── CODE — ONLY when user explicitly asks to write/create code ───
        CODE_TRIGGERS = [
            # Must mention a programming language or framework
            r"write\s+(?:a\s+)?(?:python|flask|django|fastapi|html|css|javascript|js|react|node|sql|bash|powershell|script|program|app|application|function|class|api|website|web app)",
            r"create\s+(?:a\s+)?(?:python|flask|django|fastapi|html|css|javascript|js|react|node|sql|bash|script|program|app|application|function|class|api|website|web app)",
            r"build\s+(?:a\s+)?(?:python|flask|django|fastapi|html|css|javascript|js|react|node|sql|bash|script|program|app|application|function|class|api|website|web app)",
            r"generate\s+(?:a\s+)?(?:python|flask|django|fastapi|html|css|javascript|js|react|node|sql|code|script|program)",
            r"code\s+(?:for|to|that|which|a)",
            r"write\s+(?:me\s+)?(?:the\s+)?code",
            r"write\s+(?:a\s+)?script",
        ]
        for pat in CODE_TRIGGERS:
            if re.search(pat, t):
                return "code"

        # Default — just chat
        return "chat"

    # ── Main process ──────────────────────────────────────────────────────

    def process(self, text: str, history: list) -> tuple[str, str]:
        intent        = self._intent(text)
        action_result = ""

        try:
            if intent == "memory":
                action_result = self.memory.run(text)

            elif intent == "screen":
                action_result = self.screen.run(text)

            elif intent == "search":
                action_result = self.search.run(text)

            elif intent == "cmd":
                action_result = self.cmd.run(text)

            elif intent == "cv":
                action_result = self.cv.run(text)

            elif intent == "job":
                action_result = self.job.run(text)

            elif intent == "email":
                action_result = self.msg.run(text)

            elif intent == "code":
                action_result = self.code.run(text)

            elif intent == "file":
                action_result = self.file.run(text)

            elif intent == "app":
                # Handle "play song on Spotify"
                if re.search(r"\bplay\b", text.lower()):
                    action_result = self._handle_play(text)
                else:
                    action_result = self.app.run(text)

        except Exception as e:
            action_result = f"Tool error: {e}"

        # Build LLM context
        mem_snippets = self.memory.search(text, top_k=2)
        mem_context  = ""
        if mem_snippets:
            mem_context = "\n\nWhat I know about the user:\n" + "\n".join(f"- {s}" for s in mem_snippets)

        llm_input = text
        if action_result:
            llm_input = f"{text}\n\n[Action completed: {action_result[:300]}]"
        if mem_context:
            llm_input += mem_context

        response = self.llm.chat(llm_input, history)
        return response, action_result

    def _handle_play(self, text: str) -> str:
        """Handle music/video play requests."""
        t = text.lower()
        # Extract song/artist name
        m = re.search(r"play\s+(.+?)(?:\s+on\s+\w+)?$", t)
        song = m.group(1).strip() if m else ""

        if "spotify" in t or not song:
            # Open Spotify
            import subprocess
            subprocess.Popen("spotify", shell=True)
            return f"Opening Spotify." + (f" Search for: {song}" if song else "")

        if "youtube" in t:
            import webbrowser
            query = song.replace(" ", "+")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"Searching YouTube for: {song}"

        # Default: open YouTube search
        import webbrowser
        query = song.replace(" ", "+")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return f"Searching YouTube for: {song}"