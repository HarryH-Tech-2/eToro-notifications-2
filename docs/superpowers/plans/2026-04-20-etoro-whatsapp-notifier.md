# eToro → WhatsApp Notifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled GitHub Actions workflow that scrapes a public eToro profile via Playwright every 15 minutes and sends a WhatsApp notification (via CallMeBot) for each new text post.

**Architecture:** Single Python script runs on a `*/15` cron in GitHub Actions. Uses Playwright + headless Chromium to render the JS-heavy profile page. Diffs current post IDs against `state/seen.json` committed in the repo. For each new post, HTTP-GETs CallMeBot's WhatsApp endpoint. Commits state changes back with `[skip ci]`.

**Tech Stack:** Python 3.11, Playwright (Chromium), `requests`, pytest, GitHub Actions.

---

## File Structure

- `check_etoro.py` — main script (entry point, orchestration)
- `etoro_scraper.py` — Playwright-based post extraction
- `state.py` — load/save `seen.json` with trim-to-200 logic
- `whatsapp.py` — CallMeBot HTTP client
- `diff.py` — pure diff logic (new_posts = current - seen, flood cap)
- `state/seen.json` — persisted state (not created until first run)
- `tests/test_diff.py` — unit tests for diff + trim logic
- `tests/test_state.py` — unit tests for state load/save (handles missing/malformed)
- `.github/workflows/check.yml` — cron workflow
- `requirements.txt` — Python dependencies
- `.gitignore` — standard Python ignores
- `README.md` — setup instructions (CallMeBot onboarding, secrets, first run)

---

## Task 1: Initialize Repository

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `README.md`

- [ ] **Step 1: Initialize git repo**

Run:
```bash
cd "C:/Users/harry/OneDrive/Documentos/code/etoro-notifcations"
git init -b main
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.env
.playwright/
```

- [ ] **Step 3: Create `requirements.txt`**

```
playwright==1.47.0
requests==2.32.3
pytest==8.3.3
```

- [ ] **Step 4: Install dev dependencies locally**

So later tasks can run `pytest`. No venv — install into the user's Python so subsequent subagent-run tests work without activation ceremony.

Run:
```bash
python -m pip install -r requirements.txt
```
Expected: pytest, playwright, requests installed (no errors). Playwright browser not needed yet (Task 5 installs that).

- [ ] **Step 5: Create `README.md`**

````markdown
# eToro → WhatsApp Notifier

Sends a WhatsApp notification whenever a tracked eToro user publishes a new text post on their public profile.

## Setup

### 1. CallMeBot (one-time)
1. Add the phone number **+34 644 63 38 90** to your WhatsApp contacts (name it e.g. "CallMeBot").
2. Send it this exact message: `I allow callmebot to send me messages`
3. Wait for a reply containing your API key. Save it.

### 2. Configure GitHub secrets
In this repo's **Settings → Secrets and variables → Actions**, add:
- `CALLMEBOT_PHONE` — your phone in international format, e.g. `+447700900000`
- `CALLMEBOT_APIKEY` — the key you received

### 3. Configure the profile (if different from default)
Edit `PROFILE_URL` at the top of `check_etoro.py`.

### 4. First run
Go to **Actions → Check eToro → Run workflow** and trigger it manually. This seeds `state/seen.json` with currently-visible posts and sends no notifications. After that, the cron takes over every 15 min.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
playwright install chromium
pytest
```
````

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt README.md
git commit -m "chore: initialize repo with deps and readme"
```

---

## Task 2: Post dataclass and diff logic (TDD)

**Files:**
- Create: `diff.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_diff.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_diff.py`:

