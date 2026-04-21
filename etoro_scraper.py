"""Scrape post IDs and URLs from an eToro public profile page."""
import logging
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from diff import Post

logger = logging.getLogger(__name__)

# Selectors discovered by dumping the rendered profile page on 2026-04-20 / 2026-04-21.
# eToro uses Angular with `automation-id` attrs (note: NOT `data-etoro-automation-id`).
#
# Public profile exposes two sources of posts to logged-out viewers:
#   1. Pinned posts section (renders immediately):
#        <a automation-id="pinned-posts-post" href="/posts/<uuid>">
#   2. "Discussions" feed (Angular CDK virtual scroll - only renders on scroll):
#        <a automation-id="feed-timestamp-link" href="/posts/<uuid>">
#        sibling <div automation-id="feed-timestamp-label" title="DD/MM/YYYY HH:MM:SS">
#
# Post IDs are UUIDs like "42a3c620-f073-11f0-8080-800007975dfe".
# If eToro changes their DOM these WILL need updating.
PINNED_POST_SELECTOR = 'a[automation-id="pinned-posts-post"]'
FEED_POST_SELECTOR = 'a[automation-id="feed-timestamp-link"]'
POST_LINK_SELECTOR = f"{PINNED_POST_SELECTOR}, {FEED_POST_SELECTOR}"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PAGE_TIMEOUT_MS = 45_000
SELECTOR_TIMEOUT_MS = 30_000
# Scroll parameters for forcing the virtualised Discussions feed to render.
SCROLL_STEPS = 12
SCROLL_PIXELS = 1200
SCROLL_SETTLE_MS = 600

# eToro post IDs are UUIDs (e.g. 42a3c620-f073-11f0-8080-800007975dfe).
# We require the UUID-like shape to filter out config/query-string noise.
POST_ID_RE = re.compile(r"/posts/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")


def _extract_post_id(href: str) -> str | None:
    m = POST_ID_RE.search(href)
    return m.group(1) if m else None


def _scroll_to_load_feed(page) -> None:
    """Scroll the page so Angular CDK virtual-scroll renders feed posts.

    The Discussions feed doesn't materialise until it enters the viewport, and
    more items render as the user scrolls further. We scroll until the count of
    feed anchors stops growing for two consecutive steps.
    """
    last_count = -1
    stable = 0
    for step in range(SCROLL_STEPS):
        page.mouse.wheel(0, SCROLL_PIXELS)
        page.wait_for_timeout(SCROLL_SETTLE_MS)
        count = len(page.query_selector_all(FEED_POST_SELECTOR))
        logger.debug("scroll step %d: feed anchors=%d", step, count)
        if count == last_count:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last_count = count


def fetch_posts(profile_url: str) -> list[Post]:
    """Fetch visible posts from a public eToro profile.

    Returns newest-first (DOM order). Combines pinned posts and the Discussions
    feed, deduping by post UUID. Raises on unrecoverable browser errors.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1600, "height": 1000},
        )
        page = ctx.new_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            try:
                page.wait_for_selector(POST_LINK_SELECTOR, timeout=SELECTOR_TIMEOUT_MS)
            except PWTimeout:
                logger.warning("No post links found within timeout - profile may have no posts or DOM changed")
                return []

            # Let initial content settle, then force the virtual feed to render.
            page.wait_for_timeout(1500)
            _scroll_to_load_feed(page)
            page.wait_for_timeout(1000)

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

                # For feed posts, the enclosing feed-timestamp-label div carries
                # an absolute timestamp in its `title` attribute (DD/MM/YYYY HH:MM:SS).
                # Pinned anchors aren't wrapped in that label; timestamp stays None.
                timestamp = a.evaluate(
                    """node => {
                        const label = node.closest('[automation-id="feed-timestamp-label"]');
                        return label ? label.getAttribute('title') : null;
                    }"""
                )

                posts.append(Post(id=post_id, url=url, timestamp=timestamp))
            logger.info("Scraped %d unique posts", len(posts))
            return posts
        finally:
            browser.close()
