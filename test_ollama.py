import os
import sys
import time
import json
import threading
import requests
from dotenv import load_dotenv

load_dotenv()
base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

print(f"Checking Ollama: {base}")
print(f"Target Model   : {model}")

# 1. Check if Ollama is reachable
try:
    r = requests.get(f"{base}/api/tags", timeout=10)
    r.raise_for_status()
except Exception as exc:
    sys.exit(f"\n[Error] Cannot reach Ollama at {base}. Please ensure Ollama is running (`ollama serve`).\nDetails: {exc}")

installed_models = [m.get("name", "") for m in r.json().get("models", [])]
print(f"Installed models: {', '.join(installed_models) if installed_models else 'None'}")

# Verify target model is present
if not any(name == model or name.startswith(model + ":") for name in installed_models):
    sys.exit(f"\n[Error] Model '{model}' is not installed.\nRun: ollama pull {model}")

# 2. Check if model is already loaded in memory (via /api/ps)
try:
    ps_resp = requests.get(f"{base}/api/ps", timeout=5)
    running = [m.get("name", "") for m in ps_resp.json().get("models", [])]
    is_warm = any(name == model or name.startswith(model + ":") for name in running)
except Exception:
    is_warm = False

if is_warm:
    print("Model status   : Loaded in memory (ready for fast response).")
else:
    print("Model status   : Cold (not yet in memory).")
    print("                 Loading ~9GB model into CPU/RAM may take 30-45 seconds on first run.")

# 3. Test generation with streaming & live waiting indicator
print(f"\nSending test prompt to '{model}'...")

stop_spinner = False

def spinner_worker():
    start = time.time()
    spinner_chars = ["|", "/", "-", "\\"]
    idx = 0
    while not stop_spinner:
        elapsed = int(time.time() - start)
        char = spinner_chars[idx % len(spinner_chars)]
        sys.stdout.write(f"\r  {char} Waiting for model response... ({elapsed}s)")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.15)
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()

spinner_thread = threading.Thread(target=spinner_worker, daemon=True)
spinner_thread.start()

start_time = time.time()
full_reply = []

try:
    with requests.post(
        f"{base}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: OLLAMA_OK"}],
            "stream": True,
        },
        stream=True,
        timeout=180,
    ) as response:
        response.raise_for_status()

        first_token = True
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line.decode("utf-8"))
            token = chunk.get("message", {}).get("content", "")
            if token:
                if first_token:
                    stop_spinner = True
                    spinner_thread.join()
                    first_token = False
                    sys.stdout.write("Model response : ")
                    sys.stdout.flush()
                sys.stdout.write(token)
                sys.stdout.flush()
                full_reply.append(token)

            if chunk.get("done", False):
                break

    stop_spinner = True
    spinner_thread.join()

    total_time = round(time.time() - start_time, 2)
    print(f"\n\n[Success] Ollama local AI test passed in {total_time}s.")

except KeyboardInterrupt:
    stop_spinner = True
    spinner_thread.join()
    print("\n\n[Interrupted] Test stopped by user (Ctrl+C).")
except requests.exceptions.Timeout:
    stop_spinner = True
    spinner_thread.join()
    print(f"\n\n[Timeout] Model '{model}' did not respond within 180s.")
    print("Tip: If running on CPU, consider switching to 'qwen2.5:7b' for faster performance.")
except Exception as e:
    stop_spinner = True
    spinner_thread.join()
    print(f"\n\n[Error] Ollama request failed: {e}")