```python
from diff import Post, new_posts, trim_seen, FLOOD_CAP


def test_new_posts_returns_unseen_only():
    current = [Post("a", "url_a", None), Post("b", "url_b", None)]
    seen = {"a"}
    assert new_posts(current, seen) == [Post("b", "url_b", None)]


def test_new_posts_returns_empty_when_all_seen():
    current = [Post("a", "url_a", None)]
    seen = {"a"}
    assert new_posts(current, seen) == []


def test_new_posts_returns_all_when_seen_empty():
    current = [Post("a", "url_a", None), Post("b", "url_b", None)]
    assert new_posts(current, set()) == current


def test_new_posts_preserves_current_order():
    current = [Post("c", "url_c", None), Post("a", "url_a", None), Post("b", "url_b", None)]
    seen = {"a"}
    assert new_posts(current, seen) == [Post("c", "url_c", None), Post("b", "url_b", None)]


def test_new_posts_flood_caps_to_five():
    current = [Post(str(i), f"url_{i}", None) for i in range(10)]
    result = new_posts(current, set())
    assert len(result) == FLOOD_CAP == 5
    # Should keep the NEWEST 5 (first 5 in fetch order, since fetch returns newest-first)
    assert [p.id for p in result] == ["0", "1", "2", "3", "4"]


def test_trim_seen_keeps_last_200():
    ids = [str(i) for i in range(300)]
    trimmed = trim_seen(ids)
    assert len(trimmed) == 200
    assert trimmed == ids[-200:]


def test_trim_seen_no_op_when_under_cap():
    ids = ["a", "b", "c"]
    assert trim_seen(ids) == ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_diff.py -v`
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'diff'`.

- [ ] **Step 3: Implement `diff.py`**

Create `diff.py`:

```python
"""Pure diff and trim logic - no I/O."""
from dataclasses import dataclass


FLOOD_CAP = 5
SEEN_CAP = 200


@dataclass(frozen=True)
class Post:
    id: str
    url: str
    timestamp: str | None


def new_posts(current: list[Post], seen: set[str]) -> list[Post]:
    """Return posts in `current` whose IDs are not in `seen`, capped at FLOOD_CAP.

    `current` is expected to be newest-first; the flood cap keeps the newest.
    Order of the returned list matches the order of `current`.
    """
    unseen = [p for p in current if p.id not in seen]
    return unseen[:FLOOD_CAP]


def trim_seen(ids: list[str]) -> list[str]:
    """Keep only the most recent SEEN_CAP ids. Assumes ids are append-ordered."""
    if len(ids) <= SEEN_CAP:
        return ids
    return ids[-SEEN_CAP:]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_diff.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add diff.py tests/__init__.py tests/test_diff.py
git commit -m "feat: add pure diff and trim logic with tests"
```

---

## Task 3: State persistence (TDD)

**Files:**
- Create: `state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_state.py`:

```python
import json
from pathlib import Path
from state import load_seen, save_seen


def test_load_seen_missing_file_returns_empty_set(tmp_path):
    missing = tmp_path / "seen.json"
    assert load_seen(missing) == set()


def test_load_seen_malformed_json_returns_empty_set(tmp_path):
    bad = tmp_path / "seen.json"
    bad.write_text("not json{")
    assert load_seen(bad) == set()


def test_load_seen_missing_key_returns_empty_set(tmp_path):
    bad = tmp_path / "seen.json"
    bad.write_text('{"other": []}')
    assert load_seen(bad) == set()


def test_load_seen_reads_ids(tmp_path):
    f = tmp_path / "seen.json"
    f.write_text('{"seen_ids": ["a", "b", "c"]}')
    assert load_seen(f) == {"a", "b", "c"}


def test_save_seen_writes_ids(tmp_path):
    f = tmp_path / "seen.json"
    save_seen(f, ["x", "y", "z"])
    data = json.loads(f.read_text())
    assert data == {"seen_ids": ["x", "y", "z"]}


def test_save_seen_creates_parent_directory(tmp_path):
    f = tmp_path / "nested" / "dir" / "seen.json"
    save_seen(f, ["a"])
    assert f.exists()


def test_save_seen_trims_to_cap(tmp_path):
    f = tmp_path / "seen.json"
    many = [str(i) for i in range(250)]
    save_seen(f, many)
    data = json.loads(f.read_text())
    assert len(data["seen_ids"]) == 200
    assert data["seen_ids"] == many[-200:]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'state'`.

- [ ] **Step 3: Implement `state.py`**

Create `state.py`:

```python
"""State persistence for seen post IDs."""
import json
from pathlib import Path
from diff import trim_seen


