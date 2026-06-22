#!/usr/bin/env python3
"""
linkedin_scraper.py

Login → search → extract post cards → save to inbox/.

Approach:
  - Profile links (/in/) are ALWAYS in search result cards (confirmed from debug).
  - We use them as anchors: find each /in/ link → walk up to its <li> container
    → grab the full innerText of that container.
  - Expand "See more" buttons first so emails at the bottom are visible.
  - Dedup by MD5 of the post text (not URN, since URN lookup was unreliable).

PREREQUISITES
    pip install selenium webdriver-manager python-dotenv

CREDENTIALS (.env):
    LINKEDIN_EMAIL=your@email.com
    LINKEDIN_PASSWORD=yourpassword
"""
from __future__ import annotations
import hashlib, os, re, sys, time, random, urllib.parse
from datetime import date
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────
INBOX     = Path("inbox")
SEEN_FILE = Path("seen_posts.txt")

KEYWORDS = [
    "vendor empanelment IT staffing",
    "C2C C2H IT vendor collaboration",
    "open to vendor IT staffing India",
    "bench consultants vendor partner India",
    "staff augmentation vendor collaboration",
    "contract staffing vendor partner India",
    "IT staffing company collaboration",
    "recruitment vendor partner",
    "vendor collaboration IT resource India",
    "subcon IT staffing requirement",
    "bench sales hotlist India",
    "looking for implementation partner IT staffing",
    "corp to corp vendor India IT",
    "talent acquisition vendor empanelment",
    "IT bench resources available C2C",
    "hiring partner IT staffing India",
    "IT recruitment vendor tie up",
    "preferred vendor IT staffing requirement",
    "consultant bench available C2C C2H",
    "IT staffing partnership India recruiter",
]

MAX_PER_KEYWORD = 12
DATE_FILTER     = "past-week"
SCROLL_ROUNDS   = 9

RELEVANCE_RE = re.compile(
    r"staffing|recruit|vendor|bench\b|c2c|c2h|corp.to.corp|"
    r"contract|talent|hiring partner|consultant|empanelment|"
    r"augment|subcon|resource sharing",
    re.I,
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# ── helpers ───────────────────────────────────────────────────────────────────
def _delay(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))

def _key(text: str) -> str:
    return hashlib.md5(text[:300].encode("utf-8", errors="ignore")).hexdigest()[:16]

def load_seen() -> set:
    if not SEEN_FILE.exists():
        return set()
    return {l.strip() for l in SEEN_FILE.read_text("utf-8").splitlines() if l.strip()}

def save_seen(seen: set):
    SEEN_FILE.write_text("\n".join(sorted(seen)), "utf-8")

def _emit(status_cb, msg: str):
    print(msg)
    if status_cb:
        try:
            status_cb(msg)
        except Exception:
            pass


# ── browser ───────────────────────────────────────────────────────────────────
def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except Exception:
        service = Service()
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return driver


# ── login ─────────────────────────────────────────────────────────────────────
def _login(driver, email, password, status_cb=None):
    from selenium.webdriver.common.keys import Keys

    _emit(status_cb, "Opening LinkedIn login page...")
    driver.get("https://www.linkedin.com/login")
    _delay(3, 5)

    if "/login" not in driver.current_url:
        _emit(status_cb, "Already logged in (existing session).")
        return

    def _visible(*sels):
        for sel in sels:
            for el in driver.find_elements("css selector", sel):
                if el.is_displayed() and el.is_enabled():
                    return el
        return None

    def _type(el, text):
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});"
            "arguments[0].click(); arguments[0].focus();", el)
        time.sleep(0.4)
        driver.execute_script("arguments[0].value='';", el)
        for ch in text:
            el.send_keys(ch)
            time.sleep(random.uniform(0.04, 0.11))

    em = _visible("input#username", "input[name='session_key']",
                   "input[autocomplete='username']", "input[type='text']",
                   "input[type='email']")
    if not em:
        _emit(status_cb, "Login form not visible yet — waiting up to 60s "
                         "(complete any prompt in the browser window)...")
        for _ in range(60):
            time.sleep(1)
            em = _visible("input#username", "input[name='session_key']",
                           "input[autocomplete='username']", "input[type='text']",
                           "input[type='email']")
            if em or "/login" not in driver.current_url:
                break
        if "/login" not in driver.current_url:
            _emit(status_cb, "Logged in.")
            return
        if not em:
            raise RuntimeError("Could not find the LinkedIn login form.")

    _emit(status_cb, "Entering credentials...")
    _type(em, email)
    pw = _visible("input#password", "input[name='session_password']",
                   "input[type='password']")
    if not pw:
        raise RuntimeError("Password field not found.")
    _type(pw, password)
    pw.send_keys(Keys.RETURN)
    _emit(status_cb, "Submitting login...")
    _delay(4, 6)

    if "checkpoint" in driver.current_url or "challenge" in driver.current_url:
        _emit(status_cb, "LinkedIn security check — please complete it in the "
                         "browser window (waiting up to 2 minutes)...")
        for _ in range(120):
            time.sleep(1)
            if "checkpoint" not in driver.current_url and "challenge" not in driver.current_url:
                break
    if "/login" in driver.current_url:
        raise RuntimeError(f"Login failed (still on {driver.current_url}). "
                            f"Check your email/password and try again.")
    _emit(status_cb, "Logged in successfully.")


