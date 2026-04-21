# Project Status

**Last updated:** 2026-04-21
**State:** Tasks 1–7 complete. Task 8 (user deployment) is the only thing left.

## Progress vs plan

| # | Task | Status | Commit |
|---|---|---|---|
| 1 | Initialize repository | ✅ Done | `b19ece1 chore: initialize repo with deps and readme` |
| 2 | diff.py with TDD | ✅ Done | `d28c174 feat: add pure diff and trim logic with tests` |
| 3 | state.py with TDD | ✅ Done | `484dcfe feat: add state load/save with trim and graceful error handling` |
| 4 | whatsapp.py CallMeBot client | ✅ Done | `af4b531 feat: add CallMeBot WhatsApp client` |
| 5 | Playwright scraper | ✅ Done | `e5d2180` scaffold + `f17ae59` selector fix + (this session) virtual-scroll + feed selector |
| 6 | Main orchestrator | ✅ Done | this session |
| 7 | GitHub Actions workflow | ✅ Done | this session |
| 8 | Deploy (user action) | ⏳ Pending — see below |

Tests: `pytest -v` → 14 passed.
Local E2E dry-run verified across all 5 profiles: first run seeds `state/seen-<username>.json` for each (13 + 10 + 13 + 3 + 10 posts), no WhatsApp calls, exit 0.

## What works

- `diff.py` — pure new-posts / trim-to-200 logic, 7 tests.
- `state.py` — JSON load/save with graceful handling of missing/malformed files, 7 tests.
- `whatsapp.py` — thin CallMeBot HTTP client.
- `etoro_scraper.py` — returns **13 posts** from the tracked profile (3 pinned + 10 from the virtualised Discussions feed), newest first, with absolute timestamps on feed posts.
- `check_etoro.py` — iterates over `PROFILE_URLS` (5 profiles: `harryh1993`, `jaynemesis`, `michalhla`, `JeppeKirkBonde`, `CPHequities`). Per-profile state file `state/seen-<username>.json`. Per-profile first-run seed, diff-and-notify, flood cap. Notification format: `@<username> posted: <url>`. Failure on one profile is logged and skipped; exit 1 only if every profile fails.
- `.github/workflows/check.yml` — `*/15 * * * *` cron, installs Playwright+Chromium, runs the checker, commits `state/` back with `[skip ci]`.

## Scraper selectors (future drift reference)

- eToro uses Angular with `automation-id="..."` (NOT `data-etoro-automation-id`).
- Pinned: `a[automation-id="pinned-posts-post"]` (rendered immediately).
- Feed:   `a[automation-id="feed-timestamp-link"]` (virtualised, needs scroll).
- Absolute timestamp: enclosing `[automation-id="feed-timestamp-label"]` element's `title` attr, format `DD/MM/YYYY HH:MM:SS`.
- Post permalinks: `/posts/<UUID v1>`.
- `scripts/dump_page.py` / `scripts/dump_after_scroll.py` / `scripts/explore_selectors.py` — diagnostics.

## Task 8 — user deployment

Remaining actions are all on the user:

1. Create a **public** GitHub repo (public = unlimited free Actions minutes).
2. Add repo secrets:
   - `CALLMEBOT_PHONE` (e.g. `+447700900000`)
   - `CALLMEBOT_APIKEY` (from CallMeBot onboarding)
3. Add remote and push: `git remote add origin …` → `git push -u origin main`.
4. Trigger the first run: **Actions → Check eToro → Run workflow**. Expect the seed path and a follow-up `chore: update seen state [skip ci]` commit on `main`. **No WhatsApp message** on first run.
5. E2E verify: publish a new post on the tracked profile, wait ≤15 min for the next cron tick, expect WhatsApp delivery and the new ID appearing in `state/seen.json`.

## Files on disk

```
etoro-notifcations/
├── .github/workflows/check.yml     ✓
├── .gitignore
├── README.md
├── check_etoro.py                  ✓
├── diff.py                         ✓
├── docs/superpowers/
│   ├── STATUS.md                   ← this file
│   ├── plans/2026-04-20-etoro-whatsapp-notifier.md
│   └── specs/2026-04-20-etoro-whatsapp-notifier-design.md
├── etoro_scraper.py                ✓ (pinned + feed, virtual-scroll aware)
├── requirements.txt
├── scripts/
│   ├── dump_page.py                (diagnostic)
│   ├── dump_after_scroll.py        (diagnostic — scrolls before dumping)
│   └── explore_selectors.py        (diagnostic)
├── state.py                        ✓
├── tests/
│   ├── __init__.py
│   ├── test_diff.py                ✓
│   └── test_state.py               ✓
└── whatsapp.py                     ✓
```
