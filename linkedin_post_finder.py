#!/usr/bin/env python3
"""
LinkedIn post FINDER (safe — no scraping).

Uses Google's Custom Search API to find PUBLIC LinkedIn posts matching your
keywords, remembers which post URLs it has already surfaced, and outputs only
the NEW ones each run as a candidate list you feed into
linkedin_post_extractor.py.

Why this and not "search LinkedIn directly"?
  There is no sanctioned API to search LinkedIn's live feed, and automating a
  logged-in session is against LinkedIn's terms and risks your account. This
  script never touches LinkedIn — it only asks GOOGLE for posts Google has
  already indexed. Trade-off: Google sees only PUBLIC posts and lags real-time,
  so it won't catch every fresh post, but it automates a real chunk of the
  hunting, hands-off.

Setup (all free, ~5 min):
  1) Create a Programmable Search Engine, set it to search the entire web, and
     copy its "Search engine ID" (cx):
        https://programmablesearchengine.google.com/
  2) In Google Cloud, enable "Custom Search API" and create an API key
     (free tier: 100 queries/day):
        https://developers.google.com/custom-search/v1/overview
  3) export GOOGLE_API_KEY=your_key
     export GOOGLE_CSE_ID=your_cx
  4) python linkedin_post_finder.py

No extra pip installs — uses only the Python standard library.

Output:
  new_candidates.csv  (url, title, snippet, keyword, found_at)  <- open in Excel/Sheets
  seen_posts.txt      (memory of every URL surfaced before, for de-duplication)
"""
from __future__ import annotations
import os, csv, sys, json, time, urllib.parse, urllib.request
from datetime import datetime

# ---- edit your keywords here ----
KEYWORDS = [
    '"IT contract staffing" vendor partner',
    '"IT staffing" "looking for vendor"',
    '"bench sales" C2C requirement',
    '"vendor collaboration" IT staffing',
    '"corp to corp" requirement bench',
]

PAGES_PER_KEYWORD = 1     # 10 results/page. Each page costs 1 of your 100 daily queries.
DATE_RESTRICT     = "d7"  # only posts indexed in the last 7 days. "" = no limit, "d1" = last day.
SEEN_FILE         = "seen_posts.txt"
OUT_FILE          = "new_candidates.csv"
ENDPOINT          = "https://www.googleapis.com/customsearch/v1"


def google_search(query: str, api_key: str, cse_id: str, start: int = 1) -> dict:
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": f"site:linkedin.com/posts/ {query}",
        "num": 10,
        "start": start,
    }
    if DATE_RESTRICT:
        params["dateRestrict"] = DATE_RESTRICT
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def load_seen(path: str) -> set:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip()}


def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        sys.exit("Set GOOGLE_API_KEY and GOOGLE_CSE_ID first (see the header of this file).")

    seen = load_seen(SEEN_FILE)
    new_rows, new_urls = [], []

    for kw in KEYWORDS:
        for page in range(PAGES_PER_KEYWORD):
            try:
                data = google_search(kw, api_key, cse_id, start=1 + page * 10)
            except Exception as e:
                print(f"! query failed for {kw!r}: {e}")
                break
            for item in data.get("items", []):
                link = item.get("link", "").split("?")[0]
                if not link or link in seen:
                    continue
                seen.add(link)
                new_urls.append(link)
                new_rows.append({
                    "url": link,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", "").replace("\n", " "),
                    "keyword": kw,
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
            time.sleep(1)  # be gentle on the API

    write_header = not os.path.exists(OUT_FILE)
    with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "title", "snippet", "keyword", "found_at"])
        if write_header:
            w.writeheader()
        w.writerows(new_rows)

    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        for u in new_urls:
            f.write(u + "\n")

    print(f"Found {len(new_rows)} NEW post(s). Appended to {OUT_FILE}.")
    for row in new_rows[:15]:
        print(f"  - {row['url']}")
    if len(new_rows) > 15:
        print(f"  ... and {len(new_rows) - 15} more in {OUT_FILE}")


if __name__ == "__main__":
    main()
