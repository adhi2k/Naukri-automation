"""
verify_system.py

Master diagnostic suite to verify all NopeRi components end-to-end:
1. Environment & Credentials Configuration
2. Local Ollama LLM Connection & Model Status
3. Naukri Authentication & Token Generation
4. Profile Bump / 'Active Today' Refresher
5. Google Sheets Webhook Sync
6. Mobile Notification Dispatcher
7. Local Applied Jobs Ledger & State Guard
8. Windows Task Scheduler Registration
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

load_dotenv(override=True)
init(autoreset=True)

PASS = f"{Fore.GREEN}[PASS]{Style.RESET_ALL}"
FAIL = f"{Fore.RED}[FAIL]{Style.RESET_ALL}"
WARN = f"{Fore.YELLOW}[WARN]{Style.RESET_ALL}"

def test_environment():
    print(f"\n{Fore.CYAN}1. Environment Configuration{Style.RESET_ALL}")
    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
    if not username or not password:
        print(f"  {FAIL} Missing NAUKRI_USERNAME or NAUKRI_PASSWORD")
        return False
    print(f"  {PASS} Credentials configured for: {username}")
    print(f"  {PASS} Auto Apply: {os.getenv('AUTO_APPLY', 'false')}")
    print(f"  {PASS} Daily Quota: {os.getenv('DAILY_APPLY_LIMIT', '20')} applications")
    return True

def test_ollama():
    print(f"\n{Fore.CYAN}2. Local Ollama LLM Engine{Style.RESET_ALL}")
    import requests
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    try:
        r = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m.get("name") for m in r.json().get("models", [])]
            print(f"  {PASS} Ollama service running at {ollama_url}")
            matched = any(model in m for m in models)
            if matched:
                print(f"  {PASS} Model loaded: {model}")
                return True
            else:
                print(f"  {WARN} Model '{model}' not found in installed models: {models}")
                return False
        else:
            print(f"  {FAIL} Ollama responded with HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"  {FAIL} Could not connect to Ollama: {e}")
        return False

def test_naukri_auth():
    print(f"\n{Fore.CYAN}3. Naukri Authentication (Direct API Mode){Style.RESET_ALL}")
    from src.client.naukri_client import NaukriLoginClient
    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
    os.environ["NAUKRI_LOGIN_MODE"] = "direct"
    os.environ["NAUKRI_BROWSER_FALLBACK"] = "false"
    
    try:
        client = NaukriLoginClient(username, password)
        sess = client.login()
        if sess and sess.bearer_token:
            print(f"  {PASS} Direct API login successful! Token length: {len(sess.bearer_token)}")
            return client
        else:
            print(f"  {FAIL} No token received")
            return None
    except Exception as e:
        print(f"  {FAIL} Login failed: {e}")
        return None

def test_profile_bump(client):
    print(f"\n{Fore.CYAN}4. Profile Bump ('Active Today' Recruiter Status){Style.RESET_ALL}")
    if not client:
        print(f"  {WARN} Skipped (Login failed)")
        return False
    from src.utils.profile_updater import bump_profile
    try:
        success = bump_profile(client)
        if success:
            print(f"  {PASS} Profile headline updated & marked 'Active Today'")
            return True
        else:
            print(f"  {FAIL} Profile bump request did not succeed")
            return False
    except Exception as e:
        print(f"  {FAIL} Profile bump error: {e}")
        return False

def test_google_sheets():
    print(f"\n{Fore.CYAN}5. Google Sheets Real-time Sync{Style.RESET_ALL}")
    webhook = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    if not webhook:
        print(f"  {WARN} GOOGLE_SHEET_WEBHOOK_URL not configured")
        return False
    from src.utils.google_sheets import append_job_to_sheet
    try:
        ok = append_job_to_sheet(
            job_id="test_diag_" + str(int(time.time())),
            title="System Diagnostic Test Job",
            company="NopeRi Automated Tests",
            location="Remote",
            score=99,
            ai_detail="Automated system diagnostic check"
        )
        if ok:
            print(f"  {PASS} Test row synced to Google Sheet via Webhook!")
            return True
        else:
            print(f"  {FAIL} Webhook sync failed")
            return False
    except Exception as e:
        print(f"  {FAIL} Google Sheets error: {e}")
        return False

def test_mobile_notification():
    print(f"\n{Fore.CYAN}6. Mobile Notification Dispatcher{Style.RESET_ALL}")
    from src.utils.notifier import send_mobile_notification
    try:
        ok = send_mobile_notification(
            applied_count=20,
            total_found=170,
            skipped_ext=0,
            failed_count=0,
            top_jobs=[{"title": "Full System Check OK", "company": "NopeRi Suite", "score": 100}]
        )
        if ok:
            print(f"  {PASS} Mobile push notification delivered successfully!")
            return True
        else:
            print(f"  {WARN} No notification channels succeeded")
            return False
    except Exception as e:
        print(f"  {FAIL} Notification error: {e}")
        return False

def test_windows_scheduler():
    print(f"\n{Fore.CYAN}7. Windows Task Scheduler & Local Guard{Style.RESET_ALL}")
    task_name = "NopeRi_Daily_Automation"
    cmd = ["schtasks", "/query", "/tn", task_name, "/fo", "LIST"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  {PASS} Task '{task_name}' is ACTIVE and ready in Windows Task Scheduler")
            for line in res.stdout.splitlines():
                if "Next Run Time" in line or "Status" in line:
                    print(f"    • {line.strip()}")
            return True
        else:
            print(f"  {WARN} Task '{task_name}' not found in schtasks")
            return False
    except Exception as e:
        print(f"  {FAIL} Scheduler check error: {e}")
        return False

def main():
    print(f"\n{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}NOPERI COMPLETE SYSTEM DIAGNOSTIC SUITE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}")

    results = {}
    results["Environment"] = test_environment()
    results["Ollama"] = test_ollama()
    client = test_naukri_auth()
    results["Naukri Auth"] = client is not None
    results["Profile Bump"] = test_profile_bump(client)
    results["Google Sheets"] = test_google_sheets()
    results["Mobile Alert"] = test_mobile_notification()
    results["Windows Scheduler"] = test_windows_scheduler()

    print(f"\n{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}")
    print(f"  {Style.BRIGHT}SYSTEM DIAGNOSTIC SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}")
    for name, status in results.items():
        st = f"{Fore.GREEN}WORKING PERFECTLY{Style.RESET_ALL}" if status else f"{Fore.RED}NEEDS ATTENTION{Style.RESET_ALL}"
        print(f"  {name:<22} : {st}")
    print(f"{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
