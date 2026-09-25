"""
test_ai.py
Quick test script to verify Groq Cloud AI connection & response speed.
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

print("=" * 60)
print("  Groq Cloud AI Diagnostic Test")
print("=" * 60)

if not key:
    print("[ERROR] GROQ_API_KEY not found in .env!")
    print("Get your free key at: https://console.groq.com/keys")
    sys.exit(1)

print(f"API Key : {key[:10]}...{key[-4:]}")
print(f"Model   : {model}")
print("\nSending test prompt to Groq Cloud...")

start = time.time()
try:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Respond with JSON: {\"status\": \"Groq is working\", \"speed\": \"ultra-fast\"}"}],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        },
        timeout=15
    )
    elapsed = time.time() - start

    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        print(f"\n[PASS] Response received in {elapsed:.2f} seconds!")
        print("Response:\n", content)
        print("\n>>> GROQ CLOUD AI IS READY & OPERATIONAL! <<<")
    else:
        print(f"\n[FAIL] Groq returned HTTP {r.status_code}: {r.text}")
except Exception as e:
    print(f"\n[FAIL] Connection error: {e}")
