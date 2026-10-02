import sys
import os
import pytest

# Ensure repo root is on path so agent_nano can be imported when pytest runs from tests/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Skip heavy dependency checks when importing the module during tests
os.environ.setdefault("NANO_SKIP_DEPS", "1")

import httpx

from agent_nano import NanoAgent
from agents.llm import LLMClient
from tools.search_tool import WebSearchTool


@pytest.fixture
def agent():
    # text_mode and no_avatar to avoid starting audio/GUI during tests
    return NanoAgent(text_mode=True, no_avatar=True)


def test_extract_cmd_direct_run(agent):
    original = "run: echo hello"
    tl = original.lower().strip()
    assert agent._extract_cmd(tl, original) == "echo hello"


def test_extract_cmd_pip_install(agent):
    tl = "pip install requests"
    assert agent._extract_cmd(tl, tl) == "pip install requests"


def test_extract_cmd_git_alias(agent):
    tl = "git status"
    assert agent._extract_cmd(tl, tl) == "git status"


def test_extract_cmd_npm(agent):
    tl = "npm install lodash"
    assert agent._extract_cmd(tl, tl) == "npm install lodash"


def test_extract_app_simple(agent):
    tl = "open chrome"
    assert agent._extract_app(tl) == "chrome"


def test_extract_app_phrase(agent):
    tl = "please launch visual studio code"
    app = agent._extract_app(tl)
    assert app != ""  # should detect an app name


def test_intent_code(agent):
    assert agent._intent("please write a python script") == "code"


def test_intent_cmd(agent):
    assert agent._intent("run git status") == "cmd"


def test_intent_app(agent):
    assert agent._intent("open chrome and navigate") == "app"


def test_intent_search(agent):
    assert agent._intent("what is python") == "search"


def test_intent_memory(agent):
    assert agent._intent("remember to buy milk") == "memory"


def test_intent_file(agent):
    assert agent._intent("read file notes.txt") == "file"


def test_search_query_extracts_clean_ollama_phrase():
    tool = WebSearchTool()
    assert tool._extract_query("search the web for Ollama update") == "Ollama update"
    assert tool._extract_query("look up qwen model improvements") == "qwen model improvements"


def test_llm_reports_missing_ollama_model(monkeypatch):
    client = LLMClient("test system")

    monkeypatch.setattr(
        "agents.llm.httpx.get",
        lambda *args, **kwargs: type("Resp", (), {"json": lambda self: {"models": []}})(),
    )

    def fake_post(*args, **kwargs):
        class Resp:
            status_code = 404

            def json(self):
                return {"error": "model 'qwen2.5:7b' not found"}

            def raise_for_status(self):
                raise httpx.HTTPStatusError(
                    "404", request=httpx.Request("POST", "http://localhost:11434/api/chat"), response=self
                )

        return Resp()

    monkeypatch.setattr("agents.llm.httpx.post", fake_post)

    assert client.chat("hello", []) == "Ollama model not found: qwen2.5:7b. Run: ollama pull qwen2.5:7b"


def test_llm_detects_missing_model_message(monkeypatch):
    client = LLMClient("test system")

    monkeypatch.setattr(
        "agents.llm.httpx.get",
        lambda *args, **kwargs: type("Resp", (), {"json": lambda self: {"models": [{"name": "tinyllama:latest"}]}})(),
    )

    ok, message = client.ensure_model_ready()
    assert ok is False
    assert "ollama pull qwen2.5:7b" in message


def test_llm_auto_pulls_missing_model(monkeypatch):
    client = LLMClient("test system")
    calls = {"get": 0, "pull": 0}

    def fake_get(*args, **kwargs):
        calls["get"] += 1
        if calls["get"] == 1:
            return type("Resp", (), {"json": lambda self: {"models": [{"name": "tinyllama:latest"}]}})()
        return type("Resp", (), {"json": lambda self: {"models": [{"name": "qwen2.5:7b"}]}})()

    def fake_run(command, **kwargs):
        calls["pull"] += 1
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("agents.llm.httpx.get", fake_get)
    monkeypatch.setattr("agents.llm.subprocess.run", fake_run)

    ok, message = client.ensure_model_ready(auto_pull=True)
    assert ok is True
    assert message is None
    assert calls["pull"] == 1