# ── expand all "See more" buttons visible on page ─────────────────────────────
def _expand_posts(driver):
    try:
        btns = driver.find_elements("css selector",
            "button[aria-label*='see more'], "
            "button[aria-label*='See more'], "
            "button.feed-shared-inline-show-more-text__see-more-less-toggle, "
            "button.search-result__supplement-btn, "
            "button.attributed-text-segment-list__show-more-btn, "
            "button[class*='show-more']")
        for btn in btns:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.2)
            except Exception:
                pass
    except Exception:
        pass


# ── extract post cards using /in/ links as anchors ────────────────────────────
_SKIP_LINE = re.compile(
    r"^(feed post|view post|view profile|follow|connect|message|"
    r"like|comment|share|repost|send|more|report|save|embed|"
    r"\d+(?:st|nd|rd|th)\+?|•.*|reactions?|comments?)$",
    re.I,
)

_EXTRACT_JS = """
var results = [];
var seenEls = new WeakSet();
var MAX_TEXT = 6000;

document.querySelectorAll('a[href*="/in/"]').forEach(function(anchor) {
    var href = (anchor.getAttribute('href') || '').split('?')[0];
    if (!href.match(/\\/in\\//)) return;

    // Find the smallest ancestor that represents ONE post / result card.
    var container = anchor.closest(
        'li, [data-urn], [data-chameleon-result-urn], ' +
        '[class*="occludable-update"], [class*="result-container"]'
    );
    if (!container) {
        // Fallback: walk up a few levels only (never reach a page-wide wrapper)
        container = anchor;
        for (var i = 0; i < 8 && container.parentElement; i++) {
            container = container.parentElement;
        }
    }
    if (!container || seenEls.has(container)) return;
    seenEls.add(container);

    var text = (container.innerText || '').trim();
    // Reject empty cards AND page-wide containers (multiple posts glued together)
    if (text.length < 60 || text.length > MAX_TEXT) return;

    // Extract post URN, scoped to this single card only
    var urn = container.getAttribute('data-urn') ||
              container.getAttribute('data-chameleon-result-urn') || '';
    if (!urn) {
        var els = container.querySelectorAll('[data-urn],[data-chameleon-result-urn]');
        for (var j = 0; j < els.length && !urn; j++) {
            var u = els[j].getAttribute('data-urn') ||
                    els[j].getAttribute('data-chameleon-result-urn') || '';
            if (u && u.indexOf('activity') > -1) urn = u;
        }
    }
    if (!urn) {
        var m = container.outerHTML.match(/urn[:%3A]+li[:%3A]+activity[:%3A]+(\d+)/i);
        if (m) urn = 'urn:li:activity:' + m[1];
    }

    results.push({
        text:      text,
        authorUrl: href,
        postUrn:   urn
    });
});

return results;
"""


