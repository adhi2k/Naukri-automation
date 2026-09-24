"""
daily_runner.py

Unified daily automation entrypoint for NopeRi:
1. Logs into Naukri.
2. Bumps profile headline/timestamp so you are marked "Active Today" for recruiters.
3. Searches, deduplicates, scores with local Ollama, and submits applications up to daily limit.
4. Updates Google Sheets in real-time.
5. Logs run statistics to daily_runs.log.

Run manually:
    python daily_runner.py

Run scheduled:
    See setup_daily_schedule.py to configure automated daily execution.
"""

import os
import sys

# Ensure execution always occurs within the project directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import logging
from datetime import datetime
from dotenv import load_dotenv
from colorama import Fore, Style, init

load_dotenv(override=True)
init(autoreset=True)

# Set up file + console logging with absolute paths
LOG_FILE = os.path.join(SCRIPT_DIR, "daily_runs.log")
STATE_FILE = os.path.join(SCRIPT_DIR, "last_run_date.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DailyRunner")

def already_ran_today() -> bool:
    if not os.path.exists(STATE_FILE):
        return False
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            last_date = f.read().strip()
        return last_date == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False

def mark_run_completed():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
    except Exception:
        pass

def main():
    force_run = "--force" in sys.argv or os.getenv("FORCE_RUN", "false").lower() in {"1", "true", "yes", "on"}
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Guard: Don't repeat full apply loop multiple times in a single day unless forced
    if not force_run and already_ran_today():
        logger.info(f"Already completed today's run ({today_str}). Exiting quietly to protect account.")
        print(f"\n{Fore.GREEN}[COMPLETED TODAY]{Style.RESET_ALL} NopeRi already completed today's applications ({today_str}).")
        print(f"Pass {Fore.YELLOW}--force{Style.RESET_ALL} if you want to re-run right now.")
        sys.exit(0)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.CYAN}{'=' * 68}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}NOPERI DAILY AUTOMATION RUNNER{Style.RESET_ALL} — {now_str}")
    print(f"{Fore.CYAN}{'=' * 68}{Style.RESET_ALL}\n")

    from src.client.naukri_client import NaukriLoginClient
    from src.utils.profile_updater import bump_profile
    from apply_agent import run_agent

    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
    daily_limit = int(os.getenv("DAILY_APPLY_LIMIT", "20"))
    auto_bump = os.getenv("AUTO_BUMP_PROFILE", "true").lower() in {"1", "true", "yes", "on"}

    if not username or not password:
        logger.error("Missing NAUKRI_USERNAME or NAUKRI_PASSWORD in .env")
        sys.exit(1)

    # 1. Login
    logger.info("Authenticating with Naukri...")
    client = NaukriLoginClient(username, password)
    try:
        client.login()
        logger.info(f"Successfully authenticated as {username}")
    except Exception as e:
        logger.error(f"Failed to log in to Naukri: {e}")
        sys.exit(1)

    # 2. Profile Bump
    if auto_bump:
        logger.info("Refreshing profile timestamp for 'Active Today' recruiter badge...")
        bump_profile(client)

    # 3. Job Search + AI Score + Apply + Google Sheet Sync
    logger.info(f"Executing application pipeline (Max daily quota: {daily_limit})...")
    try:
        summary = run_agent(client=client, auto_bump=False, max_applies=daily_limit)
        applied = summary.get("applied", 0)
        skipped = summary.get("skipped_ext", 0)
        failed = summary.get("failed", 0)
        logger.info(
            f"Daily run completed: {applied} applied, {skipped} skipped (external), {failed} failed."
        )
        mark_run_completed()
    except Exception as e:
        logger.error(f"Error during job application run: {e}", exc_info=True)
        sys.exit(1)

    print(f"\n{Fore.GREEN}[DONE] Daily automation finished successfully at {datetime.now().strftime('%H:%M:%S')}.{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
