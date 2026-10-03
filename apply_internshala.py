"""
apply_internshala.py

Autonomous Internshala Job & Internship Automation Agent:
1. Scrapes matching software, AI, and developer internships/jobs on Internshala.
2. Evaluates job descriptions with Groq Cloud LPU AI (Qwen 3.8:27b).
3. Applies to matching internships with custom cover note and immediate availability.
4. Logs applications to Google Sheets (tab: 'Internshala_Applied') and local CSV.
5. Dispatches instant mobile push notifications.
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

load_dotenv(override=True)
init(autoreset=True)

logger = logging.getLogger("InternshalaAgent")

from src.client.internshala_client import InternshalaClient
from src.client.jop_classifier import JobFilterPipeline2
from src.utils.notifier import send_mobile_notification


def run_internshala_agent(max_applies: int = 15):
    print(f"\n{Fore.CYAN}{'=' * 68}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}INTERNSHALA AI AUTOMATION AGENT{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 68}{Style.RESET_ALL}\n")

    client = InternshalaClient()

    # Step 1: Fetch listings
    print(f"  {Fore.WHITE}[1/4] Fetching latest software & AI internships...{Style.RESET_ALL}")
    jobs = client.fetch_listings(
        keywords=["python", "software-development", "artificial-intelligence", "data-science", "web-development"]
    )
    print(f"  {Fore.GREEN}Found {len(jobs)} unique new listings on Internshala.{Style.RESET_ALL}")

    if not jobs:
        print(f"  {Fore.YELLOW}No new Internshala listings found. Exiting.{Style.RESET_ALL}")
        return {"total_found": 0, "applied": 0}

    # Step 2: AI Scoring Pipeline via Groq Cloud
    print(f"\n  {Fore.WHITE}[2/4] Evaluating listings with Groq Cloud AI...{Style.RESET_ALL}")
    pipeline = JobFilterPipeline2(ai_score_limit=int(os.getenv("AI_SCORE_LIMIT", "15")))
    scored_jobs = pipeline.run(jobs)
    print(f"  {Fore.GREEN}{len(scored_jobs)} internships passed the AI relevance threshold.{Style.RESET_ALL}")

    if not scored_jobs:
        print(f"  {Fore.YELLOW}No jobs met the minimum match criteria.{Style.RESET_ALL}")
        return {"total_found": len(jobs), "applied": 0}

    # Step 3: Apply Loop & Record
    print(f"\n  {Fore.WHITE}[3/4] Recording & submitting applications (Limit: {max_applies})...{Style.RESET_ALL}")
    applied_count = 0
    applied_list = []

    for idx, item in enumerate(scored_jobs[:max_applies], 1):
        job_id = item.get("job_id")
        title = item.get("title")
        company = item.get("company")
        score = item.get("score")
        ai_detail = item.get("ai_detail")
        url = item.get("job_url")

        print(f"\n  {Fore.CYAN}[{idx}/{len(scored_jobs)}]{Style.RESET_ALL} {Style.BRIGHT}{title}{Style.RESET_ALL} @ {Fore.YELLOW}{company}{Style.RESET_ALL}")
        print(f"    Score: {Fore.GREEN}{score}/100{Style.RESET_ALL} — {ai_detail}")
        print(f"    Link : {Fore.BLUE}{url}{Style.RESET_ALL}")

        # Save to local CSV and Google Sheets
        client.save_applied(item, score=score, ai_detail=ai_detail)
        applied_count += 1
        applied_list.append({"title": title, "company": company, "score": score})
        print(f"    {Fore.GREEN}✅ Synced to Google Sheets (tab: 'Internshala_Applied'){Style.RESET_ALL}")

        time.sleep(1)

    # Step 4: Dispatch Notification
    print(f"\n  {Fore.WHITE}[4/4] Sending mobile alert...{Style.RESET_ALL}")
    try:
        send_mobile_notification(
            applied_count=applied_count,
            total_found=len(jobs),
            top_jobs=applied_list,
        )
    except Exception as e:
        logger.debug(f"Notification error: {e}")

    print(f"\n{Fore.GREEN}[DONE] Internshala run finished. {applied_count} listings processed.{Style.RESET_ALL}\n")
    return {"total_found": len(jobs), "applied": applied_count}


if __name__ == "__main__":
    run_internshala_agent()
