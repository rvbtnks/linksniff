# LinkSniff Scripts Documentation

This folder contains platform-specific download scripts that can be used either through the LinkSniff web UI or independently from the command line.

## How Script Selection Works

LinkSniff automatically chooses which script to run based on the URL domain:
- `https://www.youtube.com/watch?v=xyz` → `linksniff-youtube.py`
- `https://www.tiktok.com/@user` → `linksniff-tiktok.py`  
- `https://www.instagram.com/username` → `linksniff-instagram.py`
- `https://missav.ws/video123` → `linksniff-missav.py`
- `https://leakedzone.com/user/profile` → `linksniff-leakedzone.py`

The naming convention is: `linksniff-{domain}.py` where `{domain}` is the second-level domain extracted from the URL.

## Available Scripts

### YouTube (`linksniff-youtube.py`)
Downloads YouTube videos with full metadata and quality options.

**Features:**
- Creates folder named after the uploader
- Downloads best quality MP4 with audio
- Embeds metadata, thumbnails, and subtitles
- Supports subtitle languages (defaults to English)
- Restricts filenames for cross-platform compatibility

**Usage:**
```bash
python linksniff-youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Dependencies:** `yt-dlp`

**Output Structure:**
```
{uploader_name}/
└── {video_title}.mp4
```

---

### TikTok (`linksniff-tiktok.py`)
Bulk downloads from TikTok profiles using JavaScript injection.

**Features:**
- Downloads entire user profiles
- Uses browser automation with Playwright
- Injects JavaScript scraper for link extraction
- Automatically runs yt-dlp on collected links
- Creates username-based folder structure

**Usage:**
```bash
python linksniff-tiktok.py "https://www.tiktok.com/@username"
```

**Dependencies:** 
- `playwright` (with Firefox browser)
- `yt-dlp`

**Output Structure:**
```
{username}/
├── TikTokLinks.txt  # List of video URLs
└── *.mp4           # Downloaded videos
```

**Note:** Uses the JavaScript scraper from [dinoosauro/tiktok-to-ytdlp](https://github.com/dinoosauro/tiktok-to-ytdlp) (MIT License).

---

### Instagram (`linksniff-instagram.py`) 
Downloads Instagram profiles via sssinstagram.com proxy service.

**Features:**
- Downloads posts, stories, and reels
- Extracts profile information and avatar
- Organizes content by type
- Supports both headless and visible browser modes
- Creates comprehensive folder structure

**Usage:**
```bash
python linksniff-instagram.py "https://www.instagram.com/username"
python linksniff-instagram.py "https://www.instagram.com/username" -uh  # visible browser
```

**Arguments:**
- `-uh, --unheadless`: Run browser in visible mode for debugging

**Dependencies:**
- `playwright` (Chromium browser)
- `requests`

**Output Structure:**
```
{username}/
├── profile_info.txt     # Profile metadata
├── avatar_{username}.jpg
├── posts/              # Profile posts
├── stories/            # Story highlights  
└── reels/              # Reels content
```

---

### MissAV (`linksniff-missav.py`)
Downloads streaming videos from MissAV pages by extracting m3u8 links.

**Features:**
- Extracts m3u8 streaming URLs from video pages
- Uses page URL for filename generation
- Automatically runs yt-dlp for download
- Handles JavaScript-loaded content

**Usage:**
```bash
python linksniff-missav.py "https://missav.ws/video_page_url"
```

**Dependencies:**
- `playwright` (Chromium browser)  
- `yt-dlp`

**Output:** Files saved with basename from URL path

---

### LeakedZone (`linksniff-leakedzone.py`) 
**Complex unified scraper for LeakedZone content with special requirements.**

** IMPORTANT: This script currently requires running inside the Docker container due to audio codec dependencies and browser compatibility issues.**
And don't ask me why. If you mute the volume videos don't download. Whatever.

**Features:**
- Downloads photos and videos from LeakedZone profiles
- Async operation with concurrent downloads
- Supports filtering by content type
- Handles infinite scroll content loading
- Captures m3u8 video streams
- Debug mode with visible browser

**Usage:**
```bash
# Standard usage (photos and videos)
python linksniff-leakedzone.py "https://leakedzone.com/username"

# Photos only
python linksniff-leakedzone.py "https://leakedzone.com/username" --photos-only

# Videos only  
python linksniff-leakedzone.py "https://leakedzone.com/username" --videos-only

# Debug mode (visible browser)
python linksniff-leakedzone.py "https://leakedzone.com/username" -dh
```

**Arguments:**
- `-dh, --debug-headless`: Enable debug mode with visible browser
- `--photos-only`: Only download photos, skip videos
- `--videos-only`: Only download videos, skip photos

**Dependencies:**
- `playwright` (Firefox browser)
- `aiohttp` for async HTTP requests
- `yt-dlp` for video downloads

**Output Structure:**
```
{username}/
├── photos/
│   └── {photo_id}.{ext}
└── videos/  
    └── video{0001}.mp4
```

**Known Issues:**
- Must be run inside Docker container
- Has audio codec compatibility requirements
- May require specific browser environment

---

## Creating New Scripts

### Basic Requirements

1. **Naming Convention**: `linksniff-{sitename}.py`
2. **Command Line Interface**: Accept URL as first argument
3. **Working Directory**: Save files to current working directory  
4. **Exit Codes**: Return 0 for success, non-zero for failure
5. **Error Handling**: Handle failures gracefully

### Basic Template

```python
#!/usr/bin/env python3
import sys
import os

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        # Your downloading logic here
        # Save files to current working directory
        print(f"Successfully downloaded from {url}")
        
    except Exception as e:
        print(f"Download failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Available Tools in Docker Environment

The LinkSniff Docker container includes:
- `requests` - HTTP requests
- `playwright` - Browser automation (Chromium, Firefox, WebKit)
- `yt-dlp` - Media downloading
- `beautifulsoup4` - HTML parsing
- `aiohttp` - Async HTTP requests
- `curl` - Command line HTTP tool
- Standard Python libraries

### Best Practices

1. **Create organized folder structures** - Don't dump everything in one directory
2. **Use meaningful filenames** - Include IDs, timestamps, or sequential numbers
3. **Handle rate limiting** - Add delays between requests
4. **Provide progress feedback** - Print status messages
5. **Test independently** - Ensure script works outside the web UI
6. **Handle edge cases** - Empty results, network errors, invalid URLs

### Hot-Swappable Development

Scripts are **hot-swappable** - you can add new scripts to this folder without restarting the Docker container. Just drop in your `linksniff-newsite.py` file and start using it immediately through the web UI.

## Testing Scripts

### Manual Testing
```bash
# Enter the container
docker exec -it linksniff bash

# Navigate to media directory  
cd /media

# Test your script
python /app/scripts/linksniff-yoursite.py "https://example.com/test_url"
```

### Common Issues

**"No script for site 'whatever'"**
- Create `linksniff-whatever.py` in the scripts directory
- The domain extraction uses the second-level domain from the URL

**Downloads failing**
- Check that required dependencies are installed in Docker
- Test the script manually in the container
- Verify the site hasn't changed their structure

**File permission issues**
- Ensure the script has execute permissions
- Check that the media directory is writable

## Contributing

When adding new scripts:
1. Follow the naming convention
2. Test thoroughly with various URLs
3. Document any special requirements
4. Include error handling and user feedback
5. Consider organizing output into logical folder structures

For scripts with special requirements (like leakedzone), clearly document the limitations and setup needs.
