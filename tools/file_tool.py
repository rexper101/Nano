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

