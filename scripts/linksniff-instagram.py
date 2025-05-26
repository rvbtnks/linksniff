#!/usr/bin/env python3

import os
import sys
import requests
import time
import argparse
from datetime import datetime
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright
import re

def extract_username_from_url(instagram_url):
    """Extract username from Instagram URL"""
    # Remove trailing slash and extract username
    clean_url = instagram_url.rstrip('/')
    username = clean_url.split('/')[-1]
    return username

def create_directories(username):
    """Create directory structure for downloads"""
    base_dir = username
    posts_dir = os.path.join(base_dir, 'posts')
    stories_dir = os.path.join(base_dir, 'stories')
    reels_dir = os.path.join(base_dir, 'reels')
    
    os.makedirs(posts_dir, exist_ok=True)
    os.makedirs(stories_dir, exist_ok=True)
    os.makedirs(reels_dir, exist_ok=True)
    
    return base_dir, posts_dir, stories_dir, reels_dir

def get_file_type_from_headers(url):
    """Determine file type from HTTP headers"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Make a HEAD request to get headers without downloading the full file
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        
        content_type = response.headers.get('content-type', '').lower()
        print(f"Content-Type: {content_type}")
        
        if 'video' in content_type:
            if 'mp4' in content_type:
                return 'video', '.mp4'
            elif 'webm' in content_type:
                return 'video', '.webm'
            elif 'quicktime' in content_type or 'mov' in content_type:
                return 'video', '.mov'
            else:
                return 'video', '.mp4'  # Default video extension
        elif 'image' in content_type:
            if 'jpeg' in content_type or 'jpg' in content_type:
                return 'image', '.jpg'
            elif 'png' in content_type:
                return 'image', '.png'
            elif 'gif' in content_type:
                return 'image', '.gif'
            elif 'webp' in content_type:
                return 'image', '.webp'
            else:
                return 'image', '.jpg'  # Default image extension
        
        # If content-type is not clear, try to get a small sample of the file
        return get_file_type_from_content(url, headers)
    
    except Exception as e:
        print(f"Error checking headers for {url}: {e}")
        return 'unknown', '.bin'

def get_file_type_from_content(url, headers):
    """Determine file type by examining file content (magic bytes)"""
    try:
        # Download first 1KB to check magic bytes
        headers_dict = headers.copy()
        headers_dict['Range'] = 'bytes=0-1023'
        
        response = requests.get(url, headers=headers_dict, timeout=10)
        content = response.content
        
        # Check magic bytes for common formats
        if content.startswith(b'\xff\xd8\xff'):  # JPEG
            return 'image', '.jpg'
        elif content.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
            return 'image', '.png'
        elif content.startswith(b'GIF8'):  # GIF
            return 'image', '.gif'
        elif content.startswith(b'RIFF') and b'WEBP' in content[:12]:  # WebP
            return 'image', '.webp'
        elif (content.startswith(b'\x00\x00\x00\x18ftypmp4') or  # MP4
              content.startswith(b'\x00\x00\x00\x20ftypmp4') or
              b'ftyp' in content[:20]):
            return 'video', '.mp4'
        elif content.startswith(b'\x1a\x45\xdf\xa3'):  # WebM/MKV
            return 'video', '.webm'
        elif content.startswith(b'ftypqt'):  # QuickTime MOV
            return 'video', '.mov'
        else:
            print(f"Unknown file type, first 20 bytes: {content[:20]}")
            return 'unknown', '.bin'
    
    except Exception as e:
        print(f"Error checking content for {url}: {e}")
        return 'unknown', '.bin'

def download_file_with_type_detection(url, base_filepath):
    """Download a file and determine its type, then save with correct extension"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # First, determine the file type
        file_type, extension = get_file_type_from_headers(url)
        
        # Create the final filepath with correct extension
        final_filepath = f"{base_filepath}_{file_type}{extension}"
        
        print(f"Downloading {file_type}: {os.path.basename(final_filepath)}")
        
        # Now download the full file
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(final_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {final_filepath}")
        return True, file_type
    
    except Exception as e:
        print(f"❌ Failed to download {url}: {str(e)}")
        return False, 'unknown'

def click_tab_and_wait(page, tab_name):
    """Click a specific tab and wait for content to load"""
    print(f"Switching to {tab_name} tab...")
    
    # Find and click the tab button
    tab_button = page.locator(f'button:has-text("{tab_name}")').first
    tab_button.click()
    
    # Wait a moment for the tab to become active and content to start loading
    time.sleep(3)
    
    # Wait for the media list to be present (it might take a moment)
    try:
        page.wait_for_selector('.profile-media-list', timeout=10000)
        print(f"{tab_name.capitalize()} tab loaded successfully")
        return True
    except:
        print(f"No content found in {tab_name} tab or tab failed to load")
        return False

def download_tab_content(page, tab_name, target_dir, username):
    """Download all content from a specific tab"""
    print(f"\n--- Processing {tab_name.upper()} ---")
    
    # Click the tab and wait for content
    if not click_tab_and_wait(page, tab_name):
        print(f"Skipping {tab_name} - no content or failed to load")
        return 0, 0, 0
    
    # Scroll to load all content for this tab
    total_media = scroll_and_load_content(page)
    
    if total_media == 0:
        print(f"No media found in {tab_name} tab")
        return 0, 0, 0
    
    # Get all download buttons for this tab
    download_buttons = page.query_selector_all('.button__download')
    print(f"Found {len(download_buttons)} {tab_name} files to download...")
    
    downloaded_count = 0
    video_count = 0
    image_count = 0
    
    # Download each media file
    for i, button in enumerate(download_buttons):
        media_url = button.get_attribute('href')
        if not media_url:
            continue
        
        # Create base filename without extension
        base_filename = f"{username}_{tab_name}_{i+1:03d}"
        base_filepath = os.path.join(target_dir, base_filename)
        
        # Download the file with type detection
        success, file_type = download_file_with_type_detection(media_url, base_filepath)
        
        if success:
            downloaded_count += 1
            if file_type == 'video':
                video_count += 1
            elif file_type == 'image':
                image_count += 1
        
        # Small delay to be respectful to the server
        time.sleep(1)
    
    print(f"Downloaded {downloaded_count} files from {tab_name} ({video_count} videos, {image_count} images)")
    return downloaded_count, video_count, image_count

def scroll_and_load_content(page):
    """Scroll down gradually to load all content via infinite scroll"""
    print("Loading all content via infinite scroll...")
    
    previous_count = 0
    no_change_count = 0
    scroll_position = 0
    scroll_increment = 800  # Scroll in smaller increments
    
    while True:
        # Get current number of media items
        current_count = len(page.query_selector_all('.profile-media-list__item'))
        
        if current_count > previous_count:
            print(f"Loaded {current_count} media items...")
            previous_count = current_count
            no_change_count = 0
        else:
            no_change_count += 1
        
        # If no new content loaded after 5 attempts, we're done
        if no_change_count >= 5:
            print("No new content detected, finishing...")
            break
        
        # Scroll down gradually instead of jumping to bottom
        scroll_position += scroll_increment
        page.evaluate(f"window.scrollTo(0, {scroll_position})")
        
        # Wait longer for content to load
        time.sleep(3)
        
        # Check if we've reached the bottom of the page
        page_height = page.evaluate("document.body.scrollHeight")
        if scroll_position >= page_height:
            # Wait a bit longer at the bottom to ensure everything loads
            time.sleep(5)
            # Try scrolling to absolute bottom one more time
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
    
    print(f"Finished loading. Total media items: {current_count}")
    return current_count

def main():
    parser = argparse.ArgumentParser(description='Download Instagram profile media via sssinstagram.com')
    parser.add_argument('instagram_url', help='Instagram profile URL')
    parser.add_argument('-uh', '--unheadless', action='store_true', 
                       help='Run browser in visible mode (default is headless)')
    
    args = parser.parse_args()
    
    instagram_url = args.instagram_url
    headless_mode = not args.unheadless  # Default to headless unless -uh flag is used
    
    username = extract_username_from_url(instagram_url)
    
    print(f"Processing Instagram profile: {username}")
    print(f"Browser mode: {'Headless' if headless_mode else 'Visible'}")
    
    # Create directories
    base_dir, posts_dir, stories_dir, reels_dir = create_directories(username)
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=headless_mode)
        page = browser.new_page()
        
        try:
            # Navigate to sssinstagram.com
            print("Loading sssinstagram.com...")
            page.goto('https://sssinstagram.com/')
            page.wait_for_load_state('networkidle')
            
            # Enter Instagram URL in search box
            print(f"Searching for {instagram_url}...")
            search_input = page.wait_for_selector('#input.form__input')
            search_input.fill(instagram_url)
            
            # Submit the form (press Enter)
            search_input.press('Enter')
            
            # Wait for results to load
            print("Waiting for profile to load...")
            page.wait_for_selector('.output-profile', timeout=30000)
            
            # Scroll to load all content
            total_media = scroll_and_load_content(page)
            
            # Extract profile information
            print("Extracting profile information...")
            
            # Get avatar image
            avatar_img = page.query_selector('.avatar__image')
            avatar_url = avatar_img.get_attribute('src') if avatar_img else None
            
            # Get profile text information
            username_elem = page.query_selector('.user-info__username')
            username_text = username_elem.inner_text() if username_elem else "N/A"
            
            stats_elem = page.query_selector('.user-info__stats')
            stats_text = stats_elem.inner_text() if stats_elem else "N/A"
            
            fullname_elem = page.query_selector('.user-info__full-name')
            fullname_text = fullname_elem.inner_text() if fullname_elem else "N/A"
            
            bio_elem = page.query_selector('.user-info__biography')
            bio_text = bio_elem.inner_text() if bio_elem else "no bio"
            
            # Create profile info text file
            profile_info_path = os.path.join(base_dir, 'profile_info.txt')
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(profile_info_path, 'w', encoding='utf-8') as f:
                f.write(f"Script run date: {current_date}\n")
                f.write(f"Username: {username_text}\n")
                f.write(f"Full name: {fullname_text}\n")
                f.write(f"Stats: {stats_text}\n")
                f.write(f"Biography: {bio_text}\n")
            
            print(f"Profile info saved to: {profile_info_path}")
            
            # Download avatar if available
            if avatar_url:
                avatar_base = os.path.join(base_dir, f"avatar_{username}")
                success, _ = download_file_with_type_detection(avatar_url, avatar_base)
            
            # Process each tab and download content
            tabs_to_process = [
                ('posts', posts_dir),
                ('stories', stories_dir),
                ('reels', reels_dir)
            ]
            
            total_downloads = 0
            total_videos = 0
            total_images = 0
            
            for tab_name, target_dir in tabs_to_process:
                downloaded_count, video_count, image_count = download_tab_content(page, tab_name, target_dir, username)
                total_downloads += downloaded_count
                total_videos += video_count
                total_images += image_count
            
            print(f"\n=== DOWNLOAD SUMMARY ===")
            print(f"Total files downloaded: {total_downloads}")
            print(f"- Videos: {total_videos}")
            print(f"- Images: {total_images}")
            print(f"Files saved in: {base_dir}/")
            print(f"- Profile info: profile_info.txt")
            if avatar_url:
                print(f"- Avatar: avatar_{username}.*")
            print(f"- Posts: posts/")
            print(f"- Stories: stories/")
            print(f"- Reels: reels/")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()