# Project Status

**Last updated:** 2026-04-20
**Paused at:** Task 5 — blocked on a product decision (see below).

## Progress vs plan

| # | Task | Status | Commit |
|---|---|---|---|
| 1 | Initialize repository | ✅ Done | `b19ece1 chore: initialize repo with deps and readme` |
| 2 | diff.py with TDD | ✅ Done | `d28c174 feat: add pure diff and trim logic with tests` |
| 3 | state.py with TDD | ✅ Done | `484dcfe feat: add state load/save with trim and graceful error handling` |
| 4 | whatsapp.py CallMeBot client | ✅ Done | `af4b531 feat: add CallMeBot WhatsApp client` |
| 5 | Playwright scraper | 🟡 Partial | `e5d2180` scaffold + `f17ae59` selector fix |
| 6 | Main orchestrator | ⏳ Pending | |
| 7 | GitHub Actions workflow | ⏳ Pending | |
| 8 | Deploy (user action) | ⏳ Pending | |

All tests pass: `pytest -v` → 14 passed.

## What works

- `diff.py` — pure new-posts / trim-to-200 logic, 7 passing tests
- `state.py` — JSON load/save with graceful handling of missing/malformed files, 7 passing tests
- `whatsapp.py` — thin CallMeBot HTTP client
- `etoro_scraper.py` — real-world smoke test returns **3 posts** from the tracked profile:
  ```
  42a3c620-f073-11f0-8080-800007975dfe
  97bc8100-7c1b-11f0-8080-800009e4a64f
  57798700-ad82-11ee-8080-800016a5337a
  ```

## The blocker

**eToro's public profile page shows only pinned posts to non-logged-in viewers.** The general feed requires authentication.

Evidence:
- `/people/harryh1993` renders only the "Pinned posts" section (3 posts, all with `automation-id="pinned-posts-post"`).
- `/people/harryh1993/feed` redirects back to the overview (pinned-only).
- `/people/harryh1993/posts`, `/activity`, `/news` all redirect to `/login`.

So the current scraper sees **pinned posts only**.

## Decision pending from user

Three options presented:

- **A) Ship with "pinned posts only"** — quickest; user would need to pin posts to trigger notifications. Unusual UX.
- **B) Add eToro login** — credentials as GitHub secrets, scraper logs in first. More powerful, but CAPTCHA / 2FA / ToS / lockout risks.
- **C) Track a different signal (e.g. trades)** — changes scope from the original "text posts" requirement.

Recommendation given: **A now, B later if needed**.

## What's needed to finish

Whichever option is chosen, the remaining work is:
- **Task 5 finish:** (possibly) update selectors / add login step to `etoro_scraper.py`.
- **Task 6:** `check_etoro.py` (wiring — already fully spec'd in the plan).
- **Task 7:** `.github/workflows/check.yml` (already fully spec'd in the plan).
- **Task 8:** User deployment (public repo, add secrets, push, trigger first run, verify WhatsApp delivery E2E).

## Selector notes (future drift reference)

- eToro uses Angular with `automation-id="..."` attrs — NOT the `data-etoro-automation-id` pattern the plan assumed.
- Post permalinks are UUID v1: `/posts/<8-4-4-4-12 hex>`.
- `scripts/dump_page.py` is a diagnostic helper — dumps rendered HTML to inspect when selectors break.
- `scripts/explore_selectors.py` launches a headed browser for interactive inspection.

## Files on disk

```
etoro-notifcations/
├── .github/                        (empty — Task 7 creates workflow here)
├── .gitignore
├── README.md
├── check_etoro.py                  (missing — Task 6)
├── diff.py                         ✓
├── docs/
│   └── superpowers/
│       ├── STATUS.md               ← this file
│       ├── plans/
│       │   └── 2026-04-20-etoro-whatsapp-notifier.md
│       └── specs/
│           └── 2026-04-20-etoro-whatsapp-notifier-design.md
├── etoro_scraper.py                ✓ (pinned-posts only)
├── requirements.txt
├── scripts/
│   ├── dump_page.py                (diagnostic)
│   └── explore_selectors.py        (diagnostic)
├── state.py                        ✓
├── tests/
│   ├── __init__.py
│   ├── test_diff.py                ✓
│   └── test_state.py               ✓
└── whatsapp.py                     ✓
```

## How to resume

1. Read this file + the plan at `docs/superpowers/plans/2026-04-20-etoro-whatsapp-notifier.md`.
2. Ask the user which option (A/B/C) to proceed with.
3. If A: proceed directly to Task 6.
4. If B: design the login step, update Task 5 spec, then Task 6.
5. If C: brainstorm the new signal first.