def load_seen(path: Path) -> set[str]:
    """Read seen ids from `path`. Returns empty set if missing or malformed."""
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    ids = data.get("seen_ids")
    if not isinstance(ids, list):
        return set()
    return set(ids)


def save_seen(path: Path, ids: list[str]) -> None:
    """Write seen ids to `path`, trimmed to cap. Creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = trim_seen(ids)
    path.write_text(
        json.dumps({"seen_ids": trimmed}, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_state.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: add state load/save with trim and graceful error handling"
```

---

## Task 4: CallMeBot client

**Files:**
- Create: `whatsapp.py`

- [ ] **Step 1: Implement `whatsapp.py`**

No unit test — this is a thin HTTP wrapper; the value is in integration. End-to-end verified manually at deploy.

Create `whatsapp.py`:

```python
"""CallMeBot WhatsApp sender.

API docs: https://www.callmebot.com/blog/free-api-whatsapp-messages/
Endpoint: GET https://api.callmebot.com/whatsapp.php?phone=...&text=...&apikey=...
"""
import logging
import requests

logger = logging.getLogger(__name__)

ENDPOINT = "https://api.callmebot.com/whatsapp.php"
TIMEOUT_SECONDS = 30


class CallMeBotError(Exception):
    pass


def send_whatsapp(phone: str, apikey: str, message: str) -> None:
    """Send `message` to `phone` via CallMeBot. Raises CallMeBotError on failure."""
    params = {"phone": phone, "text": message, "apikey": apikey}
    try:
        resp = requests.get(ENDPOINT, params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise CallMeBotError(f"HTTP error: {e}") from e
    if resp.status_code != 200:
        raise CallMeBotError(
            f"CallMeBot returned {resp.status_code}: {resp.text[:200]}"
        )
    logger.info("WhatsApp sent: %s", message)
```

- [ ] **Step 2: Sanity-import the module**

Run:
```bash
python -c "from whatsapp import send_whatsapp, CallMeBotError; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add whatsapp.py
git commit -m "feat: add CallMeBot WhatsApp client"
```

---

## Task 5: Playwright scraper (exploratory + integrated)

This task has an exploratory step — the correct selector for posts on the eToro profile page is not knowable from static inspection. We discover it locally first, then hard-code it.

**Files:**
- Create: `etoro_scraper.py`
- Create: `scripts/explore_selectors.py` (one-off helper, kept for future debugging)

- [ ] **Step 1: Install Playwright locally**

Run:
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 2: Write the exploration helper**

Create `scripts/explore_selectors.py`:

```python
"""One-off helper to discover post selectors on an eToro profile.

