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


    def _make_filename(self, user_text: str, code: str) -> str:
        """Pick a sensible filename based on the request and code content."""
        text_lower = user_text.lower()

        # Detect language
        ext = ".py"  # default
        for lang, language_ext in LANGUAGE_MAP.items():
            if lang in text_lower:
                ext = language_ext
                break

        # Detect class/function name from code for Python
        if ext == ".py":
            m = re.search(r"class (\w+)", code)
            if m:
                return f"{m.group(1).lower()}{ext}"
            m = re.search(r"def (\w+)", code)
            if m and m.group(1) != "__init__":
                return f"{m.group(1).lower()}{ext}"

        # Build name from user request
        clean = re.sub(r"[^a-z0-9\s]", "", text_lower)
        words = clean.split()
        # Remove filler words
        filler = {"write","create","build","make","a","an","the","for","me",
                  "simple","basic","with","using","in","code","script","app",
                  "application","program","python","html","flask","django"}
        words = [w for w in words if w not in filler]

        if words:
            name = "_".join(words[:3])
        else:
            name = "nano_project"

        return f"{name}{ext}"

    def _save(self, filename: str, code: str) -> Path:
        """Save code to ~/Desktop/Nano_Projects/"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / filename

        # Don't overwrite — add number suffix
        counter = 1
        while filepath.exists():
            stem = Path(filename).stem
            ext  = Path(filename).suffix
            filepath = OUTPUT_DIR / f"{stem}_{counter}{ext}"
            counter += 1

        filepath.write_text(code, encoding="utf-8")
        print(f"\033[32m[Code] Saved: {filepath}\033[0m")
        return filepath

    def _open_in_editor(self, filepath: Path):
        """Open the file in VS Code if installed."""
        import subprocess
        try:
            subprocess.Popen(["code", str(filepath)])
        except FileNotFoundError:
            try:
                subprocess.Popen(["notepad", str(filepath)])
            except Exception:
                pass
