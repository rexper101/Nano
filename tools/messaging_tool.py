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

    def _reply_to_last(self) -> str:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self._creds["gmail_user"], self._creds["gmail_password"])
            mail.select("inbox")

            _, data = mail.search(None, "ALL")
            ids = data[0].split()
            if not ids:
                mail.logout()
                return "No emails found."

            # Get last email
            _, msg_data = mail.fetch(ids[-1], "(RFC822)")
            msg      = email.message_from_bytes(msg_data[0][1])
            sender   = msg.get("From", "")
            subject  = msg.get("Subject", "")
            body     = self._get_body(msg)
            mail.logout()

            # Generate reply with LLM
            reply_text = self._generate_reply(body, sender)

            # Send the reply
            return self._send_raw(
                to=sender,
                subject=f"Re: {subject}",
                body=reply_text,
            )

        except Exception as e:
            return f"Could not reply: {e}"

    def _send_email(self, user_text: str) -> str:
        # Extract TO address
        match = re.search(r"to\s+([\w.@+]+)", user_text, re.IGNORECASE)
        if not match:
            return "Could not find recipient email address."
        to = match.group(1)

        # Extract subject / body from user text
        about_match = re.search(r"about\s+(.+)", user_text, re.IGNORECASE)
        body = about_match.group(1) if about_match else user_text

        return self._send_raw(to=to, subject="Message from Nano", body=body)

    def _send_raw(self, to: str, subject: str, body: str) -> str:
        try:
            msg            = MIMEText(body)
            msg["Subject"] = subject
            msg["From"]    = self._creds["gmail_user"]
            msg["To"]      = to

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self._creds["gmail_user"], self._creds["gmail_password"])
                smtp.send_message(msg)

            return f"Email sent to {to}."
        except Exception as e:
            return f"Failed to send email: {e}"

    def _get_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="ignore")
        else:
            return msg.get_payload(decode=True).decode(errors="ignore")
        return ""

    def _generate_reply(self, original: str, sender: str) -> str:
        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": REPLY_SYSTEM},
                        {"role": "user",   "content":
                            f"Original email from {sender}:\n{original[:400]}\n\nWrite a reply:"},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 300},
                },
                timeout=60.0,
            )
            return resp.json()["message"]["content"].strip()
        except Exception:
            return "Thank you for your email. I will get back to you shortly."
