"""Entry point: fetch posts for each tracked profile, diff, notify, save state."""
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from diff import Post, new_posts
from etoro_scraper import fetch_post_text, fetch_posts
from reply_generator import generate_reply
from state import load_seen, save_seen
from whatsapp import CallMeBotError, send_whatsapp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("check_etoro")

PROFILE_URLS: list[str] = [
    "https://www.etoro.com/people/jaynemesis",
    "https://www.etoro.com/people/michalhla",
    "https://www.etoro.com/people/JeppeKirkBonde",
    "https://www.etoro.com/people/CPHequities",
    "https://www.etoro.com/people/defense_investor",
    "https://www.etoro.com/people/ccalle",
    "https://www.etoro.com/people/krejzekemil",
    "https://www.etoro.com/people/aukie2008",
    "https://www.etoro.com/people/mcgintye",
    "https://www.etoro.com/people/triangulacapital",
]
STATE_DIR = Path("state")

# Keep WhatsApp messages comfortably below CallMeBot's URL-length budget by
# trimming the post excerpt embedded in the notification.
EXCERPT_MAX_CHARS = 280


def _username_from_url(profile_url: str) -> str:
    """Extract the eToro username (last path segment) from a profile URL."""
    path = urlparse(profile_url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def _state_path(username: str) -> Path:
    return STATE_DIR / f"seen-{username}.json"


def _excerpt(text: str, limit: int = EXCERPT_MAX_CHARS) -> str:
    """Single-line excerpt of `text`, capped at `limit` chars."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "\u2026"


def _build_message(username: str, post_url: str, post_text: str | None, reply: str | None) -> str:
    """Compose the WhatsApp notification body.

    Always includes who/where. Adds a post excerpt and suggested reply only
    when available - missing pieces degrade gracefully so the user still
    gets the link.
    """
    parts = [f"@{username} posted: {post_url}"]
    if post_text:
        parts.append("")
        parts.append(_excerpt(post_text))
    if reply:
        parts.append("")
        parts.append(f"Reply suggestion:\n{reply}")
    return "\n".join(parts)


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
        # Best-effort enrichment: scrape the post body, then ask the LLM for
        # a casual reply suggestion. Either step may return None - the
        # notification still goes out, just less rich.
        post_text = fetch_post_text(post.url)
        reply = generate_reply(post_text, username) if post_text else None
        message = _build_message(username, post.url, post_text, reply)
        try:
            send_whatsapp(phone, apikey, message)
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
