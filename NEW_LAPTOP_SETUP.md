# Setting Up NopeRi on a New Laptop

This guide explains how to set up NopeRi on a **brand-new laptop** in 3 minutes, connect it to your **existing Google Sheet** using a dedicated new tab, and configure custom jobs to be applied from a **Job Queue** table.

---

## Step 1: Install Prerequisites on the New Laptop

1. **Python 3.10+**: Download & install from [python.org](https://www.python.org/downloads/) *(Check the box: **"Add Python to PATH"** during install)*.
2. **Git**: Download & install from [git-scm.com](https://git-scm.com/).
3. **Ollama**: Download & install from [ollama.ai](https://ollama.ai/), then open a terminal and run:
   ```powershell
   ollama pull qwen2.5:14b
   ```
   *(Or `ollama pull qwen2.5:7b` if the new laptop has less than 16GB RAM).*

---

## Step 2: Clone the Codebase & Install Dependencies

Open PowerShell on your new laptop and run:

```powershell
git clone https://github.com/adhi2k/Naukri-automation.git
cd Naukri-automation

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

---

## Step 3: Configure `.env` on the New Laptop

Create a `.env` file in the folder:

```env
USERNAME=adhithyad.1.1.2@gmail.com
PASSWORD=YourNaukriPasswordHere

AUTO_APPLY=true
DAILY_APPLY_LIMIT=20
AI_SCORE_LIMIT=15

OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:14b

# --- SAME GOOGLE SHEET, NEW TABLES ---
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/AKfycbyokuU4Qsc3dp1u9-uMs8TMwZfpHgPV-zzwAmmU2psQaZNVvDoO50HQ4E__K4oE01mk/exec
GOOGLE_SHEET_TAB_NAME=Laptop2_Applied
GOOGLE_SHEET_QUEUE_TAB=Laptop2_Queue

# --- MOBILE NOTIFICATION ---
NTFY_TOPIC=noperi_adhithya_jobs
```

> [!TIP]
> **Notice `GOOGLE_SHEET_TAB_NAME=Laptop2_Applied`**:
> You don't need to create this tab in Google Sheets manually! When the new laptop runs, the webhook will automatically create the tab `Laptop2_Applied` with pre-formatted headers.
> Laptop 1's applied jobs remain in `Applied_Jobs` without getting mixed up.

---

## Step 4: Update the Google Apps Script Webhook (One-Time)

To support multiple tabs and the Job Queue, make sure your Apps Script contains the updated script:
1. Open your Google Sheet in a browser.
2. Go to **Extensions** > **Apps Script**.
3. Replace the contents of `Code.gs` with the updated code in [GOOGLE_SHEET_SETUP.md](file:///c:/Users/adhit/Downloads/NopeRi-Local-Qwen14-Working/NopeRi-main/GOOGLE_SHEET_SETUP.md).
4. Click **Deploy** > **Manage deployments** > **Edit (`✏️`)** > Version: **`New version`** > **Deploy**.

---

## Step 5: How to Feed Custom Jobs to the New Laptop from Google Sheet

Want to apply to specific jobs you find while browsing on your phone or computer?

1. In your Google Sheet, open the `Laptop2_Queue` tab (or `Job_Queue`).
2. Add your jobs:
   | Column A (Job URL or ID) | Column B (Status) | Column C (Updated At) |
   | :--- | :--- | :--- |
   | `https://www.naukri.com/job-listings-python-dev-123456789012` | `PENDING` | *(leave blank)* |
   | `010124005678` | `PENDING` | *(leave blank)* |
3. When NopeRi runs on the new laptop:
   - It reads all pending jobs from this table first.
   - It prioritizes and applies to them with top priority.
   - It marks Column B as `APPLIED` with the timestamp in Column C.
   - It sends a notification to your phone!

---

## Step 6: Test & Schedule on the New Laptop

### 1. Test System Health:
```powershell
python verify_system.py
```

### 2. Test Queue Reading:
```powershell
python -c "from src.utils.google_sheets import fetch_queued_jobs_from_sheet; print(fetch_queued_jobs_from_sheet('Laptop2_Queue'))"
```

### 3. Install Silent Daily Background Task:
```powershell
python setup_daily_schedule.py
```
*(Runs completely in the background at 09:00 AM every day or as soon as you open the laptop).*