Usage: python scripts/explore_selectors.py https://www.etoro.com/people/harryh1993
"""
import sys
from playwright.sync_api import sync_playwright


def main(url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headed so you can see
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        print("Page loaded. Inspect the feed in the browser devtools.")
        print("Look for: stable [data-etoro-automation-id=...] on post containers,")
        print("and stable permalink href patterns (e.g. /posts/<id>).")
        print("When done, press Enter to exit.")
        input()
        browser.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.etoro.com/people/harryh1993"
    main(url)
```

- [ ] **Step 3: Run the explorer and record findings**

Run:
```bash
python scripts/explore_selectors.py
```

In the browser that opens:
1. Scroll to the "Feed" / "Posts" tab if not already there.
2. Open DevTools (F12). Find a post element.
3. Record a stable selector (prefer `data-etoro-automation-id` attrs — eToro's convention). Examples to look for: `[data-etoro-automation-id="feed-item-container"]`, `[data-etoro-automation-id="feed-post-text"]`.
4. Find the post's permalink anchor and its `href` pattern. Ideally `/posts/<numeric-id>` or similar.
5. Note these in a comment block in `etoro_scraper.py` for future maintenance.

**If posts are not visible without login:** STOP and escalate. The design assumed public visibility. The workaround is either (a) require login via eToro credentials as additional secrets, or (b) switch tracked profiles to one whose posts are public. Neither is in scope for this task — escalate and pause.

- [ ] **Step 4: Implement `etoro_scraper.py`**

Replace the placeholder selectors below with the actual ones found in Step 3. Everything else is fixed.

Create `etoro_scraper.py`:

```python
"""Scrape post IDs and URLs from an eToro public profile page."""
import logging
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from diff import Post

logger = logging.getLogger(__name__)

# Selectors discovered via scripts/explore_selectors.py on 2026-04-20.
# If eToro changes their DOM these WILL need updating.
FEED_CONTAINER_SELECTOR = '[data-etoro-automation-id="feed-item-container"]'
POST_LINK_SELECTOR = 'a[href*="/posts/"]'

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT_MS = 45_000
SELECTOR_TIMEOUT_MS = 30_000

POST_ID_RE = re.compile(r"/posts/([^/?#]+)")


def _extract_post_id(href: str) -> str | None:
    m = POST_ID_RE.search(href)
    return m.group(1) if m else None


def fetch_posts(profile_url: str) -> list[Post]:
    """Fetch visible posts from a public eToro profile.

    Returns newest-first. Raises on unrecoverable browser errors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=USER_AGENT)
        page = ctx.new_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            try:
                page.wait_for_selector(FEED_CONTAINER_SELECTOR, timeout=SELECTOR_TIMEOUT_MS)
            except PWTimeout:
                logger.warning("Feed selector not found within timeout - profile may have no posts or DOM changed")
                return []

            # Give the feed a moment to settle after first items render.
            page.wait_for_timeout(1500)

            anchors = page.query_selector_all(POST_LINK_SELECTOR)
            posts: list[Post] = []
            seen_ids: set[str] = set()
            for a in anchors:
                href = a.get_attribute("href") or ""
                post_id = _extract_post_id(href)
                if not post_id or post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                url = urljoin(profile_url, href)
                posts.append(Post(id=post_id, url=url, timestamp=None))
            logger.info("Scraped %d unique posts", len(posts))
            return posts
        finally:
            browser.close()
```

- [ ] **Step 5: Smoke-test the scraper against the live profile**

Run:
```bash
python -c "from etoro_scraper import fetch_posts; posts = fetch_posts('https://www.etoro.com/people/harryh1993'); print(f'Found {len(posts)} posts'); [print(p.id, p.url) for p in posts[:5]]"
```
Expected: prints a non-zero post count, and post IDs/URLs look plausible (e.g. numeric IDs, URLs starting with `https://www.etoro.com/posts/`). If 0 posts and the profile has visible posts in a normal browser, return to Step 3 and re-check selectors.

- [ ] **Step 6: Commit**

```bash
git add etoro_scraper.py scripts/explore_selectors.py
git commit -m "feat: add Playwright scraper for eToro profile posts"
```

---

## Task 6: Main orchestrator

**Files:**
- Create: `check_etoro.py`

- [ ] **Step 1: Implement `check_etoro.py`**

Create `check_etoro.py`:

