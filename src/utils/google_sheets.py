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
) -> bool:
    """
    Appends an applied job to Google Sheets.
    
    Supports two methods:
    1. GOOGLE_SHEET_WEBHOOK_URL: Webhook URL from a Google Apps Script Web App (Easiest setup).
    2. gspread Service Account: GOOGLE_SERVICE_ACCOUNT_FILE + (GOOGLE_SHEET_ID or GOOGLE_SHEET_NAME).

    Returns True if successfully sent/updated, False otherwise.
    Does not crash or raise exceptions if syncing fails.
    """
    if not applied_at:
        applied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    job_url = f"https://www.naukri.com/job-listings-{job_id}"
    score_val = str(score) if score is not None else ""

    payload = {
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
                logger.warning(f"Google Sheet webhook responded with code {resp.status_code}: {resp.text}")
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
