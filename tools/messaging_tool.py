"""
Messaging Tool
===============
Read and reply to Gmail using smtplib + imaplib.
No paid API needed — uses your Gmail account directly.

Setup (one time):
  1. Enable 2-factor auth on your Gmail account
  2. Go to myaccount.google.com → Security → App Passwords
  3. Create an app password for "Mail"
  4. Add to config/secrets.json:
     {"gmail_user": "you@gmail.com", "gmail_password": "xxxx xxxx xxxx xxxx"}

Examples:
  "read my emails"
  "check inbox"
  "reply to the last email"
  "send email to boss@company.com about meeting tomorrow"
"""

import json
import re
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
from pathlib import Path
import httpx


OLLAMA_URL   = "http://localhost:11434/api/chat"
MODEL        = "qwen2.5:7b"
SECRETS_FILE = Path("config/secrets.json")

REPLY_SYSTEM = """Write a professional email reply.
Be concise (3-5 sentences max).
Match the tone of the original email.
Output only the reply body text, no subject line, no greeting header."""


class MessagingTool:
    def __init__(self):
        self._creds = self._load_creds()

    def _load_creds(self) -> dict:
        if SECRETS_FILE.exists():
            try:
                return json.loads(SECRETS_FILE.read_text())
            except Exception:
                pass
        return {}

    def run(self, user_text: str) -> str:
        text = user_text.lower()

        if not self._creds.get("gmail_user"):
            return (
                "Gmail not configured. "
                "Add your credentials to config/secrets.json. "
                "See tools/messaging_tool.py for instructions."
            )

        if any(w in text for w in ["read", "check", "inbox", "show email"]):
            return self._read_emails()

        if any(w in text for w in ["reply to", "reply"]):
            return self._reply_to_last()

        if "send" in text and ("to" in text or "@" in text):
            return self._send_email(user_text)

        return self._read_emails()

    def _read_emails(self, count: int = 5) -> str:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self._creds["gmail_user"], self._creds["gmail_password"])
            mail.select("inbox")

            _, data = mail.search(None, "UNSEEN")
            ids = data[0].split()

            if not ids:
                mail.logout()
                return "No unread emails."

            # Read last N unread
            results = []
            for uid in ids[-count:]:
                _, msg_data = mail.fetch(uid, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode(errors="ignore")

                sender = msg.get("From", "Unknown")
                results.append(f"From: {sender}\nSubject: {subject}")

            mail.logout()
            summary = f"You have {len(ids)} unread email(s):\n\n"
            summary += "\n\n".join(results)
            return summary[:500]

        except Exception as e:
            return f"Could not read emails: {e}"

    