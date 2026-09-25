# ----------------------------------------------------------------------------------
# apply_agent.py
#
# Entry point for the automated Naukri job application agent.
#
# What this script does end to end:
#   1. Logs in to Naukri using credentials from the environment.
#   2. Searches for jobs across a curated set of keyword/location queries.
#   3. Deduplicates results and passes them through an AI scoring pipeline.
#   4. Iterates over jobs that passed the filter and applies to each one.
#   5. Handles questionnaires automatically using a static answer engine.
#   6. Skips jobs that redirect to an external company apply page.
#   7. Persists applied job IDs to a CSV so they are never applied to twice.
#   8. Prints a structured terminal summary at the end of each run.
#
# Dependencies:
#   - NaukriLoginClient   : handles login and session management
#   - NaukriJobClient     : wraps Naukri's internal job/apply APIs
#   - JobFilterPipeline2  : AI-based job relevance scorer
#   - colorama            : terminal color output
#
# Configuration:
#   Set USERNAME and PASSWORD in .env. AI scoring runs locally through Ollama.
#   Optional: OLLAMA_URL and OLLAMA_MODEL (default: qwen2.5:7b).
#   Adjust BQUERIES, EXPERIENCE_LEVELS, PAGES, and JOB_AGE inside
#   fetch_all_jobs() to tune what gets fetched each run.
# ----------------------------------------------------------------------------------

from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.client.jop_classifier import JobFilterPipeline2
from src.exceptions.exceptions import NaukriAuthError, NaukriParseError
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init
import os
import time
import csv
import logging
from datetime import datetime

load_dotenv(override=True)
init(autoreset=True)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------
# Persistence — applied jobs CSV
#
# A flat CSV file is used as a lightweight store for applied job IDs. This
# prevents the agent from applying to the same job on subsequent runs.
# The file is appended to, never rewritten, so historical records are preserved.
# ----------------------------------------------------------------------------------

CSV_FILE = "applied_jobs.csv"


def load_applied_jobs() -> set:
    # Returns the set of job_ids already applied to in previous runs.
    # Returns an empty set if the file does not exist yet.
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return set(row["job_id"] for row in reader if "job_id" in row and row["job_id"])


def save_applied_job(job, score=None, ai_detail=None) -> None:
    # Appends a single job record to the CSV after a successful apply.
    # Creates the file with a header row on first write.
    file_exists = os.path.exists(CSV_FILE)
    fieldnames = ["job_id", "title", "company", "location", "score", "ai_detail", "applied_at", "job_url"]
    now_iso = datetime.utcnow().isoformat()
    now_readable = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    job_url = f"https://www.naukri.com/job-listings-{job.job_id}"
    location = getattr(job, "location", "")

    # Append to local CSV
    if not file_exists:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "job_id":     job.job_id,
                "title":      job.title,
                "company":    job.company,
                "location":   location,
                "score":      score if score is not None else "",
                "ai_detail":  ai_detail or "",
                "applied_at": now_iso,
                "job_url":    job_url,
            })
    else:
        # Check existing headers
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            first_line = f.readline().strip()
            existing_headers = [h.strip() for h in first_line.split(",")]
        
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=existing_headers, extrasaction="ignore")
            writer.writerow({
                "job_id":     job.job_id,
                "title":      job.title,
                "company":    job.company,
                "location":   location,
                "score":      score if score is not None else "",
                "ai_detail":  ai_detail or "",
                "applied_at": now_iso,
                "job_url":    job_url,
            })

    # Sync to Google Sheets if configured
    try:
        from src.utils.google_sheets import append_job_to_sheet
        target_tab = os.getenv("GOOGLE_SHEET_TAB_NAME", "Applied_Jobs")
        synced = append_job_to_sheet(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            location=location,
            score=score,
            ai_detail=ai_detail,
            experience=getattr(job, "experience", ""),
            salary=getattr(job, "salary", ""),
            applied_at=now_readable,
            tab_name=target_tab,
        )
        if synced:
            print(f"  {Fore.GREEN}[Google Sheets]{Style.RESET_ALL} Synced to tab '{target_tab}'")
    except Exception as e:
        logger.debug(f"Google Sheet update skipped: {e}")


# ----------------------------------------------------------------------------------
# Terminal display helpers
#
# All output is routed through these functions so the visual style stays
# consistent across the run. Nothing here affects business logic.
# ----------------------------------------------------------------------------------

