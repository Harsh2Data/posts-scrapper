#!/usr/bin/env python3
"""
full_pipeline.py — Master orchestrator for the LinkedIn lead bot.

Runs in order:
  1. linkedin_scraper.py  — logs into LinkedIn, searches keywords, saves posts
                             as .txt files to inbox/
  2. run_daily.py         — processes inbox/, deduplicates, validates, exports
                             leads_master.xlsx + daily_leads_YYYY_MM_DD.xlsx, report

Usage (CLI):
    python full_pipeline.py

Usage (programmatic, e.g. from app.py):
    from full_pipeline import run
    result = run(email, password, status_cb=lambda msg: print(msg))

Env vars required for CLI (put in .env file):
    LINKEDIN_EMAIL=your@email.com
    LINKEDIN_PASSWORD=yourpassword
"""
from __future__ import annotations
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run(email: str, password: str, status_cb=None) -> dict:
    """Run the full scrape + extract pipeline. Returns a result dict with
    output file paths and stats. status_cb(msg) is called with progress
    updates throughout (also printed to stdout)."""

    def emit(msg: str):
        print(msg)
        if status_cb:
            try:
                status_cb(msg)
            except Exception:
                pass

    emit(f"=== LinkedIn Lead Bot — {datetime.now():%Y-%m-%d %H:%M} ===")

    emit("[1/2] Logging in and searching LinkedIn for new posts...")
    scraped = 0
    if not email or not password:
        emit("  LinkedIn email/password not provided — skipping scrape.")
        emit("  Processing any posts already in inbox/ instead.")
    else:
        try:
            from linkedin_scraper import scrape
            scraped = scrape(email, password, status_cb=emit)
        except Exception as exc:
            emit(f"  Scrape failed: {exc}")
            emit("  Continuing with whatever is already in inbox/...")

    emit("[2/2] Extracting leads, deduplicating, generating Excel...")
    import run_daily
    result = run_daily.main(status_cb=emit)

    emit("Pipeline complete.")
    result["scraped"] = scraped
    return result


def main():
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent / ".env")  # .env loading is optional; env vars may already be set

    email    = os.environ.get("LINKEDIN_EMAIL", "")
    password = os.environ.get("LINKEDIN_PASSWORD", "")
    run(email, password)


if __name__ == "__main__":
    main()