def _get_cards(driver, seen: set) -> list[dict]:
    raw = driver.execute_script(_EXTRACT_JS) or []
    out = []
    for c in raw:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        k = _key(text)
        if k in seen:
            continue
        if not RELEVANCE_RE.search(text):
            continue
        urn = (c.get("postUrn") or "").strip()
        post_url = (f"https://www.linkedin.com/feed/update/{urn}/"
                    if urn.startswith("urn:li:activity:") else "")
        out.append({
            "key":        k,
            "text":       text,
            "author_url": (c.get("authorUrl") or "").strip(),
            "post_url":   post_url,
        })
    return out


# ── scrape one keyword ────────────────────────────────────────────────────────
def _scrape_keyword(driver, keyword: str, seen: set, status_cb=None) -> list[dict]:
    q   = urllib.parse.quote_plus(keyword)
    url = (f"https://www.linkedin.com/search/results/content/"
           f"?keywords={q}&datePosted={DATE_FILTER}&sortBy=date_posted")
    driver.get(url)
    _delay(3, 5)
    _emit(status_cb, f"  Visiting search results for: {keyword!r}")

    saved      = []
    seen_local = set()

    for rnd in range(SCROLL_ROUNDS):
        _expand_posts(driver)
        _delay(0.6, 1.2)

        cards = _get_cards(driver, seen | seen_local)
        new_in_round = 0
        for card in cards:
            k = card["key"]
            if k in seen_local:
                continue
            seen_local.add(k)
            new_in_round += 1

            author_url = card["author_url"]
            text       = card["text"]
            post_url   = card.get("post_url", "")

            # Extract author name: first non-trivial line of the card text
            author = ""
            for ln in text.splitlines():
                ln = ln.strip()
                if ln and not _SKIP_LINE.match(ln) and len(ln) < 80:
                    author = ln
                    break

            parts = []
            if author:
                parts.append(author)
            if author_url:
                parts.append(f"[{author}]({author_url})")
            parts.append("")
            parts.append(text)
            parts.append("")
            if post_url:
                parts.append(post_url)
            parts.append(f"Keyword: {keyword}")

            saved.append({
                "key":       k,
                "text":      "\n".join(parts),
                "has_email": bool(EMAIL_RE.search(text)),
            })

            if len(saved) >= MAX_PER_KEYWORD:
                return saved

        _emit(status_cb, f"    scanning... ({rnd+1}/{SCROLL_ROUNDS}) "
                         f"+{new_in_round} new relevant post(s), {len(saved)} total")
        driver.execute_script("window.scrollBy(0, 900);")
        _delay(2.0, 3.5)

    return saved


# ── save to inbox ─────────────────────────────────────────────────────────────
def _save(post: dict, idx: int) -> Path:
    INBOX.mkdir(exist_ok=True)
    path = INBOX / f"post_{date.today():%Y%m%d}_{idx:04d}.txt"
    path.write_text(post["text"], "utf-8")
    return path


# ── public entry point ────────────────────────────────────────────────────────
def scrape(email: str, password: str, status_cb=None) -> int:
    driver = _make_driver()
    seen   = load_seen()
    total  = 0

    try:
        _login(driver, email, password, status_cb)

        for i, kw in enumerate(KEYWORDS, 1):
            _emit(status_cb, f"[{i}/{len(KEYWORDS)}] Searching: {kw!r}")
            try:
                posts = _scrape_keyword(driver, kw, seen, status_cb)
                for post in posts:
                    path = _save(post, total)
                    seen.add(post["key"])
                    total += 1
                    flag = " [has email]" if post["has_email"] else ""
                    _emit(status_cb, f"    saved {path.name}{flag}")
                if not posts:
                    _emit(status_cb, "    no new relevant posts found")
            except Exception as exc:
                _emit(status_cb, f"    error on '{kw}': {exc}")
            _delay(4, 8)

    finally:
        save_seen(seen)
        driver.quit()

    _emit(status_cb, f"Scrape done — {total} new post(s) saved.")
    return total


# ── standalone ────────────────────────────────────────────────────────────────
def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    email    = os.environ.get("LINKEDIN_EMAIL", "")
    password = os.environ.get("LINKEDIN_PASSWORD", "")
    if not email or not password:
        sys.exit("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
    scrape(email, password)

if __name__ == "__main__":
    main()
