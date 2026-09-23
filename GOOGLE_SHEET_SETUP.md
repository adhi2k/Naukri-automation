# Google Sheets Real-time Sync Setup Guide

You can sync all applied jobs from NopeRi directly to your personal Google Sheet in real-time.

There are two methods available:
1. **Google Apps Script Webhook (Recommended — takes ~60 seconds, no Google Cloud project needed)**
2. **gspread Service Account (For advanced Google Cloud Console users)**

---

## Method 1: Google Apps Script Webhook (Easiest & Fastest)

### Step 1: Create a Google Sheet
1. Open [Google Sheets](https://sheets.new) and create a new blank spreadsheet.
2. Name it something like **Naukri Applied Jobs**.

### Step 2: Open Apps Script
1. In the top menu, click **Extensions** > **Apps Script**.
2. Press **`Ctrl + A`** (or `Cmd + A` on Mac) and press **Delete / Backspace** to completely empty the editor.
   *(Make sure the default `function myFunction() { }` is deleted so there are no extra curly braces!)*
3. Paste **only** the code below into `Code.gs`:

```javascript
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // If the sheet is empty, create formatted header row
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
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
      ]);
      sheet.getRange(1, 1, 1, 10).setFontWeight("bold").setBackground("#d9ead3");
      sheet.setFrozenRows(1);
    }
    
    // Append the applied job record
    sheet.appendRow([
      data.applied_at || Utilities.formatDate(new Date(), "GMT+5:30", "yyyy-MM-dd HH:mm:ss"),
      data.title || "",
      data.company || "",
      data.location || "",
      data.score || "",
      data.ai_detail || "",
      data.experience || "",
      data.salary || "",
      data.job_url || "",
      data.job_id || ""
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

### Step 3: Deploy as Web App
1. At the top right of Apps Script, click **Deploy** > **New deployment**.
2. Click the gear icon (`⚙️`) next to "Select type" and choose **Web app**.
3. Fill in:
   - **Description**: `NopeRi Webhook`
   - **Execute as**: `Me (<your_email>)`
   - **Who has access**: `Anyone` *(Crucial so the script can post job rows without complicated OAuth)*
4. Click **Deploy**.
5. Click **Authorize access**, select your Google account, click *Advanced* > *Go to Untitled project (unsafe)*, and click **Allow**.
6. Copy the generated **Web app URL** (starts with `https://script.google.com/macros/s/.../exec`).

### Step 4: Add to your `.env`
Open your `.env` file and paste the Webhook URL:
```env
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec
```

---

## Method 2: Google Cloud Service Account (`gspread`)

If you already have a Google Cloud Service Account JSON key:
1. Save your service account JSON file in this directory as `service_account.json`.
2. Share your Google Sheet with the `client_email` listed in the JSON file (as Editor).
3. In `.env`, add:
```env
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
GOOGLE_SHEET_NAME=Naukri Applied Jobs
# or GOOGLE_SHEET_ID=1AbC...
```

---

## Testing & Syncing Existing Jobs

To test your connection and immediately sync the 4 jobs already applied today:
```powershell
python sync_to_google_sheet.py
```

Whenever you run `python apply_agent.py`, each newly applied job will automatically appear in your Google Sheet!
