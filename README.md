# LinkSniff 🕷️

**A modular web-based media downloader.** Because I'd rather spend 24 hours poking python with a stick to download some galleries than just download them manually.

LinkSniff is a containerized Flask frontend webui that queues and manages downloads using website-specific Python scripts. Add support for any website by creating a script that follows the naming convention.

## Features

- **Web UI**: Clean, dark-mode-enabled interface with real-time status updates
- **Queue Management**: Add multiple URLs at once (one per line)
- **Concurrent Downloads**: Configurable concurrency with smart per-site limiting
- **Modular Design**: Add new platforms by creating a single Python script
- **Docker**: Containerized for easy deployment and isolation
- **Persistence**: Your downloads and queue survive container restarts
- **Built-in Updates**: Update yt-dlp directly from the web interface

## Warning!
- **!NOT MEANT FOR PUBLIC FACING WEBSITES!**: If you openly expose this to the internet from your network that is 100% not my problem. Don't do it. It is not made with that in mind.

## Table of Contents
- [Quick Start](#quick-start)
- [How It Works - The Modular Magic](#how-it-works---the-modular-magic)
- [Included Example Scripts](#included-example-scripts)
- [Adding New Platforms](#adding-new-platforms)
  - [Requirements for Your Script](#requirements-for-your-script)
  - [Basic Template](#basic-template)
  - [What Tools Can You Use?](#what-tools-can-you-use)
  - [Hot-Swappable Scripts](#hot-swappable-scripts)
- [Configuration](#configuration)
  - [Directory Structure](#directory-structure)
  - [Concurrency Settings](#concurrency-settings)
- [Usage](#usage)
  - [Adding URLs](#adding-urls)
  - [Queue Management](#queue-management)
  - [Control Buttons](#control-buttons)
  - [Settings Menu (☰)](#settings-menu-☰)
- [Docker Configuration](#docker-configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Basic understanding of Python scripting

### Installation

1. **Clone this repository**:
   ```bash
   git clone <your-repo-url>
   cd linksniff
   ```

2. **Create the required directories**:
   ```bash
   mkdir -p config scripts media
   ```

3. **Start the container**:
   ```bash
   docker-compose up -d
   ```

4. **Visit** `http://localhost:9559` and start adding URLs to download.

If you need to change anything for folder locations or port and do not know how, here is a link: https://docs.docker.com/get-started/

## How It Works - The Modular Magic

LinkSniff automatically detects which script to use based on the domain in your URL. The naming convention is simple: `linksniff-{domain}.py` where `{domain}` is extracted from the URL.

For example:
- `https://youtube.com/watch?v=xyz` → uses `linksniff-youtube.py`
- `https://tiktok.com/@user` → uses `linksniff-tiktok.py`
- `https://missav.ws/video123` → uses `linksniff-missav.py`

All it looks for is the domain name and will dump files it downloads into a folder named that TL domain name. Again, I cannot stress this enough. Only run this on your personal private internal network.

## Included Example Scripts

### YouTube (`linksniff-youtube.py`)
Downloads videos with metadata, thumbnails, and subtitles. Creates a folder named after the uploader and saves the video there.

### TikTok (`linksniff-tiktok.py`)
Bulk profile downloads using JavaScript injection to scrape video links, then passes them to yt-dlp for actual downloading. Uses the JavaScript scraper from [dinoosauro/tiktok-to-ytdlp](https://github.com/dinoosauro/tiktok-to-ytdlp) (MIT License).

### MissAV (`linksniff-missav.py`)
Finds m3u8 streams on video pages and downloads them using yt-dlp with the page's filename.

## Adding New Platforms

Want to add support for Instagram? Reddit? That obscure video site only you use? Just create a script.

### Requirements for Your Script

1. **Name it properly**: `linksniff-{sitename}.py` in the `scripts/` directory
2. **Accept a URL**: Take the URL as the first command-line argument
3. **Download to current directory**: Save files to wherever the script is running
4. **Exit codes matter**: Return 0 for success, anything else for failure

Example: As long as you can independently run:

:$ python linksniff-example.py http://www.example.site/username/

from the command line, and it downloads stuff, you can drop that python script into ./scripts and start pasting urls into the webui.

### Basic Template

```python
#!/usr/bin/env python3
import sys
import subprocess

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Your downloading logic here
    # Use requests, playwright, yt-dlp, or whatever works
    # Save files to current working directory
    
    print(f"Successfully downloaded from {url}")

if __name__ == "__main__":
    main()
```

### What Tools Can You Use?

The Docker container includes common libraries like:
- `requests` for HTTP requests
- `playwright` for browser automation
- `yt-dlp` for media downloading
- `beautifulsoup4` (bs4) for HTML parsing
- `curl` because sure, why not.
- Standard Python libraries

Need something else? Modify the Dockerfile to include it.

### Hot-Swappable Scripts

**You don't need to restart the Docker container when adding new scripts.** Just drop your `linksniff-newsite.py` file into the `scripts/` directory and immediately start pasting URLs into the web UI.

## Configuration

### Directory Structure

```
linksniff/
├── config/              # App database and settings
├── scripts/             # Your platform scripts
├── media/               # Downloaded media files
└── docker-compose.yml
```

### Concurrency Settings

Configure the maximum concurrent downloads via the settings menu (☰) in the web UI. The app enforces **one active download per platform** to avoid overwhelming sites and getting rate-limited.

## Usage

### Adding URLs

1. Paste URLs in the text area (one per line)
2. Click "Add to Queue"
3. Watch downloads progress in real-time

### Queue Management

- **Pending**: Waiting for an available download slot
- **Active**: Currently downloading (shows live progress)
- **Completed**: Successfully downloaded
- **Failed**: Something went wrong (click to retry)

### Control Buttons

- **Refresh Status**: Updates the queue (auto-refreshes every 5 seconds)
- **Clear Completed**: Removes successful downloads from the queue
- **Clear All**: Removes all tasks from the queue

### Settings Menu (☰)
- **Dark/Light toggle**
- **Change Concurrency Settings**
- **Verify yt-dlp is updated and update if needed**: I specifically added this because let's face it, the webui just will do whatever. Things like yt-dlp update a lot and I am not going to update this whole thing just for a new yt-dlp release.

## Docker Configuration

The `docker-compose.yml` mounts three volumes:

```yaml
volumes:
  - ./config:/app/data      # App database and settings
  - ./scripts:/app/scripts  # Your platform scripts
  - ./media:/media          # Downloaded files
```

Adjust these paths as needed for your setup.

## Troubleshooting

### "No script for site 'whatever'"
Create a `linksniff-whatever.py` script in your `scripts/` directory. The app extracts the site name from the URL domain.

### Downloads failing
Failed tasks can be clicked to retry. Check that your script works by testing it manually:
```bash
docker exec -it linksniff bash
cd /media
python /app/scripts/linksniff-yoursite.py "https://example.com/video"
```
(logs -f does not work because app.py isn't faulting, the python linksniff script is faulting. I may address this in the future if it's more than me troubleshooting it.)

### UI not loading
Make sure port 9559 isn't already in use, or change it in the docker-compose.yml file.

## Development

### File Structure

```
linksniff/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Web UI template
├── static/
│   ├── style.css       # Styling with dark mode
│   └── script.js       # Frontend JavaScript
├── scripts/
│   └── linksniff-*.py  # Platform-specific scripts
├── docker-compose.yml  # Container configuration
└── README.md          # Documentation
```

If you really want to run it bare metal just follow the Dockerfile instructions by hand.

The app runs on `http://localhost:9559` by default.

## Contributing

Found a bug? Want to add support for another platform? 

1. Fork the repository
2. Create your script following the naming convention
3. Test it thoroughly
4. Submit a pull request

**Fair warning**: I'm not the most consistent maintainer. I tend to build things, then move on to the next shiny project. I also work 60 hours a week not doing this. But that's what makes community contributions even more valuable - you're not dependent on me to keep things moving.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*Built for people who appreciate modular design and clean interfaces.*
