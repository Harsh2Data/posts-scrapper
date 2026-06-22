#!/usr/bin/env python3
"""
scheduler.py — Keep-running daily scheduler for the LinkedIn lead bot.

Runs full_pipeline.py once every day at the configured time.
Leave this script running in the background (or use setup_windows_task.py
to register it as a proper Windows Scheduled Task instead).

Usage:
    pip install schedule
    python scheduler.py

    # Override the run time:
    RUN_TIME=08:30 python scheduler.py
"""
from __future__ import annotations
import os, subprocess, sys, time
from datetime import datetime

try:
    import schedule
except ImportError:
    sys.exit("Install schedule first:  pip install schedule")

RUN_TIME = os.environ.get("RUN_TIME", "09:00")   # 24-hour HH:MM
SCRIPT   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "full_pipeline.py")


def _run():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n[{ts}]  Starting daily lead-bot pipeline …")
    result = subprocess.run([sys.executable, SCRIPT])
    if result.returncode != 0:
        print(f"[{ts}]  Pipeline exited with code {result.returncode}")
    else:
        print(f"[{ts}]  Pipeline finished successfully.")


def main():
    print(f"Scheduler running.  Pipeline fires daily at {RUN_TIME}.")
    print("Press Ctrl+C to stop.\n")

    schedule.every().day.at(RUN_TIME).do(_run)

    # Also allow an immediate test run
    if "--now" in sys.argv:
        print("--now flag detected: running pipeline immediately …")
        _run()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