LINE = f"{Fore.WHITE}{'-' * 68}{Style.RESET_ALL}"
THIN = f"{Fore.WHITE}{'.' * 68}{Style.RESET_ALL}"


def print_section_title(text: str) -> None:
    # Prints a bold titled section divider. Used to mark each major phase
    # of the run (login, fetch, filter, apply, summary).
    print(f"\n{LINE}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}{text.upper()}{Style.RESET_ALL}")
    print(LINE)


def print_job_header(index: int, total: int, job, score=None, ai_detail=None) -> None:
    # Prints the full metadata block for a single job. Includes title, company,
    # job ID, URL, AI score with a visual bar, and skill tags if present.
    now = datetime.utcnow().strftime("%Y-%m-%d  %H:%M UTC")
    score_str = ""

    if score is not None:
        score_color = Fore.GREEN if score >= 70 else (Fore.YELLOW if score >= 50 else Fore.RED)
        score_bar   = _score_bar(score)
        score_str   = f"  {score_color}{score}/100{Style.RESET_ALL}  {score_bar}"

    print(f"\n{LINE}")
    print(
        f"  {Fore.CYAN}{Style.BRIGHT}JOB {index}/{total}{Style.RESET_ALL}"
        f"  {Fore.WHITE}{now}{Style.RESET_ALL}"
    )
    print(THIN)
    print(f"  {Fore.WHITE}Title   :{Style.RESET_ALL}  {Style.BRIGHT}{job.title}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Company :{Style.RESET_ALL}  {Fore.YELLOW}{job.company}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Job ID  :{Style.RESET_ALL}  {Fore.BLUE}{job.job_id}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}URL     :{Style.RESET_ALL}  {Fore.BLUE}https://www.naukri.com/job-listings-{job.job_id}{Style.RESET_ALL}")

    if score is not None:
        detail_text = f"  {Fore.WHITE}({ai_detail}){Style.RESET_ALL}" if ai_detail else ""
        print(f"  {Fore.WHITE}Score   :{Style.RESET_ALL}{score_str}{detail_text}")

    if job.tags:
        tag_str = "  ".join(f"{Fore.CYAN}[{t}]{Style.RESET_ALL}" for t in job.tags)
        print(f"  {Fore.WHITE}Tags    :{Style.RESET_ALL}  {tag_str}")


def _score_bar(score: int, width: int = 10) -> str:
    # Returns a small progress bar representing the AI score (0-100).
    filled = int((score / 100) * width)
    bar    = "=" * filled + "-" * (width - filled)
    color  = Fore.GREEN if score >= 70 else (Fore.YELLOW if score >= 50 else Fore.RED)
    return f"{color}{bar}{Style.RESET_ALL}"


def print_status_applied(applied_at=None) -> None:
    ts = f"  {Fore.WHITE}at {applied_at}{Style.RESET_ALL}" if applied_at else ""
    print(f"  {Fore.GREEN}Status  :  Applied successfully{Style.RESET_ALL}{ts}")


def print_status_skipped_external() -> None:
    # External apply jobs cannot be submitted via the API. The URL is printed
    # in the job header so the user can open it manually if needed.
    print(f"  {Fore.YELLOW}Status  :  Skipped — external apply (open URL manually){Style.RESET_ALL}")


def print_status_failed(error) -> None:
    print(f"  {Fore.RED}Status  :  Failed — {error}{Style.RESET_ALL}")


def print_questionnaire_notice() -> None:
    print(f"  {Fore.CYAN}           Questionnaire detected, handling automatically{Style.RESET_ALL}")


