"""
src/client/indeed_client.py

Autonomous Indeed Job Search & Easy-Apply Client:
- Uses Playwright to search jobs on in.indeed.com
- Extracts direct job titles, companies, salaries, locations, and descriptions
- Filters via Groq Cloud LPU AI matcher
- Syncs to Google Sheets (tab: 'Indeed_Applied') and local CSV
"""

import os
import re
import csv
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, quote_plus
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from colorama import Fore, Style

logger = logging.getLogger(__name__)

INDEED_BASE = "https://in.indeed.com"
INDEED_CSV = "applied_indeed.csv"


class IndeedClient:
    def __init__(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        resume_path: Optional[str] = None,
        headless: bool = True,
    ):
        self.email = email or os.getenv("INDEED_EMAIL")
        self.phone = phone or os.getenv("INDEED_PHONE")
        self.resume_path = resume_path or os.getenv("RESUME_PDF_PATH")
        self.headless = headless
        self.applied_ids = self._load_applied_ids()

    def _load_applied_ids(self) -> set:
        if not os.path.exists(INDEED_CSV):
            return set()
        try:
            with open(INDEED_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return {row["job_id"] for row in reader if row.get("job_id")}
        except Exception:
            return set()

    def save_applied(self, job_dict: dict, score: Optional[int] = None, ai_detail: str = ""):
        file_exists = os.path.exists(INDEED_CSV)
        fieldnames = ["job_id", "title", "company", "location", "score", "ai_detail", "applied_at", "job_url"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = {
            "job_id": job_dict.get("job_id", ""),
            "title": job_dict.get("title", ""),
            "company": job_dict.get("company", ""),
            "location": job_dict.get("location", ""),
            "score": score if score is not None else "",
            "ai_detail": ai_detail,
            "applied_at": now_str,
            "job_url": job_dict.get("job_url", ""),
        }

        with open(INDEED_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        self.applied_ids.add(job_dict.get("job_id"))

        # Sync to Google Sheets
        try:
            from src.utils.google_sheets import append_job_to_sheet
            tab_name = os.getenv("INDEED_SHEET_TAB", "Indeed_Applied")
            append_job_to_sheet(
                job_id=job_dict.get("job_id", ""),
                title=job_dict.get("title", ""),
                company=job_dict.get("company", ""),
                location=job_dict.get("location", ""),
                score=score,
                ai_detail=ai_detail,
                experience="Entry / Fresher",
                salary=job_dict.get("salary", ""),
                tab_name=tab_name,
                job_url=job_dict.get("job_url", "")
            )
        except Exception as e:
            logger.debug(f"Google Sheets sync skipped for Indeed: {e}")

    def fetch_listings(self, keywords: List[str] = None, location: str = "India") -> List[dict]:
        """Scrapes Indeed India for matching job listings."""
        keywords = keywords or ["Python Developer", "Software Engineer Fresher", "Artificial Intelligence"]
        all_jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768}
            )
            page = context.new_page()

            for kw in keywords:
                search_url = f"{INDEED_BASE}/jobs?q={quote_plus(kw)}&l={quote_plus(location)}&fromage=3"
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2500)

                    job_cards = page.locator(".job_seen_beacon, .resultContent, [data-jk]")
                    card_count = job_cards.count()

                    for i in range(min(card_count, 25)):
                        card = job_cards.nth(i)
                        try:
                            # Extract Job key (jk)
                            jk = card.get_attribute("data-jk") or ""
                            if not jk:
                                anchor = card.locator("a[data-jk]").first
                                if anchor.count():
                                    jk = anchor.get_attribute("data-jk")

                            title_el = card.locator("h2.jobTitle span, a.jcs-JobTitle").first
                            if not title_el.count():
                                continue
                            title = title_el.inner_text().strip()

                            comp_el = card.locator("[data-testid='company-name']").first
                            company = comp_el.inner_text().strip() if comp_el.count() else "Indeed Employer"

                            loc_el = card.locator("[data-testid='text-location']").first
                            loc = loc_el.inner_text().strip() if loc_el.count() else location

                            sal_el = card.locator(".salary-snippet-container, [data-testid='attribute_snippet_testid']").first
                            salary = sal_el.inner_text().strip() if sal_el.count() else ""

                            job_id = f"IND_{jk}" if jk else f"IND_{re.sub(r'[^a-zA-Z0-9]', '', title)[:15]}"
                            job_url = f"{INDEED_BASE}/viewjob?jk={jk}" if jk else search_url

                            if job_url in seen_urls or job_id in self.applied_ids:
                                continue

                            seen_urls.add(job_url)

                            all_jobs.append({
                                "job_id": job_id,
                                "id": job_id,
                                "title": title,
                                "company": company,
                                "location": loc,
                                "salary": salary,
                                "tags": [kw, "Indeed"],
                                "job_url": job_url,
                                "description": f"Indeed Job Posting for {title} at {company}. Location: {loc}. Salary: {salary}.",
                                "source": "indeed"
                            })
                        except Exception:
                            continue

                except Exception as e:
                    logger.warning(f"Indeed fetch error for query '{kw}': {e}")

            browser.close()

        return all_jobs
