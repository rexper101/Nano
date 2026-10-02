import subprocess
import sys

MODEL = "qwen2.5:7b"


def ensure_model() -> int:
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and MODEL in result.stdout:
            print(f"[OK] Ollama model already installed: {MODEL}")
            return 0

        print(f"[INFO] Pulling missing Ollama model: {MODEL}")
        pull = subprocess.run(["ollama", "pull", MODEL], capture_output=True, text=True, timeout=600)
        if pull.stdout:
            print(pull.stdout.strip())
        if pull.stderr:
            print(pull.stderr.strip())
        if pull.returncode != 0:
            print(f"[ERROR] Failed to install {MODEL}")
            return pull.returncode
        print(f"[OK] Installed Ollama model: {MODEL}")
        return 0
    except FileNotFoundError:
        print("[ERROR] Ollama is not installed or not on PATH. Install it from https://ollama.ai")
        return 1
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timed out while pulling {MODEL}")
        return 2


if __name__ == "__main__":
    sys.exit(ensure_model())
