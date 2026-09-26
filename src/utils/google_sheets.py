import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Standard column headers for Google Sheets
SHEET_HEADERS = [
    "Applied At",
    "Job Title",
    "Company",
    "Location",
    "AI Score",
    "Match Detail",
    "Experience",
    "Salary",
    "Job URL",
    "Job ID"
]

_gspread_client = None
_gspread_worksheet = None


def _get_gspread_worksheet():
    """Lazily initializes and caches gspread worksheet connection."""
    global _gspread_client, _gspread_worksheet
    if _gspread_worksheet is not None:
        return _gspread_worksheet

    creds_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not os.path.exists(creds_file):
        return None

    try:
        import gspread
        _gspread_client = gspread.service_account(filename=creds_file)
        if sheet_id:
            spreadsheet = _gspread_client.open_by_key(sheet_id)
        elif sheet_name:
            spreadsheet = _gspread_client.open(sheet_name)
        else:
            return None

        _gspread_worksheet = spreadsheet.sheet1
        
        # Ensure header row exists if sheet is empty
        try:
            existing_values = _gspread_worksheet.row_values(1)
            if not existing_values:
                _gspread_worksheet.append_row(SHEET_HEADERS)
        except Exception:
            pass

        return _gspread_worksheet
    except Exception as e:
        logger.warning(f"Failed to initialize gspread: {e}")
        return None


def append_job_to_sheet(
    job_id: str,
    title: str,
    company: str,
    location: str = "",
    score: Optional[int] = None,
    ai_detail: str = "",
    experience: str = "",
    salary: str = "",
    applied_at: Optional[str] = None,
    tab_name: Optional[str] = None,
) -> bool:
    """
    Appends an applied job to Google Sheets.
    Supports targeting a specific worksheet/tab (e.g. for different laptops/profiles).
    """
    if not applied_at:
        applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    target_tab = tab_name or os.getenv("GOOGLE_SHEET_TAB_NAME", "Applied_Jobs")
    job_url = f"https://www.naukri.com/job-listings-{job_id}"
    score_val = str(score) if score is not None else ""

    payload = {
        "action": "append",
        "tab_name": target_tab,
        "applied_at": applied_at,
        "title": title,
        "company": company,
        "location": location or "",
        "score": score_val,
        "ai_detail": ai_detail or "",
        "experience": experience or "",
        "salary": salary or "",
        "job_url": job_url,
        "job_id": str(job_id)
    }

    # Method 1: Google Apps Script Webhook (Zero GCP Setup required)
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    if webhook_url:
        try:
            import requests
            resp = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
                allow_redirects=True
            )
            if resp.status_code in (200, 201, 302):
                return True
            else:
                logger.warning(f"Google Sheet webhook responded with code {resp.status_code}: {resp.text[:120]}")
                return False
        except Exception as e:
            logger.warning(f"Google Sheet webhook sync failed: {e}")
            return False

    # Method 2: gspread via Service Account
    ws = _get_gspread_worksheet()
    if ws is not None:
        try:
            row = [
                applied_at,
                title,
                company,
                location or "",
                score_val,
                ai_detail or "",
                experience or "",
                salary or "",
                job_url,
                str(job_id)
            ]
            ws.append_row(row)
            return True
        except Exception as e:
            logger.warning(f"gspread append_row failed: {e}")
            return False

    return False


def fetch_queued_jobs_from_sheet(queue_tab: Optional[str] = None) -> list:
    """
    Fetches custom pending jobs listed in a Google Sheet tab (e.g. 'Job_Queue').
    Allows user to paste job URLs/IDs in Google Sheets from their phone/browser,
    which the agent will ingest and apply to!
    """
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    if not webhook_url:
        return []

    target_tab = queue_tab or os.getenv("GOOGLE_SHEET_QUEUE_TAB", "Job_Queue")
    try:
        import requests
        resp = requests.get(
            webhook_url,
            params={"action": "get_queue", "tab_name": target_tab},
            timeout=15,
            allow_redirects=True
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("jobs", [])
    except Exception as e:
        logger.debug(f"Could not fetch queued jobs from Google Sheet: {e}")
    return []


def update_queued_job_status(job_id: str, status: str = "APPLIED", queue_tab: Optional[str] = None) -> bool:
    """
    Marks a queued job in the Google Sheet queue tab as APPLIED, SKIPPED, etc.
    """
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL")
    if not webhook_url:
        return False

    target_tab = queue_tab or os.getenv("GOOGLE_SHEET_QUEUE_TAB", "Job_Queue")
    payload = {
        "action": "update_status",
        "queue_tab": target_tab,
        "job_id": str(job_id),
        "status": status
    }
    try:
        import requests
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
            allow_redirects=True
        )
        return resp.status_code in (200, 201, 302)
    except Exception as e:
        logger.debug(f"Failed to update queued job status: {e}")
        return False
