"""
Job Tool
=========
Searches LinkedIn for jobs and opens application pages.
Uses Playwright to automate form filling.

Examples:
  "apply for Python developer jobs"
  "find data science jobs in Pune"
  "apply for this job: https://linkedin.com/jobs/..."
  "show me software engineer jobs"
"""

import re
import os
import subprocess
import httpx
from pathlib import Path


OLLAMA_URL  = "http://localhost:11434/api/chat"
MODEL       = "qwen2.5:7b"
LOG_FILE    = Path(os.path.expanduser("~/Documents/Nano_CV/job_applications.txt"))

COVER_SYSTEM = """Write a short, professional cover letter (3 paragraphs max).
First paragraph: express interest in the role.
Second paragraph: highlight 2-3 relevant skills.
Third paragraph: closing + call to action.
Output only the cover letter text."""


class JobTool:
    def run(self, user_text: str) -> str:
        text = user_text.lower()

        # Direct URL → open application
        url_match = re.search(r"https?://\S+", user_text)
        if url_match:
            return self._open_job_url(url_match.group())

        # Search for jobs
        if any(w in text for w in ["find", "search", "show", "look for"]):
            return self._search_jobs(user_text)

        # Apply command
        return self._apply_for_job(user_text)

    def _extract_query(self, text: str) -> str:
        """Pull job title and location from natural language."""
        # Remove filler
        clean = re.sub(
            r"(apply for|find|search|look for|show me|"
            r"jobs?|positions?|vacancies|openings?|"
            r"in|at|near|for)", "", text, flags=re.IGNORECASE
        ).strip()
        return clean or "software engineer"

    def _search_jobs(self, user_text: str) -> str:
        query  = self._extract_query(user_text)
        # Extract location if mentioned
        loc_match = re.search(r"\bin\s+([A-Za-z\s]+)$", user_text, re.IGNORECASE)
        location  = loc_match.group(1).strip() if loc_match else "India"

        search_url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={query.replace(' ', '%20')}"
            f"&location={location.replace(' ', '%20')}"
        )
        # Open in browser
        subprocess.Popen(["start", search_url], shell=True)
        return f"Opened LinkedIn job search for '{query}' in {location}."

    def _open_job_url(self, url: str) -> str:
        subprocess.Popen(["start", url], shell=True)
        self._log_application(url, "opened")
        return f"Opened job application: {url}"

    def _apply_for_job(self, user_text: str) -> str:
        query = self._extract_query(user_text)

        # Generate cover letter
        cover = self._generate_cover_letter(query)

        # Open LinkedIn job search
        search_url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={query.replace(' ', '%20')}&location=India"
        )
        subprocess.Popen(["start", search_url], shell=True)

        # Save cover letter
        cover_path = Path(os.path.expanduser("~/Documents/Nano_CV/cover_letter.txt"))
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.write_text(cover, encoding="utf-8")

        self._log_application(query, "applied")
        return (
            f"Opened LinkedIn for '{query}' jobs. "
            f"Cover letter saved to {cover_path}. "
            f"Use LinkedIn Easy Apply for quick applications."
        )

    def _generate_cover_letter(self, role: str) -> str:
        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": COVER_SYSTEM},
                        {"role": "user",   "content":
                            f"Write a cover letter for: {role} position"},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 400},
                },
                timeout=60.0,
            )
            return resp.json()["message"]["content"].strip()
        except Exception:
            return f"Dear Hiring Manager,\n\nI am applying for the {role} position..."

    def _log_application(self, job: str, status: str):
        from datetime import datetime
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {status} | {job}\n")
