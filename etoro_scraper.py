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
