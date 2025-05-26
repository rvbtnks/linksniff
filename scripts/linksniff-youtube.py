# linksniff-youtube.py
# Version: 0.5 - Simple URL-based naming

import sys
import subprocess
import os
import re
from urllib.parse import urlparse, parse_qs

def sanitize_folder_name(name):
    """Clean folder name for filesystem compatibility"""
    if not name:
        return "Unknown"
    
    # Remove problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name[:80] if name else "Unknown"

def extract_name_from_url(url):
    """Extract meaningful name directly from YouTube URL"""
    url = url.strip()
    
    # Handle different YouTube URL formats
    if '/@' in url:
        # youtube.com/@ClaudeAI -> ClaudeAI
        name = url.split('/@')[1].split('/')[0].split('?')[0]
        return sanitize_folder_name(name)
    
    elif '/c/' in url:
        # youtube.com/c/ChannelName -> ChannelName  
        name = url.split('/c/')[1].split('/')[0].split('?')[0]
        return sanitize_folder_name(name)
    
    elif '/user/' in url:
        # youtube.com/user/username -> username
        name = url.split('/user/')[1].split('/')[0].split('?')[0]
        return sanitize_folder_name(name)
    
    elif '/channel/' in url:
        # youtube.com/channel/UCxxxxx -> UCxxxxx (channel ID)
        channel_id = url.split('/channel/')[1].split('/')[0].split('?')[0]
        # Try to get a better name from yt-dlp, fallback to channel ID
        try:
            result = subprocess.run([
                "yt-dlp", "--skip-download", "--print", "%(uploader)s", url
            ], capture_output=True, text=True, check=True, timeout=10)
            uploader = result.stdout.strip()
            if uploader and uploader.upper() != 'NA':
                return sanitize_folder_name(uploader)
        except:
            pass
        return sanitize_folder_name(channel_id)
    
    elif 'list=' in url:
        # Playlist URL - try to get playlist title
        try:
            result = subprocess.run([
                "yt-dlp", "--skip-download", "--print", "%(playlist_title)s", url
            ], capture_output=True, text=True, check=True, timeout=10)
            playlist_title = result.stdout.strip()
            if playlist_title and playlist_title.upper() != 'NA':
                return sanitize_folder_name(playlist_title)
        except:
            pass
        return "Playlist"
    
    elif 'watch?v=' in url or 'youtu.be/' in url:
        # Single video - try to get uploader
        try:
            result = subprocess.run([
                "yt-dlp", "--skip-download", "--print", "%(uploader)s", url
            ], capture_output=True, text=True, check=True, timeout=10)
            uploader = result.stdout.strip()
            if uploader and uploader.upper() != 'NA':
                return sanitize_folder_name(uploader)
        except:
            pass
        return "Video"
    
    # Fallback
    return "YouTube_Download"

def determine_content_type(url):
    """Simple content type detection"""
    if any(x in url for x in ['/channel/', '/user/', '/c/', '/@']):
        return "channel"
    elif 'list=' in url:
        return "playlist"
    else:
        return "video"

def main():
    if len(sys.argv) != 2:
        print("Usage: python linksniff-youtube.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1].strip()
    
    # Validate URL
    if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
        print("Error: Please provide a valid YouTube URL")
        sys.exit(1)

    print(f"Processing: {url}")
    
    # Extract folder name from URL
    folder_name = extract_name_from_url(url)
    content_type = determine_content_type(url)
    
    print(f"Content type: {content_type}")
    print(f"Folder name: {folder_name}")
    
    # Create output directory
    os.makedirs(folder_name, exist_ok=True)
    
    # Set up output template
    output_template = os.path.join(folder_name, "%(title).150s.%(ext)s")
    
    # Build yt-dlp command
    command = [
        "yt-dlp",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "--embed-metadata",
        "--embed-thumbnail", 
        "--embed-subs",
        "--sub-langs", "en.*,en",
        "--write-subs",
        "--merge-output-format", "mp4",
        "--restrict-filenames",
        "--no-overwrites",
        "--ignore-errors",
        "-o", output_template,
    ]
    
    # Adjust for content type
    if content_type == "video":
        command.append("--no-playlist")
    elif content_type == "channel":
        command.extend(["--playlist-end", "25"])  # Limit channel downloads
    
    command.append(url)
    
    print(f"Starting download to: {folder_name}/")
    
    try:
        process = subprocess.run(command, check=False)
        
        if process.returncode == 0:
            print(f"✅ Download completed!")
        else:
            print(f"⚠️  Download completed with some issues")
            
        print(f"📁 Files saved in: {folder_name}/")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Download interrupted")
        print(f"📁 Check folder: {folder_name}/")

if __name__ == "__main__":
    main()