def print_pipeline_results(final_jobs: list) -> None:
    # Prints a compact ranked table of every job that passed the AI filter,
    # sorted by score descending. Gives a quick overview before the apply loop.
    print_section_title(f"AI filter — {len(final_jobs)} jobs passed")
    col_w  = [4, 35, 28, 6]
    header = (
        f"  {Fore.WHITE}{'#':<{col_w[0]}}  "
        f"{'Title':<{col_w[1]}}  "
        f"{'Company':<{col_w[2]}}  "
        f"{'Score':>{col_w[3]}}{Style.RESET_ALL}"
    )
    print(header)
    print(f"  {Fore.WHITE}{'-' * sum(col_w)}{Style.RESET_ALL}")

    for i, job in enumerate(final_jobs, 1):
        score = job.get("score")
        score_color = (
            Fore.GREEN  if score and score >= 70 else
            Fore.YELLOW if score and score >= 50 else
            Fore.RED
        )
        score_display = f"{score_color}{score:>3}{Style.RESET_ALL}" if score is not None else "  ?"
        title   = (job.get("title")   or "")[:col_w[1]]
        company = (job.get("company") or "")[:col_w[2]]
        print(
            f"  {Fore.CYAN}{i:<{col_w[0]}}{Style.RESET_ALL}  "
            f"{title:<{col_w[1]}}  "
            f"{Fore.YELLOW}{company:<{col_w[2]}}{Style.RESET_ALL}  "
            f"{score_display}"
        )


def print_fetch_progress(keyword: str, location: str, exp: int, page: int, fetched: int, new: int) -> None:
    # Prints a single progress line per search query showing how many jobs
    # were returned and how many were new (not seen in earlier queries).
    loc        = location or "All India"
    kw_display = keyword[:30].ljust(30)
    loc_display = loc[:12].ljust(12)
    new_color  = Fore.GREEN if new > 0 else Fore.WHITE
    print(
        f"  {Fore.WHITE}[{kw_display} | {loc_display} | exp={exp} | p{page}]{Style.RESET_ALL}"
        f"  {Fore.WHITE}{fetched:>3} fetched  "
        f"{new_color}{new:>3} new{Style.RESET_ALL}"
    )


def print_summary(total_found: int, total_allowed: int, applied: int, skipped_ext: int, failed: int) -> None:
    # Prints the final run summary table. Called once at the end of the script.
    print_section_title("run summary")
    rows = [
        ("Jobs fetched (total unique)", str(total_found),   Fore.WHITE),
        ("Jobs passed AI filter",       str(total_allowed), Fore.CYAN),
        ("Applied successfully",        str(applied),       Fore.GREEN),
        ("Skipped (external apply)",    str(skipped_ext),   Fore.YELLOW),
        ("Failed",                      str(failed),        Fore.RED),
    ]
    for label, value, color in rows:
        print(f"  {Fore.WHITE}{label:<30}{Style.RESET_ALL}  {color}{Style.BRIGHT}{value}{Style.RESET_ALL}")
    print(LINE + "\n")


# ----------------------------------------------------------------------------------
# Job fetching
#
# Runs a fixed set of search queries against the Naukri search API and
# collects results into a deduplicated list.
#
# Design decisions:
#   - Queries are hand-curated for the target stack (Node.js, Python, backend).
#   - Only Bangalore and Pune are targeted — highest product/startup density.
#   - Experience is fixed at 2 years. exp=3 pulled in too many senior roles.
#   - job_age=2 keeps results fresh, which improves apply response rates.
#   - 1 page per query. Quality drops sharply beyond page 2 on Naukri.
#   - 1.2s sleep between requests to avoid rate limiting.
#   - Deduplication is done by job_id across all queries before returning.
# ----------------------------------------------------------------------------------

