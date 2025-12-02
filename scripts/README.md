# LinkSniff Scripts Documentation

This folder contains platform-specific download scripts that can be used either through the LinkSniff web UI or independently from the command line.

## How Script Selection Works

LinkSniff automatically chooses which script to run based on the URL domain:
- `https://www.example1.com/content` → `linksniff-example1.py`
- `https://www.example2.com/user` → `linksniff-example2.py`  
- `https://www.example3.com/profile` → `linksniff-example3.py`

The naming convention is: `linksniff-{domain}.py` where `{domain}` is the second-level domain extracted from the URL.

## Script Template Examples

### Video Platform Script Template
Downloads videos with metadata and quality options.

**Common Features:**
- Creates organized folder structures
- Downloads best available quality
- Embeds metadata and thumbnails
- Supports subtitle extraction
- Cross-platform compatible filenames

**Usage:**
```bash
python linksniff-videosite.py "https://www.videosite.com/content/VIDEO_ID"
```

**Typical Dependencies:** `yt-dlp`, `requests`

**Output Structure:**
```
{content_creator}/
└── {content_title}.mp4
```

---

### Profile/Bulk Download Script Template
Bulk downloads from user profiles using browser automation.

**Common Features:**
- Downloads entire user profiles or collections
- Uses browser automation for JavaScript-heavy sites
- Extracts links via page scraping
- Processes collected URLs with download tools
- Creates organized folder structures

**Usage:**
```bash
python linksniff-socialsite.py "https://www.socialsite.com/@username"
```

**Typical Dependencies:** 
- `playwright` (with browser engines)
- `yt-dlp` or other download tools
- `beautifulsoup4` for parsing

**Output Structure:**
```
{username}/
├── links.txt           # List of content URLs
└── content/            # Downloaded files
```

---

### Proxy-Based Downloader Template
Downloads content via proxy services or alternative access methods.

**Common Features:**
- Uses third-party services or proxies
- Extracts profile information
- Organizes content by type
- Supports both headless and visible browser modes
- Creates comprehensive folder structure

**Usage:**
```bash
python linksniff-site.py "https://www.site.com/username"
python linksniff-site.py "https://www.site.com/username" -uh  # visible browser
```

**Arguments:**
- `-uh, --unheadless`: Run browser in visible mode for debugging

**Typical Dependencies:**
- `playwright` (browser automation)
- `requests`
- `beautifulsoup4`

**Output Structure:**
```
{username}/
├── profile_info.txt    # Profile metadata
├── avatar.jpg
├── content_type_1/     # Organized by content type
├── content_type_2/     
└── content_type_3/
```

---

### Stream Extractor Template
Downloads streaming content by extracting media URLs.

**Common Features:**
- Extracts m3u8 or other streaming URLs
- Uses page URL for filename generation
- Processes streams with appropriate tools
- Handles JavaScript-loaded content

**Usage:**
```bash
python linksniff-streamsite.py "https://streamsite.com/content_page_url"
```

**Typical Dependencies:**
- `playwright` (browser automation)
- `yt-dlp` or `ffmpeg`
- `requests`

**Output:** Files saved with descriptive names based on content

---

### Advanced Multi-Content Scraper Template
**Complex unified scraper with special requirements.**

**⚠️ IMPORTANT: Some advanced scripts may require running inside the Docker container due to codec dependencies, browser compatibility, or other environmental requirements.**

**Common Features:**
- Downloads multiple content types (photos, videos, etc.)
- Async operation with concurrent downloads
- Supports content filtering
- Handles infinite scroll or pagination
- Captures various media formats
- Debug mode with visible browser

**Usage:**
```bash
# Standard usage (all content types)
python linksniff-advancedsite.py "https://site.com/username"

# Filter by content type
python linksniff-advancedsite.py "https://site.com/username" --photos-only
python linksniff-advancedsite.py "https://site.com/username" --videos-only

# Debug mode (visible browser)
python linksniff-advancedsite.py "https://site.com/username" -dh
```

**Typical Arguments:**
- `-dh, --debug-headless`: Enable debug mode with visible browser
- `--photos-only`: Only download photos, skip other content
- `--videos-only`: Only download videos, skip other content
- `--filter [type]`: Download specific content types

**Typical Dependencies:**
- `playwright` (with specific browser)
- `aiohttp` for async HTTP requests
- `yt-dlp` or other download tools
- `asyncio` for concurrent operations

**Output Structure:**
```
{username}/
├── photos/
│   └── {photo_id}.{ext}
├── videos/  
│   └── video{0001}.mp4
└── other_content/
    └── files...
```

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
7. **Document special requirements** - Note any container-specific dependencies

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

**Browser automation issues**
- Verify correct browser engine is installed in container
- Check for JavaScript errors in debug mode
- Ensure sufficient container resources

## Contributing

When adding new scripts:
1. Follow the naming convention
2. Test thoroughly with various URLs
3. Document any special requirements
4. Include error handling and user feedback
5. Consider organizing output into logical folder structures
6. Note any container-specific dependencies or limitations

For scripts with special requirements (codec dependencies, specific browsers, etc.), clearly document the limitations and setup needs.
