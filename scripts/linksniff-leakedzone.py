#!/usr/bin/env python3
"""
Unified LeakedZone Scraper - Simplified
"""

import asyncio
import os
import argparse
import subprocess
import re
import aiohttp

# Argument Parsing
parser = argparse.ArgumentParser(description="Scrape LeakedZone pages for photos and videos.")
parser.add_argument("url", help="The URL of the page to scrape.")
parser.add_argument("-dh", "--debug-headless", action="store_true", help="Enable debug mode with visible browser.")
parser.add_argument("--photos-only", action="store_true", help="Only download photos, skip videos.")
parser.add_argument("--videos-only", action="store_true", help="Only download videos, skip photos.")
args = parser.parse_args()

# Globals
found_m3u8_urls = []

async def scroll_to_bottom(page):
    """Scroll to load all content."""
    print("Loading all content...")
    prev_height = await page.evaluate('document.body.scrollHeight')
    
    while True:
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)
        curr_height = await page.evaluate('document.body.scrollHeight')
        if curr_height == prev_height:
            break
        prev_height = curr_height
    
    print('All content loaded.')

async def get_all_links(page):
    """Extract photo and video links."""
    links = await page.evaluate('() => Array.from(document.querySelectorAll("a")).map(a => a.href)')
    pattern = re.compile(r'https://leakedzone\.com/[^/]+/(photo|video)/\d+')
    return [link for link in links if pattern.match(link)]

async def download_image(url, folder, photo_id):
    """Download single image."""
    os.makedirs(folder, exist_ok=True)
    
    # Use photo ID as filename, keep original extension
    original_filename = os.path.basename(url)
    extension = os.path.splitext(original_filename)[1] or '.jpg'
    filename = f"{photo_id}{extension}"
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        print(f"Skip existing: {filename}")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        f.write(await response.read())
                    print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

async def download_video(m3u8_url, username):
    """Download video using yt-dlp."""
    folder = os.path.join(username, 'videos')
    os.makedirs(folder, exist_ok=True)
    
    # Find next available filename
    counter = 1
    while os.path.exists(os.path.join(folder, f"video{counter:04d}.mp4")):
        counter += 1
    
    filename = os.path.join(folder, f"video{counter:04d}.mp4")
    print(f"Downloading video: {filename}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--retries", "5", "--fragment-retries", "5", "-o", filename, m3u8_url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=600)
        
        if proc.returncode == 0:
            print(f"Video downloaded: {filename}")
        else:
            print(f"Video download failed for {m3u8_url}")
    except Exception as e:
        print(f"Video download error: {e}")

def handle_request(request):
    """Capture .m3u8 URLs from network requests."""
    if ".m3u8" in request.url:
        print(f"Found .m3u8: {request.url}")
        found_m3u8_urls.append(request.url)

async def process_link(page, link):
    """Process a single photo or video link."""
    username = link.split('/')[3]
    link_type = 'photo' if '/photo/' in link else 'video'
    
    print(f"Processing {link_type}: {link}")
    
    try:
        if link_type == 'video':
            page.on('request', handle_request)
        
        await page.goto(link, wait_until='domcontentloaded')
        await page.wait_for_load_state('networkidle')
        
        if link_type == 'photo':
            # Extract photo ID from URL
            photo_id = link.split('/')[-1]
            
            # Get images
            image_urls = await page.evaluate('''
                () => Array.from(document.querySelectorAll('img[src*="storage/images/"]')).map(img => img.src)
            ''')
            
            if image_urls:
                folder = os.path.join(username, 'photos')
                tasks = [download_image(url, folder, photo_id) for url in image_urls]
                await asyncio.gather(*tasks, return_exceptions=True)
                print(f"Processed {len(image_urls)} photos from {username}")
        
        elif link_type == 'video':
            # Click to trigger video loading
            viewport = page.viewport_size
            if viewport:
                await page.mouse.click(viewport['width'] // 2, viewport['height'] // 2)
                await asyncio.sleep(3)  # Wait for video to start loading
            
        if link_type == 'video':
            page.remove_listener('request', handle_request)
            
    except Exception as e:
        print(f"Error processing {link}: {e}")

async def main():
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=not args.debug_headless)
        page = await browser.new_page()
        
        try:
            print(f"Navigating to: {args.url}")
            await page.goto(args.url, wait_until='domcontentloaded')
            
            # Load all content
            await scroll_to_bottom(page)
            
            # Get all links
            links = await get_all_links(page)
            print(f"Found {len(links)} links")
            
            # Filter by type
            photo_links = [l for l in links if '/photo/' in l]
            video_links = [l for l in links if '/video/' in l]
            
            if args.photos_only:
                video_links = []
            elif args.videos_only:
                photo_links = []
            
            print(f"Processing {len(photo_links)} photos, {len(video_links)} videos")
            
            # Process all links
            all_links = photo_links + video_links
            for link in all_links:
                await process_link(page, link)
            
            # Download any videos we found
            if video_links and found_m3u8_urls:
                print(f"\nDownloading {len(found_m3u8_urls)} videos...")
                username = args.url.split('/')[-1] or 'unknown'
                for m3u8_url in found_m3u8_urls:
                    await download_video(m3u8_url, username)
            
            if args.debug_headless:
                await asyncio.sleep(10)
                
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())