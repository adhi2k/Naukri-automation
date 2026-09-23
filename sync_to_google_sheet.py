"""
sync_to_google_sheet.py

Utility script to:
1. Validate your Google Sheets connection (Webhook or Service Account).
2. Sync all previously applied jobs from applied_jobs.csv to your Google Sheet.
3. Automatically backfill Job URLs and formats.

Usage:
    python sync_to_google_sheet.py
"""

import os
import csv
import time
from dotenv import load_dotenv
from colorama import Fore, Style, init
from src.utils.google_sheets import append_job_to_sheet

load_dotenv(override=True)
init(autoreset=True)

CSV_FILE = "applied_jobs.csv"

def main():
    print(f"\n{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}GOOGLE SHEETS SYNC UTILITY{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 65}{Style.RESET_ALL}\n")

    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

    mode = None
    if webhook_url:
        mode = "Webhook"
        print(f"  Target: {Fore.GREEN}Google Apps Script Webhook{Style.RESET_ALL}")
        print(f"  URL   : {webhook_url[:40]}...")
    elif (sheet_name or sheet_id) and os.path.exists(creds_file):
        mode = "ServiceAccount"
        print(f"  Target: {Fore.GREEN}gspread Service Account ({creds_file}){Style.RESET_ALL}")
        print(f"  Sheet : {sheet_name or sheet_id}")
    else:
        print(f"  {Fore.RED}No Google Sheets configuration detected in .env!{Style.RESET_ALL}")
        print(f"\n  {Style.BRIGHT}Quick Setup (Takes 60 seconds):{Style.RESET_ALL}")
        print(f"  1. Open Google Sheets -> Create a new Blank Sheet.")
        print(f"  2. Click Extensions -> Apps Script.")
        print(f"  3. Replace the code with the script in GOOGLE_SHEET_SETUP.md.")
        print(f"  4. Click Deploy -> New Deployment -> Web app (Who has access: Anyone).")
        print(f"  5. Copy the Web app URL and add it to .env:")
        print(f"     {Fore.YELLOW}GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/.../exec{Style.RESET_ALL}\n")
        return

    if not os.path.exists(CSV_FILE):
        print(f"\n  {Fore.YELLOW}No {CSV_FILE} found yet. Nothing to sync.{Style.RESET_ALL}")
        return

    # Read applied_jobs.csv
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        print(f"\n  {Fore.YELLOW}{CSV_FILE} is empty.{Style.RESET_ALL}")
        return

    print(f"\n  Found {Fore.CYAN}{len(reader)}{Style.RESET_ALL} jobs in {CSV_FILE}. Beginning sync...\n")

    synced_count = 0
    failed_count = 0

    for i, row in enumerate(reader, 1):
        job_id = row.get("job_id", "")
        title = row.get("title", "")
        company = row.get("company", "")
        location = row.get("location", "")
        score_val = row.get("score")
        score = int(score_val) if score_val and score_val.isdigit() else None
        ai_detail = row.get("ai_detail", "")
        applied_at = row.get("applied_at", "")

        print(f"  [{i}/{len(reader)}] Syncing {Style.BRIGHT}{title}{Style.RESET_ALL} @ {company}...", end=" ", flush=True)

        success = append_job_to_sheet(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            score=score,
            ai_detail=ai_detail,
            applied_at=applied_at
        )

        if success:
            print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
            synced_count += 1
        else:
            print(f"{Fore.RED}FAILED{Style.RESET_ALL}")
            failed_count += 1

        time.sleep(0.5)

    print(f"\n{Fore.CYAN}{'-' * 65}{Style.RESET_ALL}")
    print(f"  Sync Complete: {Fore.GREEN}{synced_count} succeeded{Style.RESET_ALL}, {Fore.RED}{failed_count} failed{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * 65}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
