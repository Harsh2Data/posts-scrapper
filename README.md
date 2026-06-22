# LinkedIn Lead Bot

Finds LinkedIn posts from Indian IT-staffing/recruitment companies looking for
vendor partners, bench resources, or C2C/C2H consultants — and extracts the
poster's **name, company, email, and LinkedIn profile** into Excel, with no
duplicates.

---

## Quick Start (Web UI — recommended)

1. Install dependencies (first time only):
   ```
   pip install -r requirements.txt
   ```
2. Start the app:
   ```
   python app.py
   ```
3. Open **http://127.0.0.1:5000** in your browser.
4. Enter your LinkedIn email + password, click **Start Extraction**.
5. A Chrome window opens — if LinkedIn shows a security check, complete it
   there. The page shows a live log of what's happening.
6. When it finishes, download:
   - **Master Excel** — every lead ever found (all-time)
   - **Today's New Leads** — only leads found in this run

> Your credentials are used only in memory for this run. They are **never**
> saved to disk by the web app.

---

## Quick Start (Command line)

1. Create a `.env` file in this folder:
   ```
   LINKEDIN_EMAIL=your@email.com
   LINKEDIN_PASSWORD=yourpassword
   ```
2. Run:
   ```
   python full_pipeline.py
   ```

To run it automatically every day at 9 AM (Windows Scheduled Task):
```
python setup_windows_task.py
```
(or `python scheduler.py` to keep a script running in the background instead.)

---

## What it does (workflow)

```
1. Log into LinkedIn (Selenium + Chrome)
2. Search 20 staffing/vendor/bench-sales keywords (past week, newest first)
3. Scroll results, collect post cards that mention staffing/vendor/bench/C2C/C2H
4. Save each new post as inbox/post_*.txt
        ↓
5. Read every file in inbox/
6. Parse it: contact name, company, email, phone, service type, profile/post URL
7. Skip if: no email, not relevant, or duplicate (same email or profile already known)
8. Add good leads to leads_master.csv (the permanent record)
        ↓
9. Rebuild leads_master.xlsx        (ALL leads, ever — formatted, with clickable links)
10. Build daily_leads_YYYY_MM_DD.xlsx (only TODAY's new leads)
11. Write report_latest.txt          (summary of this run)
```

Steps 1-4 are "scraping". Steps 5-11 are "extraction/export". Both run back
to back every time, whether via the web UI or `full_pipeline.py`.

---

## Output files

| File | Contents |
|---|---|
| `leads_master.xlsx` | **Everything found so far**, one row per person. Open this to see all leads. |
| `daily_leads_YYYY_MM_DD.xlsx` | Only the new leads found **today**. |
| `leads_master.csv` | Same data as the master Excel, in CSV form (the actual database — never delete this). |
| `report_latest.txt` | Plain-text summary of the most recent run (posts scanned, new leads, duplicates, etc.) |
| `inbox/` | Posts waiting to be processed. |
| `inbox/processed/` | Posts already processed (kept for reference). |
| `seen_posts.txt` | Memory of posts already scraped, so they aren't fetched again. |

Each row in the Excel files has these columns:

`Contact Person | Company Name | Email | LinkedIn Profile | LinkedIn Post | Keyword | Date`

The **LinkedIn Profile** and **LinkedIn Post** columns are clickable links.

---

## Project files

| File | Purpose |
|---|---|
| `app.py` | Web server — the UI described above. |
| `templates/`, `static/` | Web page HTML/CSS/JS. |
| `full_pipeline.py` | Runs the scraper, then the extractor, in order. |
| `linkedin_scraper.py` | Logs into LinkedIn, searches keywords, saves raw posts to `inbox/`. |
| `linkedin_post_extractor.py` | Reads a post's text and pulls out name/company/email/etc. |
| `run_daily.py` | Processes `inbox/`, removes duplicates, writes the Excel files and report. |
| `requirements.txt` | Python packages needed. |
| `scheduler.py`, `setup_windows_task.py` | Optional: automate the CLI run on a daily schedule. |

---

## How leads are de-duplicated

A new post is only added if **both**:
- Its LinkedIn profile URL is not already in `leads_master.csv`, **and**
- Its email is not already in `leads_master.csv`

Otherwise it's logged as a duplicate and skipped. This means re-running the
tool is always safe — you'll only ever get *new* leads added to the master.

---

## Notes & limits

- **One job at a time.** The web app can only run one extraction at a time.
- **LinkedIn ToS.** Automated browsing/login of LinkedIn is against its Terms
  of Service and carries a risk of account restriction, regardless of whose
  account is used. Use a secondary/throwaway account if possible, and don't
  run it excessively.
- **Manual security checks.** If LinkedIn asks for a verification code or
  CAPTCHA, you must complete it in the Chrome window that opens — the tool
  waits up to 2 minutes for this.
- To use a **different LinkedIn account**: just type different credentials
  into the web form (or edit `.env` for CLI use). No API keys are needed —
  this tool only uses normal LinkedIn login.
