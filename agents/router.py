"""
Router — Intent Classifier + Dispatcher
=========================================
Reads every user message, decides what to do, calls the right tool.
"""

import re
from pydantic import BaseModel
from agents.llm           import LLMClient
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


class Message(BaseModel):
    role: str
    content: str


INTENT_MAP = {
    "memory":  ["remember", "note that", "keep in mind", "what do you know",
                 "what do you remember", "forget", "recall"],
    "screen":  ["screen", "what's on", "what is on", "read the error",
                 "screenshot", "what does it say", "ocr"],
    "search":  ["search", "look up", "find info", "what is", "who is",
                 "how does", "tell me about", "latest news", "google"],
    "cmd":     ["run", "execute", "terminal", "command", "shell",
                 "install", "ping", "ipconfig", "git", "mkdir", "dir"],
    "cv":      ["cv", "resume", "update cv", "edit resume", "export cv",
                 "add skill", "update experience", "update my resume"],
    "job":     ["apply", "job", "linkedin", "application", "vacancy",
                 "apply for", "find jobs", "search jobs"],
    "message": ["email", "gmail", "reply", "send message", "read email",
                 "inbox", "unread", "send an email"],
    "code":    ["write code", "create app", "build a", "make a", "generate",
                 "script", "program", "python file", "html", "website",
                 "application", "function", "class", "flask", "django",
                 "fastapi", "create a", "write a", "build me"],
    "file":    ["create file", "create folder", "open file", "delete",
                 "move file", "rename", "save", "new folder", "new file"],
    "app":     ["open", "close", "launch", "start chrome", "open spotify",
                 "open notepad", "open calculator", "open vs code"],
}


class Router:
    def __init__(self, system_prompt: str):
        self.llm       = LLMClient(system_prompt)
        self.memory    = MemoryTool()
        self.cmd       = CMDTool()
        self.cv        = CVTool()
        self.job       = JobTool()
        self.messaging = MessagingTool()
        self.code      = CodeTool()
        self.file      = FileTool()
        self.app       = AppTool()
        self.search    = WebSearchTool()
        self.screen    = ScreenTool()

    def _detect_intent(self, text: str) -> str:
        t = text.lower()
        for intent, keywords in INTENT_MAP.items():
            if any(kw in t for kw in keywords):
                return intent
        return "chat"

    def _get_memory_context(self, text: str) -> str:
        """Inject relevant memories into the LLM context."""
        snippets = self.memory.search(text, top_k=3)
        if snippets:
            return "\n\nWhat I remember about you:\n" + "\n".join(
                f"- {s}" for s in snippets
            )
        return ""

    def process(self, text: str, history: list) -> tuple[str, str]:
        """
        Returns (llm_response, action_result_string).
        """
        intent        = self._detect_intent(text)
        action_result = ""

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

        elif intent == "message":
            action_result = self.messaging.run(text)

        elif intent == "code":
            action_result = self.code.run(text)

        elif intent == "file":
            action_result = self.file.run(text)

        elif intent == "app":
            action_result = self.app.run(text)

        # Build LLM context
        mem_context = self._get_memory_context(text)
        context     = text
        if action_result:
            context = f"{text}\n\n[Action completed: {action_result[:400]}]"
        if mem_context:
            context += mem_context

        response = self.llm.chat(context, history)
        return response, action_result
