"""Entry point: fetch posts for each tracked profile, diff, notify, save state."""
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from diff import Post, new_posts
from etoro_scraper import fetch_posts
from state import load_seen, save_seen
from whatsapp import CallMeBotError, send_whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("check_etoro")

PROFILE_URLS: list[str] = [
    "https://www.etoro.com/people/harryh1993",
    "https://www.etoro.com/people/jaynemesis",
    "https://www.etoro.com/people/michalhla",
    "https://www.etoro.com/people/JeppeKirkBonde",
    "https://www.etoro.com/people/CPHequities",
]
STATE_DIR = Path("state")


def _username_from_url(profile_url: str) -> str:
    """Extract the eToro username (last path segment) from a profile URL."""
    path = urlparse(profile_url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def _state_path(username: str) -> Path:
    return STATE_DIR / f"seen-{username}.json"


def _process_profile(profile_url: str, phone: str, apikey: str) -> None:
    """Scrape, diff, notify, and persist state for one profile.

    Raises on scrape failure; caller handles per-profile isolation.
    """
    username = _username_from_url(profile_url)
    state_path = _state_path(username)
    log = logging.getLogger(f"check_etoro.{username}")

    current = fetch_posts(profile_url)
    if not current:
        log.warning("0 posts scraped - not modifying state")
        return

    seen = load_seen(state_path)

    # First-run seed: no prior state means we treat everything as already seen.
    # This prevents spamming historical posts on first deploy.
    if not seen:
        log.info("First run - seeding %d current posts as seen, no notifications", len(current))
        save_seen(state_path, [p.id for p in current])
        return

    to_notify: list[Post] = new_posts(current, seen)
    if not to_notify:
        log.info("No new posts (%d current, %d seen)", len(current), len(seen))
        return

    log.info("Notifying %d new post(s)", len(to_notify))

    # Notify oldest-first so WhatsApp order matches chronological order.
    # `current` is newest-first, so reverse to_notify.
    updated_seen = list(seen)
    for post in reversed(to_notify):
        try:
            send_whatsapp(phone, apikey, f"@{username} posted: {post.url}")
            updated_seen.append(post.id)
        except CallMeBotError as e:
            log.error("Failed to send for post %s: %s", post.id, e)
            # Do NOT add to seen - will retry next run.

    save_seen(state_path, updated_seen)


def main() -> int:
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not apikey:
        logger.error("CALLMEBOT_PHONE and CALLMEBOT_APIKEY must be set")
        return 2

    failures = 0
    for profile_url in PROFILE_URLS:
        username = _username_from_url(profile_url)
        try:
            _process_profile(profile_url, phone, apikey)
        except Exception as e:  # noqa: BLE001 - isolate one profile's failure from others
            logger.exception("Profile %s failed: %s", username, e)
            failures += 1

    if failures == len(PROFILE_URLS):
        logger.error("All %d profiles failed", failures)
        return 1
    if failures:
        logger.warning("%d/%d profiles failed (continuing)", failures, len(PROFILE_URLS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
