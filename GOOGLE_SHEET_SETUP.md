# Google Sheets Real-time Sync & Job Queue Setup Guide

You can sync all applied jobs from NopeRi directly to your personal Google Sheet in real-time, connect multiple laptops/profiles to different tabs in the same spreadsheet, and even manually feed jobs from your phone or browser into a **Job Queue** table!

---

## Google Apps Script Webhook (Multi-Tab & Job Queue Enabled)

### Step 1: Open Your Existing Google Sheet
1. Open your **Naukri Applied Jobs** spreadsheet in Google Sheets.
2. In the top menu, click **Extensions** > **Apps Script**.

### Step 2: Replace `Code.gs` with the Upgraded Script
1. Press **`Ctrl + A`** (or `Cmd + A` on Mac) and press **Delete / Backspace** to empty `Code.gs`.
2. Paste the following complete script:

```javascript
/**
 * NopeRi Multi-Device & Job Queue Webhook
 * Supports writing to custom tabs (per laptop/profile) and reading/updating Job Queue
 */

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var data = JSON.parse(e.postData.contents);
    var action = data.action || "append";

    // ----------------------------------------------------
    // Action 1: Update Job Queue Status (Mark as APPLIED/SKIPPED)
    // ----------------------------------------------------
    if (action === "update_status") {
      var queueTabName = data.queue_tab || "Job_Queue";
      var qSheet = ss.getSheetByName(queueTabName);
      if (qSheet) {
        var values = qSheet.getDataRange().getValues();
        var targetId = String(data.job_id || "");
        for (var i = 1; i < values.length; i++) {
          var cellVal = String(values[i][0] || "");
          if (cellVal.indexOf(targetId) !== -1) {
            // Update Status column (column B)
            qSheet.getRange(i + 1, 2).setValue(data.status || "APPLIED");
            // Update Timestamp (column C)
            var nowStr = Utilities.formatDate(new Date(), "GMT+5:30", "yyyy-MM-dd HH:mm:ss");
            qSheet.getRange(i + 1, 3).setValue(nowStr);
            break;
          }
        }
      }
      return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // ----------------------------------------------------
    // Action 2: Append Applied Job to Target Tab
    // ----------------------------------------------------
    var targetTabName = data.tab_name || "Applied_Jobs";
    var sheet = ss.getSheetByName(targetTabName);
    
    // Automatically create tab if it doesn't exist yet
    if (!sheet) {
      sheet = ss.insertSheet(targetTabName);
    }

    // If new or empty tab, set up styled headers
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

    // Append the job record
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

    return ContentService.createTextOutput(JSON.stringify({ status: "success", tab: targetTabName }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var params = e ? e.parameter : {};
    var queueTabName = params.tab_name || "Job_Queue";
    var sheet = ss.getSheetByName(queueTabName);

    // Create queue sheet if it doesn't exist yet
    if (!sheet) {
      sheet = ss.insertSheet(queueTabName);
      sheet.appendRow(["Job URL or ID", "Status", "Updated At", "Notes"]);
      sheet.getRange(1, 1, 1, 4).setFontWeight("bold").setBackground("#cfe2f3");
      sheet.setFrozenRows(1);
      return ContentService.createTextOutput(JSON.stringify({ status: "success", jobs: [] }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = sheet.getDataRange().getValues();
    var jobs = [];

    // Skip header row
    for (var i = 1; i < data.length; i++) {
      var jobRef = String(data[i][0] || "").trim();
      var status = String(data[i][1] || "").trim().toUpperCase();

      // Only pick jobs that are not already APPLIED or SKIPPED
      if (jobRef && status !== "APPLIED" && !status.startsWith("SKIPPED")) {
        jobs.push({
          row: i + 1,
          job_id: jobRef,
          status: status || "PENDING"
        });
      }
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "success", count: jobs.length, jobs: jobs }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

### Step 3: Deploy as New Version
1. At the top right of Apps Script, click **Deploy** > **Manage deployments**.
2. Click the **Pencil icon (`✏️`)** (Edit) on your existing deployment.
3. Under **Version**, select **`New version`**.
4. Click **Deploy**.
*(The Webhook URL remains exactly the same!)*

---

## How Multi-Device & Job Queue Works

### 1. Connecting a Second Laptop to a New Tab
In your new laptop's `.env`, use the **same** `GOOGLE_SHEET_WEBHOOK_URL`, but specify a unique tab name:
```env
GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/AKfycbyokuU4Qsc3dp1u9-uMs8TMwZfpHgPV-zzwAmmU2psQaZNVvDoO50HQ4E__K4oE01mk/exec
GOOGLE_SHEET_TAB_NAME=Laptop2_Applied
GOOGLE_SHEET_QUEUE_TAB=Laptop2_Queue
```
- When Laptop 2 runs, it will **automatically create** the tab `Laptop2_Applied` in your Google Sheet!
- Laptop 1 records will stay in `Applied_Jobs` (or whatever tab Laptop 1 uses).

### 2. How to Use the Job Queue (Apply to Specific Jobs from Phone / Browser)
You can manually queue jobs in Google Sheets without running a manual command!

1. Open your Google Sheet on your phone or browser.
2. In the tab named `Job_Queue` (or `Laptop2_Queue`):
   - **Column A (`Job URL or ID`)**: Paste the Naukri job URL or 12-digit job ID.
     *(Example: `https://www.naukri.com/job-listings-python-developer-company-010124001234` or `010124001234`)*
   - **Column B (`Status`)**: Leave blank or type `PENDING`.
3. When NopeRi runs:
   - It fetches all pending jobs from this table.
   - It prioritizes them **at the top** of the apply queue.
   - Once applied, NopeRi automatically updates **Column B** to `APPLIED` with the timestamp in **Column C**!

---

## Testing Your Setup

To test both reading the queue and writing to your tab:
```powershell
python -c "from src.utils.google_sheets import fetch_queued_jobs_from_sheet; print('Queue jobs:', fetch_queued_jobs_from_sheet())"
```
