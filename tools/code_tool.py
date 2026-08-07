"""
Code Tool
==========
Nano's code writing capability.
User says: "write a Flask app", "create a Python calculator",
           "build a todo list app", "make a login page in HTML"
Nano generates the code and saves it to a file.

Uses Ollama LLM with a code-focused system prompt.
"""

import re
import os
import httpx
from pathlib import Path


CODE_SYSTEM = """You are an expert programmer. When asked to write code:
1. Write complete, working, well-commented code.
2. Use best practices for the language.
3. Include all imports and dependencies.
4. Add a brief comment at the top explaining what the code does.
5. Output ONLY the code, no explanation before or after.
Do not wrap in markdown fences. Output raw code only."""

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL      = "qwen2.5:7b"
OUTPUT_DIR = Path(os.path.expanduser("~/Desktop/Nano_Projects"))


# Language → file extension mapping
LANGUAGE_MAP = {
    "python":     ".py",
    "html":       ".html",
    "javascript": ".js",
    "js":         ".js",
    "css":        ".css",
    "flask":      ".py",
    "django":     ".py",
    "fastapi":    ".py",
    "react":      ".jsx",
    "node":       ".js",
    "typescript": ".ts",
    "sql":        ".sql",
    "bash":       ".sh",
    "powershell": ".ps1",
    "c++":        ".cpp",
    "java":       ".java",
    "rust":       ".rs",
}


class CodeTool:
    def run(self, user_text: str) -> str:
        """Generate code and save to file. Returns result message."""
        print(f"\033[35m[Code] Generating code for: {user_text[:60]}\033[0m")

        # Generate the code
        code = self._generate(user_text)
        if not code:
            return "Failed to generate code."

        # Determine filename
        filename = self._make_filename(user_text, code)
        filepath = self._save(filename, code)

        # Also open in VS Code if available
        self._open_in_editor(filepath)

        lines = code.count("\n") + 1
        return f"Created {filepath} ({lines} lines). Opening in VS Code..."

   