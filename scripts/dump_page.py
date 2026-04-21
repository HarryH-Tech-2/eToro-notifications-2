"""Debug helper: dump rendered HTML of an eToro profile to inspect structure."""
import sys
from playwright.sync_api import sync_playwright


def main(url: str, out_path: str = "page_dump.html") -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3000)  # extra settle time
        html = page.content()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Wrote {len(html)} bytes to {out_path}")
        print(f"Current URL: {page.url}")
        print(f"Title: {page.title()}")
        browser.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.etoro.com/people/harryh1993"
    out = sys.argv[2] if len(sys.argv) > 2 else "page_dump.html"
    main(url, out)
