"""
File Tool
==========
Create files, folders, read and open them.

Examples:
  "create a folder called MyProject on the desktop"
  "create a file called notes.txt"
  "open the downloads folder"
  "read requirements.txt"
"""

import os
import re
import subprocess
from pathlib import Path


class FileTool:
    def run(self, user_text: str) -> str:
        text = user_text.lower().strip()

        if any(w in text for w in ["create folder", "make folder", "new folder", "mkdir"]):
            return self._create_folder(user_text)

        if any(w in text for w in ["create file", "new file", "make file"]):
            return self._create_file(user_text)

        if any(w in text for w in ["open folder", "open file", "open the"]):
            return self._open_path(user_text)

        if any(w in text for w in ["read file", "show file", "read the"]):
            return self._read_file(user_text)

        return ""

    def _extract_name(self, text: str, keyword: str) -> str:
        """Extract name after keyword like 'called X' or 'named X'."""
        patterns = [
            rf"{keyword}\s+called\s+['\"]?(.+?)['\"]?$",
            rf"{keyword}\s+named\s+['\"]?(.+?)['\"]?$",
            rf"called\s+['\"]?(.+?)['\"]?",
            rf"named\s+['\"]?(.+?)['\"]?",
            rf"['\"](.+?)['\"]",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _resolve_path(self, text: str, name: str) -> Path:
        """Resolve full path, defaulting to Desktop."""
        base = Path(os.path.expanduser("~/Desktop"))
        if "documents" in text.lower():
            base = Path(os.path.expanduser("~/Documents"))
        elif "downloads" in text.lower():
            base = Path(os.path.expanduser("~/Downloads"))
        return base / name

    def _create_folder(self, text: str) -> str:
        name = self._extract_name(text, "folder")
        if not name:
            name = "NewFolder"
        path = self._resolve_path(text, name)
        path.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {path}"

    def _create_file(self, text: str) -> str:
        name = self._extract_name(text, "file")
        if not name:
            name = "new_file.txt"
        path = self._resolve_path(text, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        # Open in default editor
        try:
            os.startfile(str(path))
        except Exception:
            pass
        return f"File created: {path}"

    def _open_path(self, text: str) -> str:
        # Common locations
        locations = {
            "desktop":   os.path.expanduser("~/Desktop"),
            "downloads": os.path.expanduser("~/Downloads"),
            "documents": os.path.expanduser("~/Documents"),
            "pictures":  os.path.expanduser("~/Pictures"),
            "music":     os.path.expanduser("~/Music"),
        }
        for name, loc in locations.items():
            if name in text.lower():
                os.startfile(loc)
                return f"Opened {name} folder."

        # Try to find a specific file/folder name
        name = self._extract_name(text, "open")
        if name:
            path = Path(name)
            if not path.is_absolute():
                path = Path(os.path.expanduser("~/Desktop")) / name
            if path.exists():
                os.startfile(str(path))
                return f"Opened {path}"
        return ""

    def _read_file(self, text: str) -> str:
        name = self._extract_name(text, "file")
        if not name:
            return ""
        # Search common locations
        search_dirs = [
            Path(os.path.expanduser("~/Desktop")),
            Path(os.path.expanduser("~/Documents")),
            Path(os.path.expanduser("~/Downloads")),
            Path("."),
        ]
        for d in search_dirs:
            path = d / name
            if path.exists() and path.is_file():
                content = path.read_text(encoding="utf-8", errors="ignore")
                if len(content) > 500:
                    content = content[:500] + "...(truncated)"
                return f"Contents of {name}:\n{content}"
        return f"File '{name}' not found."
