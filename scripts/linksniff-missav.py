#!/usr/bin/env python3
"""
linksniff-missav.py v0.1
- only grabs the first .m3u8 link found
- uses the page URL’s final path segment for the yt-dlp output filename
- runs yt-dlp automatically
"""

import sys
import time
import os
import subprocess
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def get_embedded_urls(page_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/88.0.4324.182 Safari/537.36")
        )
        page = ctx.new_page()
        page.set_extra_http_headers({"Referer": page_url})
        page.goto(page_url)
        time.sleep(10)  # wait for any JS/cloudflare

        # gather all possible URLs
        links = [a.get_attribute("href")    for a in page.query_selector_all("a[href]")]
        iframes = [i.get_attribute("src")   for i in page.query_selector_all("iframe[src]")]
        objects = [o.get_attribute("data")  for o in page.query_selector_all("object[data]")]
        vid = page.query_selector("div.plyr__video-wrapper video")
        video_src = [vid.get_attribute("src")] if vid and vid.get_attribute("src") else []

        ctx.close()
        browser.close()
        return [u for u in (links + iframes + objects + video_src) if u]

def main():
    if len(sys.argv) != 2:
        print("Usage: python linksniff-missav.py <PAGE_URL>")
        sys.exit(1)

    page_url = sys.argv[1]
    urls = get_embedded_urls(page_url)

    # 1) filter for .m3u8
    m3u8_links = [u for u in urls if ".m3u8" in u]
    if not m3u8_links:
        print("❌ No .m3u8 links found on the page.")
        sys.exit(2)

    m3u8_url = m3u8_links[0]
    # 2) extract filename from page URL
    basename = os.path.basename(urlparse(page_url).path) or "output"
    output_template = f"{basename}.%(ext)s"

    # 3) download with yt-dlp
    print(f"⏬ Downloading {m3u8_url!r} → {output_template!r}")
    subprocess.run(["yt-dlp", "-N4", "-o", output_template, m3u8_url], check=True)

if __name__ == "__main__":
    main()
