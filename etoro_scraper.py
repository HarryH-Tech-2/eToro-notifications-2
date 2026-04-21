"""Scrape post IDs and URLs from an eToro public profile page."""
import logging
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from diff import Post

logger = logging.getLogger(__name__)

# Selectors discovered by dumping the rendered profile page on 2026-04-20.
# eToro uses Angular with `automation-id` attrs (note: NOT `data-etoro-automation-id`).
# Post links live inside <a automation-id="pinned-posts-post" href="/posts/<uuid>">.
# Post IDs are UUIDs like "42a3c620-f073-11f0-8080-800007975dfe".
# If eToro changes their DOM these WILL need updating.
POST_LINK_SELECTOR = 'a[automation-id="pinned-posts-post"]'

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT_MS = 45_000
SELECTOR_TIMEOUT_MS = 30_000

# eToro post IDs are UUIDs (e.g. 42a3c620-f073-11f0-8080-800007975dfe).
# We require the UUID-like shape to filter out config/query-string noise.
POST_ID_RE = re.compile(r"/posts/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


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
                page.wait_for_selector(POST_LINK_SELECTOR, timeout=SELECTOR_TIMEOUT_MS)
            except PWTimeout:
                logger.warning("No post links found within timeout - profile may have no posts or DOM changed")
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
