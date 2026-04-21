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
