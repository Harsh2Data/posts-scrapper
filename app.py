#!/usr/bin/env python3
"""
app.py — Local web UI for the LinkedIn Lead Bot.

Lets a user enter their LinkedIn email/password in a browser, click Start,
watch live progress, and download the resulting Excel files.

Run:
    pip install flask
    python app.py

Then open http://127.0.0.1:5000 in your browser.

Credentials are kept in memory only for the duration of the run and are
never written to disk.
"""
from __future__ import annotations
import os, sys, threading, uuid
from datetime import datetime
from pathlib import Path


from flask import Flask, render_template, request, jsonify, send_file, abort

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))

app = Flask(__name__)

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _worker(job_id: str, email: str, password: str):
    job = jobs[job_id]

    def emit(msg: str):
        with jobs_lock:
            job["logs"].append(msg)

    try:
        import full_pipeline
        result = full_pipeline.run(email, password, status_cb=emit)
        with jobs_lock:
            job["status"] = "done"
            job["result"] = result
    except Exception as exc:
        emit(f"ERROR: {exc}")
        with jobs_lock:
            job["status"] = "error"
            job["error"] = str(exc)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    with jobs_lock:
        if any(j["status"] == "running" for j in jobs.values()):
            return jsonify({"error": "A run is already in progress. Please wait for it to finish."}), 409

        job_id = uuid.uuid4().hex
        jobs[job_id] = {"status": "running", "logs": [], "result": None, "error": None}

    t = threading.Thread(target=_worker, args=(job_id, email, password), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            abort(404)
        return jsonify({
            "status": job["status"],
            "logs": job["logs"],
            "error": job["error"],
            "has_master": (BASE_DIR / "leads_master.xlsx").exists(),
            "has_daily": (BASE_DIR / f"daily_leads_{datetime.now():%Y_%m_%d}.xlsx").exists(),
        })


@app.route("/api/download/master")
def download_master():
    path = BASE_DIR / "leads_master.xlsx"
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name="leads_master.xlsx")


@app.route("/api/download/daily")
def download_daily():
    fname = f"daily_leads_{datetime.now():%Y_%m_%d}.xlsx"
    path = BASE_DIR / fname
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=fname)


if __name__ == "__main__":
    print("\n  LinkedIn Lead Bot is running.")
    print("  Open http://127.0.0.1:5000 in your browser.\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