```python
"""Entry point: fetch posts, diff against state, notify, save state."""
import logging
import os
import sys
from pathlib import Path

from diff import new_posts
from etoro_scraper import fetch_posts
from state import load_seen, save_seen
from whatsapp import CallMeBotError, send_whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("check_etoro")

PROFILE_URL = "https://www.etoro.com/people/harryh1993"
STATE_PATH = Path("state/seen.json")


def main() -> int:
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not apikey:
        logger.error("CALLMEBOT_PHONE and CALLMEBOT_APIKEY must be set")
        return 2

    try:
        current = fetch_posts(PROFILE_URL)
    except Exception as e:
        logger.exception("Scrape failed: %s", e)
        return 1

    if not current:
        logger.warning("0 posts scraped - not modifying state")
        return 0

    seen = load_seen(STATE_PATH)

    # First-run seed: no prior state means we treat everything as already seen.
    # This prevents spamming historical posts on first deploy.
    if not seen:
        logger.info("First run - seeding %d current posts as seen, no notifications", len(current))
        save_seen(STATE_PATH, [p.id for p in current])
        return 0

    to_notify = new_posts(current, seen)
    if not to_notify:
        logger.info("No new posts (%d current, %d seen)", len(current), len(seen))
        return 0

    logger.info("Notifying %d new post(s)", len(to_notify))

    # Notify oldest-first so WhatsApp order matches chronological order.
    # `current` is newest-first, so reverse to_notify.
    updated_seen = list(seen)
    for post in reversed(to_notify):
        try:
            send_whatsapp(phone, apikey, f"New eToro post: {post.url}")
            updated_seen.append(post.id)
        except CallMeBotError as e:
            logger.error("Failed to send for post %s: %s", post.id, e)
            # Do NOT add to seen - will retry next run.

    save_seen(STATE_PATH, updated_seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Dry-run locally**

Set dummy env vars (won't actually send because CallMeBot rejects bad keys):

```bash
# Use real values here to actually test the WhatsApp side
CALLMEBOT_PHONE="+447700900000" CALLMEBOT_APIKEY="xxxx" python check_etoro.py
```

Expected on first run: log line `First run - seeding N current posts as seen, no notifications`, a new `state/seen.json` file appears with that many IDs, exit code 0.

- [ ] **Step 3: Verify subsequent run is a no-op**

Run again immediately:
```bash
CALLMEBOT_PHONE="+447700900000" CALLMEBOT_APIKEY="xxxx" python check_etoro.py
```
Expected: `No new posts (N current, N seen)`, no change to `state/seen.json`, exit 0.

- [ ] **Step 4: Commit (but NOT `state/seen.json` yet — that should be written by the workflow, not by local dev)**

```bash
git add check_etoro.py
git commit -m "feat: add main orchestrator wiring scraper, state, and whatsapp"
```

Remove local `state/seen.json` so the first cloud run does the seed:

```bash
rm -rf state/
```

---

## Task 7: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/check.yml`

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/check.yml`:

```yaml
name: Check eToro

on:
  schedule:
    - cron: "*/15 * * * *"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: check-etoro
  cancel-in-progress: false

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browser
        run: playwright install --with-deps chromium

      - name: Run checker
        env:
          CALLMEBOT_PHONE: ${{ secrets.CALLMEBOT_PHONE }}
          CALLMEBOT_APIKEY: ${{ secrets.CALLMEBOT_APIKEY }}
        run: python check_etoro.py

      - name: Commit state changes
        run: |
          if [[ -n "$(git status --porcelain state/)" ]]; then
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add state/
            git commit -m "chore: update seen state [skip ci]"
            git push
          else
            echo "No state changes to commit"
          fi
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/check.yml
git commit -m "ci: add 15-min cron workflow with state commit"
```

---

## Task 8: Publish and deploy

- [ ] **Step 1: Create public GitHub repo**

Manual action by the user:
1. Create a new **public** repo on github.com named `etoro-notifcations` (or any name). Public = unlimited free Actions minutes.
2. Do NOT initialize it with any files (no README/gitignore/license from GitHub).

- [ ] **Step 2: Add secrets**

In the new repo: **Settings → Secrets and variables → Actions → New repository secret**:
- `CALLMEBOT_PHONE` — international format, e.g. `+447700900000`
- `CALLMEBOT_APIKEY` — from CallMeBot

- [ ] **Step 3: Push local repo**

```bash
git remote add origin https://github.com/<your-user>/etoro-notifcations.git
git push -u origin main
```

- [ ] **Step 4: Manually trigger first run**

1. Go to **Actions → Check eToro → Run workflow → Run**.
2. Wait for it to finish. Inspect the logs.
3. Expected: log line `First run - seeding N current posts as seen, no notifications`. A follow-up commit `chore: update seen state [skip ci]` should appear on `main` containing the new `state/seen.json`.
4. **No WhatsApp message should arrive on the first run.**

- [ ] **Step 5: End-to-end verification with a real new post**

1. Have the eToro user (or yourself on the tracked account) publish a new text post.
2. Within 15 minutes of the next cron tick, a WhatsApp message should arrive on the configured phone, containing the post URL.
3. Inspect the next workflow run's log: should say `Notifying 1 new post(s)`.
4. `state/seen.json` on `main` should now include the new post's ID.

- [ ] **Step 6: Done**

No commit in this task — all artifacts are in the GitHub cloud at this point.
