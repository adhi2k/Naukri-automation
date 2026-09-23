"""
src/utils/profile_updater.py

Profile bump and refresh utility.
Automatically touches your Naukri profile (headline / summary) to keep your
account status as 'Active Today' / 'Profile Updated: Today' in recruiter searches.
"""

import os
import logging
from datetime import datetime
from typing import Optional
from colorama import Fore, Style

logger = logging.getLogger(__name__)

DEFAULT_HEADLINE = "Software Developer | B.Tech AI & Data Science | Python, Java, FastAPI, PostgreSQL, REST APIs"

def bump_profile(client, headline: Optional[str] = None, summary: Optional[str] = None) -> bool:
    """
    Updates the candidate's profile on Naukri to refresh the 'Last Updated' timestamp.
    Recruiters filter candidate searches by 'Active in Last 1 Day' or 'Profile Updated Recently'.
    """
    try:
        base_headline = headline or os.getenv("PROFILE_HEADLINE") or DEFAULT_HEADLINE
        # Alternating trailing space ensures Naukri always detects a field mutation
        # even if the user doesn't change the actual wording
        day = datetime.now().day
        toggled_headline = base_headline.rstrip() + (" " if (day % 2 == 0) else "")

        print(f"  {Fore.CYAN}[PROFILE REFRESH]{Style.RESET_ALL} Bumping profile timestamp...")
        result = client.update_profile(headline=toggled_headline, summary=summary)

        if result.status_code in (200, 201, 204):
            print(f"  {Fore.GREEN}[PROFILE REFRESH]{Style.RESET_ALL} Profile headline updated successfully!")
            print(f"  {Fore.GREEN}[ACTIVE TODAY]{Style.RESET_ALL} Profile marked 'Active Today' for recruiters.")
            return True
        else:
            print(f"  {Fore.YELLOW}[PROFILE REFRESH]{Style.RESET_ALL} Naukri returned status {result.status_code}")
            return False

    except Exception as e:
        logger.warning(f"Profile refresh warning (non-fatal): {e}")
        print(f"  {Fore.YELLOW}[PROFILE REFRESH NOTICE]{Style.RESET_ALL} Could not bump profile: {e}")
        return False
