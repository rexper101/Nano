import sys
import os
import pytest

# Ensure repo root is on path so agent_nano can be imported when pytest runs from tests/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Skip heavy dependency checks when importing the module during tests
os.environ.setdefault("NANO_SKIP_DEPS", "1")

from agent_nano import NanoAgent


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
