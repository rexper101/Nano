"""
File Tool — Fixed for Windows
===============================
Creates folders/files and opens paths properly.
"""

import os
import re
import subprocess
import webbrowser
from pathlib import Path


class FileTool:
    def run(self, user_text: str) -> str:
        t = user_text.lower()

        if any(w in t for w in ["create folder","make folder","new folder","mkdir"]):
            return self._create_folder(user_text)
        if any(w in t for w in ["create file","new file","make file"]):
            return self._create_file(user_text)
        if any(w in t for w in ["open folder","open file","open the"]):
            return self._open_path(t)
        if any(w in t for w in ["read file","show file","read the","contents of"]):
            return self._read_file(user_text)

        return ""

    def _extract_name(self, text: str) -> str:
        for pat in [
            r'called\s+["\']?([^"\']+?)["\']?\s*(?:on|in|at|$)',
            r'named\s+["\']?([^"\']+?)["\']?\s*(?:on|in|at|$)',
            r'"([^"]+)"',
            r"'([^']+)'",
        ]:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _base_path(self, text: str) -> Path:
        tl = text.lower()
        if "document" in tl:  return Path(os.path.expanduser("~/Documents"))
        if "download" in tl:  return Path(os.path.expanduser("~/Downloads"))
        if "picture"  in tl:  return Path(os.path.expanduser("~/Pictures"))
        return Path(os.path.expanduser("~/Desktop"))

    def _create_folder(self, text: str) -> str:
        name = self._extract_name(text) or "NewFolder"
        # Remove path-unsafe chars
        name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
        path = self._base_path(text) / name
        path.mkdir(parents=True, exist_ok=True)
        # Open it in Explorer
        subprocess.Popen(f'explorer "{path}"', shell=True)
        return f"Folder created: {path}"

    def _create_file(self, text: str) -> str:
        name = self._extract_name(text) or "new_file.txt"
        name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
        path = self._base_path(text) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        os.startfile(str(path))
        return f"File created: {path}"

    def _open_path(self, text: str) -> str:
        LOCS = {
            "desktop":   os.path.expanduser("~/Desktop"),
            "downloads": os.path.expanduser("~/Downloads"),
            "documents": os.path.expanduser("~/Documents"),
            "pictures":  os.path.expanduser("~/Pictures"),
            "music":     os.path.expanduser("~/Music"),
            "videos":    os.path.expanduser("~/Videos"),
        }
        for name, loc in LOCS.items():
            if name in text:
                subprocess.Popen(f'explorer "{loc}"', shell=True)
                return f"Opened {name} folder."

        name = self._extract_name(text)
        if name:
            p = Path(os.path.expanduser("~/Desktop")) / name
            if p.exists():
                os.startfile(str(p))
                return f"Opened {p}"
        return ""

    def _read_file(self, text: str) -> str:
        name = self._extract_name(text)
        if not name:
            return ""
        for base in [Path(os.path.expanduser("~/Desktop")),
                     Path(os.path.expanduser("~/Documents")),
                     Path("."), Path(os.path.expanduser("~"))]:
            p = base / name
            if p.exists() and p.is_file():
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if len(content) > 600:
                        content = content[:600] + "\n...(truncated)"
                    return f"Contents of {name}:\n{content}"
                except Exception as e:
                    return f"Could not read {name}: {e}"
        return f"File '{name}' not found on Desktop or Documents."