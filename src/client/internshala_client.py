"""
src/client/internshala_client.py

Autonomous Internshala Job & Internship Client:
- Headless Playwright / Session automation for Internshala.com
- Scrapes matching software, AI, and developer internships/jobs
- Form fills cover letter, availability ("Immediately"), and custom screening answers
- Syncs with Google Sheets (tab: 'Internshala_Applied') and local CSV
"""

import os
import re
import csv
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from colorama import Fore, Style

logger = logging.getLogger(__name__)

INTERNSHALA_BASE = "https://internshala.com"
INTERNSHALA_LOGIN_URL = "https://internshala.com/login/user"
INTERNSHALA_CSV = "applied_internshala.csv"


class InternshalaClient:
    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        cover_letter: Optional[str] = None,
        headless: bool = True,
    ):
        self.email = email or os.getenv("INTERNSHALA_EMAIL")
        self.password = password or os.getenv("INTERNSHALA_PASSWORD")
        self.cover_letter = cover_letter or os.getenv(
            "INTERNSHALA_COVER_LETTER",
            "I am a passionate software engineer with hands-on experience in Python, AI, backend development, and REST APIs. I am eager to contribute and available to start immediately."
        )
        self.headless = headless
        self.applied_ids = self._load_applied_ids()

    def _load_applied_ids(self) -> set:
        if not os.path.exists(INTERNSHALA_CSV):
            return set()
        try:
            with open(INTERNSHALA_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return {row["job_id"] for row in reader if row.get("job_id")}
        except Exception:
            return set()

    def save_applied(self, job_dict: dict, score: Optional[int] = None, ai_detail: str = ""):
        file_exists = os.path.exists(INTERNSHALA_CSV)
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

        with open(INTERNSHALA_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        self.applied_ids.add(job_dict.get("job_id"))

        # Sync to Google Sheets
        try:
            from src.utils.google_sheets import append_job_to_sheet
            tab_name = os.getenv("INTERNSHALA_SHEET_TAB", "Internshala_Applied")
            append_job_to_sheet(
                job_id=job_dict.get("job_id", ""),
                title=job_dict.get("title", ""),
                company=job_dict.get("company", ""),
                location=job_dict.get("location", ""),
                score=score,
                ai_detail=ai_detail,
                experience=job_dict.get("duration", "Fresher / Intern"),
                salary=job_dict.get("stipend", ""),
                tab_name=tab_name,
                job_url=job_dict.get("job_url", "")
            )
        except Exception as e:
            logger.debug(f"Google Sheets sync skipped for Internshala: {e}")

    def fetch_listings(self, keywords: List[str] = None) -> List[dict]:
        """Scrapes current internship/fresher listings matching keywords."""
        keywords = keywords or ["python", "software-development", "artificial-intelligence", "data-science"]
        all_jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            for kw in keywords:
                search_url = f"{INTERNSHALA_BASE}/internships/{kw}-internship"
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2000)

                    # Extract internship cards
                    cards = page.locator(".individual_internship")
                    card_count = cards.count()

                    for i in range(card_count):
                        card = cards.nth(i)
                        try:
                            title_el = card.locator(".job-internship-name, .heading_4_5 a, .profile a").first
                            if not title_el.count():
                                continue
                            title = title_el.inner_text().strip()
                            rel_href = title_el.get_attribute("href") or ""
                            full_url = urljoin(INTERNSHALA_BASE, rel_href)

                            # Extract Job/Internship ID from URL
                            id_match = re.search(r"-(\d+)$", full_url)
                            job_id = id_match.group(1) if id_match else rel_href

                            if full_url in seen_urls or job_id in self.applied_ids:
                                continue

                            seen_urls.add(full_url)

                            comp_el = card.locator(".company-name, .link_display_like_text").first
                            company = comp_el.inner_text().strip() if comp_el.count() else "Internshala Employer"

                            loc_el = card.locator(".row-1-item.locations, .location_link").first
                            location = loc_el.inner_text().strip() if loc_el.count() else "Remote / India"

                            stipend_el = card.locator(".stipend").first
                            stipend = stipend_el.inner_text().strip() if stipend_el.count() else ""

                            # Extract tags/skills if present
                            tags = []
                            for tag_el in card.locator(".tags_container span").all():
                                tags.append(tag_el.inner_text().strip())

                            all_jobs.append({
                                "job_id": f"IS_{job_id}",
                                "id": f"IS_{job_id}",
                                "title": title,
                                "company": company,
                                "location": location,
                                "stipend": stipend,
                                "salary": stipend,
                                "tags": tags,
                                "job_url": full_url,
                                "description": f"Internshala Listing for {title} at {company}. Location: {location}. Stipend: {stipend}. Skills: {', '.join(tags)}",
                                "source": "internshala"
                            })
                        except Exception as e:
                            continue

                except Exception as e:
                    logger.warning(f"Internshala search failed for {kw}: {e}")

            browser.close()

        return all_jobs

    def apply_to_internship(self, page, job_url: str) -> bool:
        """Navigates to an internship page and submits application form."""
        try:
            page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)

            # Check if already applied on UI
            if page.locator("text=Already Applied").count() > 0:
                return True

            # Click Apply Now
            apply_btn = page.locator("#easy_apply_button, .apply_now_button, button:has-text('Apply now')").first
            if not apply_btn.count():
                return False

            apply_btn.click()
            page.wait_for_timeout(2500)

            # If redirected to proceed to application / resume review modal
            proceed_btn = page.locator("#proceed_to_application, button:has-text('Proceed to application')").first
            if proceed_btn.count() and proceed_btn.is_visible():
                proceed_btn.click()
                page.wait_for_timeout(2000)

            # Fill Cover letter
            cover_area = page.locator("textarea#cover_letter_text, textarea[name='cover_letter']").first
            if cover_area.count() and cover_area.is_visible():
                val = cover_area.input_value()
                if not val.strip():
                    cover_area.fill(self.cover_letter)

            # Handle radio buttons / availability ("Yes, I am available" / "Immediately")
            radio_yes = page.locator("input[type='radio'][value*='yes'], input[type='radio'][value*='immediate']").first
            if radio_yes.count() and radio_yes.is_visible():
                try:
                    radio_yes.check()
                except Exception:
                    pass

            # Submit Application
            submit_btn = page.locator("#submit, input[type='submit'][value*='Submit'], button:has-text('Submit')").first
            if submit_btn.count() and submit_btn.is_visible():
                submit_btn.click()
                page.wait_for_timeout(3000)
                return True

            return False
        except Exception as e:
            logger.warning(f"Error applying on Internshala ({job_url}): {e}")
            return False