def fetch_all_jobs(jc: NaukriJobClient) -> list:

    BQUERIES = [
    {"keyword": "Python Developer",     "location": "Chennai"},
    {"keyword": "Python Developer",     "location": "Bangalore"},
    {"keyword": "Java Developer",       "location": "Chennai"},
    {"keyword": "Software Developer",   "location": "Chennai"},
    {"keyword": "FastAPI Developer",    "location": ""},
    {"keyword": "Backend Developer",    "location": "Bangalore"},
]


    EXPERIENCE_LEVELS = [0, 1, 2]
    PAGES   = 2
    JOB_AGE = 15

    seen_ids = set()
    all_jobs = []

    # 0. Fetch custom queued jobs from Google Sheets (if configured)
    queue_tab = os.getenv("GOOGLE_SHEET_QUEUE_TAB", "Job_Queue")
    try:
        from src.utils.google_sheets import fetch_queued_jobs_from_sheet
        import re
        raw_queue = fetch_queued_jobs_from_sheet(queue_tab)
        if raw_queue:
            q_count = 0
            for item in raw_queue:
                val = ""
                if isinstance(item, dict):
                    val = str(item.get("job_id") or item.get("job_url") or item.get("url") or item.get("id") or "")
                elif isinstance(item, (list, tuple)):
                    val = str(item[0]) if len(item) > 0 else ""
                else:
                    val = str(item)

                match = re.search(r'(\d{10,14})', val)
                if match:
                    jid = match.group(1)
                    if jid not in seen_ids:
                        seen_ids.add(jid)
                        try:
                            details = jc.get_job_details(jid)
                            raw_job = details.get("job") or details.get("jobDetails") or details
                            job_obj = jc._parse_job(raw_job)
                            if not job_obj.job_id:
                                job_obj.job_id = jid
                            job_obj.is_queued = True
                            all_jobs.append(job_obj)
                            q_count += 1
                        except Exception:
                            from src.models.models import Job
                            job_obj = Job(
                                job_id=jid,
                                title="Queued Custom Job",
                                company="N/A",
                                location="N/A",
                                experience="N/A",
                                salary="Not disclosed",
                                posted_date="Today",
                                apply_link=f"https://www.naukri.com/job-listings-{jid}",
                                is_queued=True
                            )
                            all_jobs.append(job_obj)
                            q_count += 1
            if q_count > 0:
                print(f"  {Fore.GREEN}[GOOGLE SHEET QUEUE]{Style.RESET_ALL} Loaded {q_count} manual jobs from tab '{queue_tab}'")
    except Exception as e:
        logger.debug(f"Queue fetch failed: {e}")

    # 1. Fetch personalized recommended jobs based on your Naukri profile
    try:
        recom_jobs = jc.get_recommended_jobs()
        for job in recom_jobs:
            job_id = getattr(job, "id", None) or getattr(job, "job_id", None)
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(job)
        print(f"  {Fore.GREEN}[RECOMMENDED]{Style.RESET_ALL}  Fetched {len(recom_jobs)} profile-recommended jobs ({len(all_jobs)} new)")
    except Exception as e:
        print(f"  {Fore.YELLOW}[RECOMMENDED SKIP]{Style.RESET_ALL}  Could not fetch recommended feed: {e}")

    print_section_title(
        f"fetching search jobs  ({len(BQUERIES)} queries x {len(EXPERIENCE_LEVELS)} exp x {PAGES} pages)"
    )

    for q in BQUERIES:
        for exp in EXPERIENCE_LEVELS:
            for page in range(1, PAGES + 1):
                try:
                    jobs = jc.search_jobs(
                        keyword=q["keyword"],
                        location=q["location"],
                        experience=exp,
                        job_age=JOB_AGE,
                        page=page,
                    )

                    # Deduplicate across queries using job_id.
                    new_jobs = []
                    for job in jobs:
                        job_id = getattr(job, "id", None) or getattr(job, "job_id", None)
                        if job_id and job_id not in seen_ids:
                            seen_ids.add(job_id)
                            new_jobs.append(job)

                    all_jobs.extend(new_jobs)
                    print_fetch_progress(
                        q["keyword"], q["location"], exp, page,
                        fetched=len(jobs),
                        new=len(new_jobs),
                    )

                    if len(jobs) == 0:
                        break

                    time.sleep(1.2)

                except Exception as e:
                    print(
                        f"  {Fore.RED}[FAIL]{Style.RESET_ALL}  "
                        f"{q['keyword']} @ {q['location']}  "
                        f"exp={exp} p={page}  ->  {e}"
                    )
                    time.sleep(3)

    print(f"\n  {Fore.CYAN}Total unique jobs collected: {Style.BRIGHT}{len(all_jobs)}{Style.RESET_ALL}")
    return all_jobs


# ----------------------------------------------------------------------------------
# Main runner — orchestrates the full agent run
# ----------------------------------------------------------------------------------

