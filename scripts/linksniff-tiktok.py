#!/usr/bin/env python3
"""
linksniff-tiktok.py v0.4
- Pure Python implementation using Playwright
- Replicates the JavaScript scraping logic
- Extracts username from TikTok profile URL
- Creates folder based on username
- Scrapes profile and generates text file
- Runs yt-dlp on the generated text file
"""

import sys
import os
import re
import time
import subprocess
import argparse
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

def get_username_from_url(tiktok_url):
    """Extract username from TikTok URL"""
    match = re.search(r'tiktok\.com/@([^/?&]+)', tiktok_url)
    if not match:
        raise ValueError("Invalid TikTok profile URL. Expected format: tiktok.com/@username")
    return match.group(1)

def find_video_containers(page):
    """Find video containers using the same selectors as the JavaScript"""
    # These are the CSS selectors from the original JavaScript
    selectors = [
        ".tiktok-1uqux2o-DivItemContainerV2",
        ".css-ps7kg7-DivThreeColumnItemContainer", 
        ".tiktok-x6y88p-DivItemContainerV2",
        ".css-1uqux2o-DivItemContainerV2",
        ".css-x6y88p-DivItemContainerV2",
        ".css-1soki6-DivItemContainerForSearch",
        ".css-ps7kg7-DivThreeColumnItemContainer"
    ]
    
    # Try each selector and combine results
    containers = []
    for selector in selectors:
        try:
            elements = page.query_selector_all(selector)
            containers.extend(elements)
        except:
            continue
    
    return containers

def extract_video_urls(containers):
    """Extract video URLs from containers"""
    urls = set()  # Use set to avoid duplicates
    
    for container in containers:
        try:
            # Find all links within this container
            links = container.query_selector_all("a")
            
            for link in links:
                href = link.get_attribute("href")
                if href and ("/video/" in href or "/photo/" in href):
                    # Make sure it's a full URL
                    if not href.startswith("http"):
                        href = "https://www.tiktok.com" + href
                    urls.add(href)
        except Exception as e:
            print(f"Error extracting from container: {e}")
            continue
    
    return list(urls)

def scroll_and_load_content(page, max_scrolls=50):
    """Scroll page to load more content via infinite scroll"""
    print("Starting infinite scroll to load all content...")
    
    all_urls = set()
    no_new_content_count = 0
    scroll_count = 0
    
    while scroll_count < max_scrolls and no_new_content_count < 5:
        scroll_count += 1
        print(f"Scroll {scroll_count}: ", end="", flush=True)
        
        # Get current content
        containers = find_video_containers(page)
        current_urls = extract_video_urls(containers)
        new_urls = set(current_urls) - all_urls
        
        if new_urls:
            all_urls.update(new_urls)
            no_new_content_count = 0
            print(f"Found {len(new_urls)} new videos (total: {len(all_urls)})")
        else:
            no_new_content_count += 1
            print(f"No new content (attempt {no_new_content_count}/5)")
        
        # Check for loading animations
        loading_elements = page.query_selector_all(".tiktok-qmnyxf-SvgContainer")
        if loading_elements:
            print("  Loading animation detected, waiting...")
            time.sleep(2)
            continue
        
        # Scroll to bottom
        current_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })")
        
        # Wait for potential new content to load
        time.sleep(2)
        
        # Check if page height changed
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == current_height:
            print("  Page height unchanged")
        else:
            print(f"  Page height: {current_height} -> {new_height}")
        
        # Small random delay to avoid being too robotic
        time.sleep(1 + (scroll_count % 3))
    
    print(f"Scrolling complete. Found {len(all_urls)} total video URLs")
    return list(all_urls)

