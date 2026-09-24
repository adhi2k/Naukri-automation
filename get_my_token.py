"""
get_my_token.py
Helper script to fetch your active Naukri session token (nauk_at)
so you can add it as a secret in GitHub Actions.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

from src.client.naukri_client import NaukriLoginClient

def main():
    username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")

    print(f"Logging in to fetch token for {username}...")
    client = NaukriLoginClient(username, password)
    sess = client.login()

    print("\n" + "=" * 60)
    print("YOUR NAUKRI_SESSION_TOKEN:")
    print("=" * 60)
    print(sess.bearer_token)
    print("=" * 60)
    print("\nCopy the token above and add it as a Secret named:")
    print("  NAUKRI_SESSION_TOKEN")
    print("in: https://github.com/adhi2k/Naukri-automation/settings/secrets/actions\n")

if __name__ == "__main__":
    main()