def run_agent(client=None, auto_bump=None, max_applies=None):
    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
    ollama_url   = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    auto_apply = os.getenv("AUTO_APPLY", "false").lower() in {"1", "true", "yes", "on"}
    
    if auto_bump is None:
        auto_bump = os.getenv("AUTO_BUMP_PROFILE", "true").lower() in {"1", "true", "yes", "on"}

    daily_apply_limit = max_applies or int(os.getenv("DAILY_APPLY_LIMIT", "20"))

    # Step 1: authenticate and establish session.
    print_section_title("logging in to naukri")
    if client is None:
        client = NaukriLoginClient(username, password)
        client.login()
    print(f"  {Fore.GREEN}Logged in as {Fore.YELLOW}{username}{Style.RESET_ALL}")

    # Optional: Profile timestamp bump ("Active Today" for recruiters)
    if auto_bump:
        try:
            from src.utils.profile_updater import bump_profile
            bump_profile(client)
        except Exception as e:
            logger.warning(f"Profile bump skipped: {e}")
    
    # Check Google Sheets sync status
    target_tab = os.getenv("GOOGLE_SHEET_TAB_NAME", "Applied_Jobs")
    queue_tab = os.getenv("GOOGLE_SHEET_QUEUE_TAB", "Job_Queue")
    if os.getenv("GOOGLE_SHEET_WEBHOOK_URL"):
        print(f"  {Fore.GREEN}Google Sheets sync : ENABLED (Webhook -> Tab: '{target_tab}', Queue: '{queue_tab}'){Style.RESET_ALL}")
    elif os.getenv("GOOGLE_SHEET_NAME") or os.getenv("GOOGLE_SHEET_ID"):
        print(f"  {Fore.GREEN}Google Sheets sync : ENABLED (Service Account -> Tab: '{target_tab}'){Style.RESET_ALL}")
    else:
        print(f"  {Fore.YELLOW}Google Sheets sync : DISABLED (set GOOGLE_SHEET_WEBHOOK_URL in .env to enable){Style.RESET_ALL}")

    # Step 2: fetch raw jobs from search API.
    jc   = NaukriJobClient(client)
    jobs = fetch_all_jobs(jc)

    if not jobs:
        print(f"\n{Fore.YELLOW}  No jobs found. Exiting.{Style.RESET_ALL}")
        return {"total_found": 0, "applied": 0}

    # Step 3: run AI filter pipeline. Jobs are scored and ranked. Only those
    # above the pipeline's threshold are passed to the apply loop.
    ai_score_limit = int(os.getenv("AI_SCORE_LIMIT", "15"))
    print_section_title("running AI filter pipeline")
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        print(f"  Engine: Cloud AI (Groq: {groq_model}) | AI evaluation cap: {ai_score_limit} jobs")
    else:
        print(f"  Engine: Local Ollama ({ollama_url} | model: {ollama_model}) | AI evaluation cap: {ai_score_limit} jobs")
    pipeline   = JobFilterPipeline2(ollama_url=ollama_url, ollama_model=ollama_model, ai_score_limit=ai_score_limit)
    final_jobs = pipeline.run(jobs)

    # Build a lookup from job_id to the pipeline result dict (score, ai_detail, etc.)
    score_map    = {j["job_id"]: j for j in final_jobs}
    allow        = set(score_map.keys())

    # Ensure custom queued jobs from Google Sheet bypass AI drops and get applied with top priority
    for j in jobs:
        if getattr(j, "is_queued", False):
            allow.add(j.job_id)
            if j.job_id not in score_map:
                score_map[j.job_id] = {
                    "job_id": j.job_id,
                    "score": 100,
                    "ai_detail": "Queued manually via Google Sheet table",
                }

    print_pipeline_results(final_jobs)

    # Step 4: apply loop. Iterates only over jobs that passed the AI filter.
    applied_jobs_set = load_applied_jobs()

    # Prioritize queued jobs first, followed by regular matches
    queued_allowed = [j for j in jobs if getattr(j, "is_queued", False) and j.job_id in allow]
    regular_allowed = [j for j in jobs if not getattr(j, "is_queued", False) and j.job_id in allow]
    allowed_jobs = queued_allowed + regular_allowed

    if not auto_apply:
        print_section_title("DRY RUN — no applications will be submitted")
        for index, job in enumerate(allowed_jobs, start=1):
            meta = score_map.get(job.job_id, {})
            print_job_header(index, len(allowed_jobs), job, meta.get("score"), meta.get("ai_detail"))
        print("\nSet AUTO_APPLY=true in .env only when you are ready to submit applications.")
        print_summary(len(jobs), len(allowed_jobs), 0, 0, 0)
        return {"total_found": len(jobs), "applied": 0}

    applied_count = 0
    skipped_ext   = 0
    failed_count  = 0
    applied_jobs_list = []

    print_section_title(f"applying to {len(allowed_jobs)} filtered jobs (Daily limit: {daily_apply_limit})")

    for index, job in enumerate(allowed_jobs, start=1):
        if applied_count >= daily_apply_limit:
            print(f"\n  {Fore.YELLOW}Daily application limit reached ({daily_apply_limit}). Stopping apply loop to protect account.{Style.RESET_ALL}")
            break

        meta      = score_map.get(job.job_id, {})
        score     = meta.get("score")
        ai_detail = meta.get("ai_detail")

        print_job_header(
            index=index,
            total=len(allowed_jobs),
            job=job,
            score=score,
            ai_detail=ai_detail,
        )

        # Skip jobs already recorded as applied.
        if job.job_id in applied_jobs_set:
            print(f"  {Fore.YELLOW}Status  :  Skipped — already applied (local history){Style.RESET_ALL}")
            if getattr(job, "is_queued", False):
                try:
                    from src.utils.google_sheets import update_queued_job_status
                    update_queued_job_status(job.job_id, status="APPLIED")
                except Exception:
                    pass
            continue

        # External apply jobs cannot be submitted via the API, skip them.
        if jc.is_external_apply(job.job_id):
            print_status_skipped_external()
            skipped_ext += 1
            if getattr(job, "is_queued", False):
                try:
                    from src.utils.google_sheets import update_queued_job_status
                    update_queued_job_status(job.job_id, status="SKIPPED (External Apply)")
                except Exception:
                    pass
            continue

        # Use the first two tags as mandatory skills and the rest as optional.
        # This maps the job's skill tags to the apply payload fields.
        mandatory = job.tags[:2] if job.tags else []
        optional  = job.tags[2:] if len(job.tags) > 2 else []

        try:
            result   = jc.apply_job(
                job,
                mandatory_skills=mandatory,
                optional_skills=optional,
                source="search",
            )

            job_result = (result.get("jobs") or [{}])[0]

            # If the apply response contains a questionnaire, answer it and
            # re-submit. This is a two-step apply flow used by some employers.
            if job_result.get("questionnaire"):
                print_questionnaire_notice()
                sid    = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"
                result = jc.handle_static_questionnaire_and_apply(
                    job,
                    questionnaire=job_result["questionnaire"],
                    sid=sid,
                    mandatory_skills=mandatory,
                    optional_skills=optional,
                    source="search",
                )

            applied_at = datetime.utcnow().strftime("%H:%M:%S UTC")
            print_status_applied(applied_at)
            save_applied_job(job, score=score, ai_detail=ai_detail)
            applied_jobs_set.add(job.job_id)
            applied_count += 1
            applied_jobs_list.append({"title": job.title, "company": job.company, "score": score})

            if getattr(job, "is_queued", False):
                try:
                    from src.utils.google_sheets import update_queued_job_status
                    update_queued_job_status(job.job_id, status="APPLIED")
                    print(f"  {Fore.GREEN}[Google Sheet Queue]{Style.RESET_ALL} Updated status to APPLIED in sheet")
                except Exception as err:
                    logger.debug(f"Queue status update failed: {err}")

        except Exception as e:
            print_status_failed(e)
            failed_count += 1
            if getattr(job, "is_queued", False):
                try:
                    from src.utils.google_sheets import update_queued_job_status
                    update_queued_job_status(job.job_id, status="FAILED")
                except Exception:
                    pass

        # Delay between applies to avoid triggering rate limits.
        time.sleep(3)

    # Step 5: print final run summary.
    print_summary(
        total_found=len(jobs),
        total_allowed=len(allowed_jobs),
        applied=applied_count,
        skipped_ext=skipped_ext,
        failed=failed_count,
    )

    # Step 6: dispatch mobile notification if configured
    try:
        from src.utils.notifier import send_mobile_notification
        send_mobile_notification(
            applied_count=applied_count,
            total_found=len(jobs),
            skipped_ext=skipped_ext,
            failed_count=failed_count,
            top_jobs=applied_jobs_list
        )
    except Exception as e:
        logger.debug(f"Mobile notification skipped: {e}")

    return {
        "total_found": len(jobs),
        "total_allowed": len(allowed_jobs),
        "applied": applied_count,
        "skipped_ext": skipped_ext,
        "failed": failed_count,
    }

if __name__ == "__main__":
    run_agent()