def save_urls_to_file(urls, filepath):
    """Save URLs to text file for yt-dlp"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url + '\n')
    print(f"Saved {len(urls)} URLs to {filepath}")

def run_ytdlp(folder_path, txt_file):
    """Run yt-dlp on the generated text file"""
    print(f"Running yt-dlp on {txt_file}...")
    
    original_cwd = os.getcwd()
    os.chdir(folder_path)
    
    try:
        cmd = [
            'yt-dlp',
            '-a', os.path.basename(txt_file),
            '--no-overwrites',
            '--ignore-errors',
            '--concurrent-fragments', '4'
        ]
        
        subprocess.run(cmd, check=True)
        print("✅ yt-dlp completed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ yt-dlp failed with exit code {e.returncode}")
        raise
    finally:
        os.chdir(original_cwd)

def main():
    parser = argparse.ArgumentParser(description='Download TikTok profile videos using Python scraper')
    parser.add_argument('tiktok_url', help='TikTok profile URL (e.g., https://tiktok.com/@username)')
    parser.add_argument('-uh', '--unheadless', action='store_true', 
                       help='Run browser in visible mode (default is headless)')
    parser.add_argument('--max-scrolls', type=int, default=50,
                       help='Maximum number of scroll attempts (default: 50)')
    
    args = parser.parse_args()
    
    try:
        # Extract username and create folder
        username = get_username_from_url(args.tiktok_url)
        folder_path = os.path.join(os.getcwd(), username)
        os.makedirs(folder_path, exist_ok=True)
        
        print(f"Processing TikTok profile: @{username}")
        print(f"Output folder: {folder_path}")
        print(f"Browser mode: {'Visible' if args.unheadless else 'Headless'}")
        
        # Check if we already have a text file with content
        txt_filename = f"{username}_links.txt"
        txt_filepath = os.path.join(folder_path, txt_filename)
        
        if os.path.exists(txt_filepath) and os.path.getsize(txt_filepath) > 0:
            print(f"Found existing links file: {txt_filename}")
            with open(txt_filepath, 'r') as f:
                existing_urls = [line.strip() for line in f if line.strip()]
            
            if len(existing_urls) > 5:  # Arbitrary threshold for "enough content"
                print(f"File has {len(existing_urls)} URLs, skipping scraping...")
                run_ytdlp(folder_path, txt_filepath)
                print(f"🎉 All done! Check the '{username}' folder for your downloads.")
                return
            else:
                print("File has minimal content, proceeding with scraping...")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=not args.unheadless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            try:
                print(f"Navigating to {args.tiktok_url}...")
                page.goto(args.tiktok_url, timeout=60000)
                
                # Wait for page to load
                print("Waiting for page to load...")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                # Wait a bit more for dynamic content
                time.sleep(5)
                
                # Check if we can find video containers
                initial_containers = find_video_containers(page)
                print(f"Found {len(initial_containers)} initial video containers")
                
                if len(initial_containers) == 0:
                    print("⚠️  No video containers found. Page might not have loaded properly.")
                    print("Trying to wait longer...")
                    time.sleep(10)
                    initial_containers = find_video_containers(page)
                    print(f"Found {len(initial_containers)} containers after waiting")
                
                if len(initial_containers) == 0:
                    print("❌ Still no containers found. The page structure might have changed.")
                    print("Available elements on page:")
                    # Debug: show what elements are available
                    all_divs = page.query_selector_all("div[class*='tiktok'], div[class*='css-']")
                    for div in all_divs[:10]:  # Show first 10
                        class_name = div.get_attribute("class")
                        print(f"  - {class_name}")
                    return
                
                # Start scrolling and collecting URLs
                all_urls = scroll_and_load_content(page, max_scrolls=args.max_scrolls)
                
                if not all_urls:
                    print("❌ No video URLs found!")
                    return
                
                # Save URLs to file
                save_urls_to_file(all_urls, txt_filepath)
                
                # Run yt-dlp
                run_ytdlp(folder_path, txt_filepath)
                
                print(f"🎉 All done! Check the '{username}' folder for your downloads.")
                
            except Exception as e:
                print(f"❌ Error during scraping: {str(e)}")
                raise
            finally:
                browser.close()
                
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()