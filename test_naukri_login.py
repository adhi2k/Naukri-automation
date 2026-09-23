import os
from dotenv import load_dotenv
from src.client.naukri_client import NaukriLoginClient

load_dotenv(override=True)
username = os.getenv("NAUKRI_USERNAME") or os.getenv("USERNAME")
password = os.getenv("NAUKRI_PASSWORD") or os.getenv("PASSWORD")
if not username or not password:
    raise SystemExit("Set USERNAME (or NAUKRI_USERNAME) and PASSWORD in .env first.")

client = NaukriLoginClient(username, password)
client.login()
print("NAUKRI_LOGIN_OK")
