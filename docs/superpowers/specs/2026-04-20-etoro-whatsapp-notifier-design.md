# eToro → WhatsApp Post Notifier

**Date:** 2026-04-20
**Status:** Design approved, pending implementation plan

## Goal

Send a WhatsApp notification to the user whenever the eToro user [harryh1993](https://www.etoro.com/people/harryh1993) publishes a new text post on their public profile feed.

## Non-Goals

- Notifying on trades (opening/closing positions)
- Notifying on replies, likes, or other engagement
- Supporting multiple watched users (single profile only)
- Sending to anyone other than the repo owner (CallMeBot is self-send only)
- Realtime (<5 min) delivery

## Architecture

A Python script runs on a GitHub Actions cron every 15 minutes. It launches a headless Chromium via Playwright, loads the eToro profile page, extracts post IDs from the rendered feed, diffs against a state file committed in the repo, and sends one WhatsApp message per new post via the CallMeBot HTTP API.

```
GitHub Actions (cron: */15 * * * *)
  └─ check_etoro.py
       ├─ Playwright: render profile page, extract posts
       ├─ Diff against state/seen.json
       ├─ For each new post → CallMeBot HTTP GET
       └─ Update state/seen.json (committed back to repo)
```

### Why these choices

- **GitHub Actions** — free, zero-maintenance 24/7 scheduler. No server to babysit.
- **Playwright** — eToro's feed is JS-rendered; a plain HTTP fetch returns no post content. Playwright is more resilient to HTML changes than reverse-engineering their internal XHR API.
- **CallMeBot** — free, one-time setup (send "I allow callmebot to send me messages" to their WhatsApp number, receive API key). Only sends to the owner's own number, which is exactly what's wanted.
- **State in the repo** — no external DB needed. `seen.json` is small and low-churn. The workflow commits updates back with `[skip ci]` to avoid re-triggering itself.

## Components

### `check_etoro.py`

Main script. Public functions:

- `fetch_posts(profile_url: str) -> list[Post]`
  Launches headless Chromium, navigates to `profile_url`, waits for the feed container selector, scrolls if needed to force-render, extracts each visible post's ID, URL, and timestamp. Returns a list of `Post` records ordered newest-first.
- `load_seen(path: Path) -> set[str]`
  Reads `state/seen.json`, returns the set of seen post IDs. Treats missing / malformed file as empty.
- `save_seen(path: Path, seen: set[str]) -> None`
  Writes `state/seen.json`, trimmed to the most recent 200 IDs to keep the file small.
- `send_whatsapp(phone: str, apikey: str, message: str) -> None`
  HTTP GET to `https://api.callmebot.com/whatsapp.php` with `phone`, `apikey`, `text` params. Raises on non-2xx.
- `main() -> int`
  Orchestrates: fetch → diff → notify each new post → save. Exits 0 on success, non-zero on fatal errors.

`Post` is a small dataclass: `id: str`, `url: str`, `timestamp: str | None`.

### `state/seen.json`

```json
{"seen_ids": ["abc123", "def456", ...]}
```

Capped at the most recent 200 post IDs. Ordering within the array is not significant.

### `.github/workflows/check.yml`

- Trigger: `schedule: cron: "*/15 * * * *"` + `workflow_dispatch` for manual runs.
- Concurrency group `check-etoro` with `cancel-in-progress: false` to serialize overlapping runs.
- Steps:
  1. Checkout (`persist-credentials: true` — we need push rights to commit state).
  2. Setup Python + cache pip.
  3. `pip install -r requirements.txt`
  4. `playwright install --with-deps chromium`
  5. Run `python check_etoro.py`, passing secrets via env vars.
  6. If `state/seen.json` changed: `git add`, `git commit -m "state update [skip ci]"`, `git push`.
- Permissions: `contents: write` on the default `GITHUB_TOKEN`.

### `requirements.txt`

```
playwright
requests
```

## Data Flow

1. Workflow fires on cron.
2. Script launches Chromium, navigates to `https://www.etoro.com/people/harryh1993`.
3. Waits for feed container to render (e.g., `[data-etoro-automation-id="feed-post"]` or equivalent — exact selector determined during implementation).
4. Extracts post ID, URL, and timestamp for each visible post.
5. Loads `state/seen.json`.
6. Computes `new_posts = current_posts - seen_ids`.
7. If `|new_posts| > 5`: truncate to newest 5 (flood guard), log the rest.
8. For each new post (oldest-first, so WhatsApp order matches chronological): call CallMeBot with the post URL. On success, add ID to seen set. On failure, log and skip (will retry next run).
9. Write updated `state/seen.json`.
10. Workflow commits & pushes the file if changed.

## First-Run Behavior

On first run, `state/seen.json` does not exist. The script treats this as a "seed" run: it loads current posts, writes them all to `seen.json`, and sends NO notifications. This prevents spamming the user with posts from the past. Only posts appearing after the seed run will trigger notifications.

## Error Handling

| Scenario | Response |
|---|---|
| Playwright times out loading page | Retry once with a fresh browser context. If still failing, exit non-zero. No notification sent. Next cron fires in 15 min. |
| Feed selector matches 0 posts (eToro HTML change) | Log warning, do NOT modify `seen.json`, exit 0. Prevents spam when selector is later fixed. |
| CallMeBot returns non-2xx for a specific post | Log error, do NOT add that ID to `seen.json`, continue with next post. Will retry next run. |
| CallMeBot rate-limits (429) | Same as above — retry on next run. |
| `state/seen.json` missing or malformed JSON | Treat as empty → first-run seed behavior. |
| `> 5` new posts since last run | Notify newest 5, log others. Prevents flood. |
| Two workflow runs overlap | `concurrency` group serializes them. |
| Profile returns 404 / error page | Log, exit 0, no state change. |

All errors and info logs go to stdout, visible in GitHub Actions run logs.

## Security

- `CALLMEBOT_PHONE` and `CALLMEBOT_APIKEY` stored as GitHub Actions secrets, never in the repo.
- No eToro credentials needed (public profile).
- Repository should be **private** (the `seen.json` may contain internal post IDs; also avoids any ToS concerns around automated access). This means GitHub Actions minutes count against the 2000/month free tier — at 15-min cadence with ~1 min per run, that's ~2,880 min/month, which **exceeds free tier**.

### Actions-minutes mitigation

Two options, to be picked at implementation time:

1. **Make repo public** — unlimited free Actions minutes. Acceptable if no sensitive data beyond post IDs is stored. The secrets remain secret regardless of repo visibility.
2. **Increase cron interval to 30 minutes** — 1,440 min/month, well within free tier.

Recommendation: **public repo, 15-min cadence**. Post IDs are not sensitive.

## Testing

- **Unit test** (`test_diff.py`): verify `new_posts = current - seen` logic against hand-crafted fixtures. Covers the trimming-to-200 behavior and the first-run-seed behavior.
- **Manual end-to-end verification** on first deploy:
  1. Trigger workflow manually → confirm seed run writes `seen.json` and sends no WhatsApp.
  2. Ask the eToro user to post something → wait up to 15 min → confirm WhatsApp arrives.
  3. Check `seen.json` now contains the new post ID.
- No unit test for the scraping itself — eToro DOM is external and tests would be brittle. Selector correctness is verified by the manual E2E check.

## Open Questions (for implementation phase)

- **Exact feed selector** — needs inspection of the live rendered page in Playwright. Design assumes it's discoverable.
- **Post ID source** — ideally the post URL contains a stable ID (e.g., `/posts/<id>`). If only a permalink is available, use a hash of the URL as the ID.
- **Whether eToro serves a bot-detection challenge** to Playwright — if so, may need a User-Agent tweak or a brief pre-navigation wait. Mitigate at implementation time.
- **Repo visibility** — public (recommended) vs private with 30-min cron.
