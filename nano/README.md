# Nano AI Desktop Assistant v3

**Anime girl avatar · Japanese-accent English voice · Offline · Windows**

Same clean architecture as jarvis-mlx:
`VAD → Whisper STT → Ollama LLM → Edge TTS (Japanese voice)`

---

## What's New in v3

| Feature | Detail |
|---|---|
| 🎌 Japanese voice | Edge TTS · `ja-JP-NanamiNeural` · natural accent |
| 🌸 Anime avatar | 2D anime girl drawn in Python/tkinter — no Unity needed |
| 🖥 Chat UI | Dark anime-themed HTML dashboard at `ui/index.html` |
| 💻 Code writer | Says "write a Flask app" → saves file → opens VS Code |
| ⚡ CMD runner | "run ipconfig", "install pandas", "git status" |
| 📄 CV updater | Reads + rewrites your resume with LLM |
| 💼 Job applier | Opens LinkedIn search + generates cover letter |
| 📧 Email | Read + reply to Gmail |
| 🔍 Web search | DuckDuckGo → LLM summary |
| 🖼 Screen reader | Screenshot + LLaVA vision + EasyOCR |
| 🧠 Memory | Remembers facts across sessions (ChromaDB) |

---

## Quick Start

```bash
# 1. Double-click setup.bat  (first time only)

# 2. Double-click run_nano.bat
#    → starts Ollama + API server + opens UI + launches Nano
```

Or manually:
```bash
# Terminal 1
ollama serve

# Terminal 2  
python api_server.py

# Terminal 3
python main.py --text        # text mode
python main.py               # voice mode
```

Then open `ui/index.html` in Chrome.

---

## Example Commands

```
"Write a Flask web app with a login page"
"Create a Python calculator GUI"
"Build a todo app in HTML and CSS"
"Run ipconfig"
"Install requests using pip"
"Check disk space"
"Open Chrome"
"Open VS Code"
"Create a folder called MCA Project on desktop"
"Update my CV — add Nano AI Assistant project"
"Find Python developer jobs in Pune"
"Read my emails"
"Search for latest AI research papers"
"What is on my screen?"
"Remember my name is Anike"
"What do you remember about me?"
```

---

## Project Structure

```
nano/
├── main.py               ← Entry point
├── api_server.py         ← FastAPI backend for the UI
├── run_nano.bat          ← One-click launcher (Windows)
├── run_nano_text.bat     ← Text-only mode launcher
├── setup.bat             ← First-time setup
│
├── avatar/
│   └── anime_avatar.py   ← 2D anime girl overlay (tkinter)
│
├── stt/
│   ├── vad.py            ← Voice activity detection
│   └── transcriber.py    ← Faster-Whisper STT
│
├── tts/
│   ├── japanese_speaker.py  ← Edge TTS Japanese voice ★
│   └── speaker.py           ← Piper offline fallback
│
├── agents/
│   ├── router.py         ← Intent detection + dispatch
│   └── llm.py            ← Ollama client
│
├── tools/
│   ├── code_tool.py      ← Write and save code ★
│   ├── cmd_tool.py       ← Run terminal commands ★
│   ├── app_tool.py       ← Open/close apps
│   ├── file_tool.py      ← Files and folders
│   ├── cv_tool.py        ← CV manager ★
│   ├── job_tool.py       ← Job applications ★
│   ├── messaging_tool.py ← Gmail read/reply ★
│   ├── search_tool.py    ← Web search
│   ├── screen_tool.py    ← Screenshot + OCR + LLaVA
│   └── memory_tool.py    ← Persistent memory
│
├── ui/
│   └── index.html        ← Anime dark chat dashboard ★
│
├── config/
│   └── secrets.json      ← Gmail credentials (optional)
│
└── requirements.txt
```

---

## Voice Setup

The Japanese voice (`ja-JP-NanamiNeural`) uses Microsoft Edge TTS — free, no API key, requires internet for the first call per session. It sounds like a natural Japanese girl speaking English.

If offline, Nano falls back to Piper TTS automatically.

---

## Gmail Setup (optional)

1. Enable 2-factor auth on Gmail
2. Go to **Google Account → Security → App Passwords**
3. Create app password for "Mail"
4. Add to `config/secrets.json`:
```json
{
  "gmail_user": "you@gmail.com",
  "gmail_password": "xxxx xxxx xxxx xxxx"
}
```
