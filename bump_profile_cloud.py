"""
bump_profile_cloud.py

Lightweight script to bump your Naukri profile timestamp in GitHub Actions or cloud cron.
- Requires NO Chrome / Selenium
- Requires NO local Ollama
- Completes in ~3 seconds
- Updates profile headline so you are shown as "Active Today" to recruiters.

Usage:
    python bump_profile_cloud.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

from src.client.naukri_client import NaukriLoginClient
from src.utils.profile_updater import bump_profile

def main():
    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
    headline = os.getenv("PROFILE_HEADLINE")

    if not username or not password:
        print("ERROR: Missing NAUKRI_USERNAME or NAUKRI_PASSWORD environment variable.")
        sys.exit(1)

    print(f"Authenticating as {username} (Direct API mode)...")
    os.environ["NAUKRI_LOGIN_MODE"] = "direct"
    os.environ["NAUKRI_BROWSER_FALLBACK"] = "false"

    client = NaukriLoginClient(username, password)
    try:
        client.login()
        print("Login successful.")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    print("Refreshing profile headline / timestamp...")
    success = bump_profile(client, headline=headline)
    if success:
        print("SUCCESS: Profile timestamp updated. Profile marked 'Active Today' for recruiters!")
        sys.exit(0)
    else:
        print("FAILED: Profile update did not succeed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
