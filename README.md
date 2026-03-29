# Ultimate Video Downloader v5.1 ULTRA

**The most powerful FREE video downloader for Windows**

A feature-rich, modern video downloader built with Python and CustomTkinter. Download videos from YouTube, Instagram, TikTok, Facebook, Twitter, and 1000+ other platforms with advanced features like auto clipboard detection, scheduled downloads, batch processing, and more.

![Version](https://img.shields.io/badge/version-5.1%20ULTRA-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

---

## ✨ Features

### Core Features
- ✅ **Auto Clipboard Detection** - Automatically detects video URLs when copied to clipboard
- ✅ **Scheduled Downloads** - Schedule downloads for later (30 min, 1 hour, 2 hours, custom time)
- ✅ **Batch Download** - Download multiple videos at once (one URL per line)
- ✅ **Pause/Resume** - Full control over active downloads
- ✅ **Concurrent Downloads** - Download up to 5 videos simultaneously
- ✅ **Auto-Retry** - Automatically retries failed downloads up to 3 times
- ✅ **Single Instance Lock** - Prevents multiple app instances

### Quality & Format Options
- ✅ **4K Quality (2160p)** - Ultra HD downloads
- ✅ **1080p / 720p / 480p / 360p** - Multiple quality options
- ✅ **Best Quality** - Automatically selects highest available quality
- ✅ **Audio Only (MP3)** - Extract audio in MP3 format
- ✅ **Subtitle Download** - Download subtitles with videos
- ✅ **Full Playlist Support** - Download entire playlists

### Advanced Features
- ✅ **Thumbnail Downloader** - Download full-resolution video thumbnails separately
- ✅ **Download History** - Track all your downloads with metadata
- ✅ **Speed Limiter** - Limit download speed (1-10 MB/s)
- ✅ **Video Preview** - See video info, thumbnail, and metadata before downloading
- ✅ **Cookie Support** - Use cookies.txt for HD quality and private videos
- ✅ **Dark/Light/System Theme** - Choose your preferred appearance

### User Interface
- 🎨 Modern, clean CustomTkinter interface
- 📊 Real-time progress tracking with speed and ETA
- 📋 Comprehensive download queue management
- 📝 Detailed download logs
- 🔔 Toast notifications for clipboard detection

---

## 🌐 Supported Sites

This application uses **yt-dlp** and supports **1000+ websites** including:

- **YouTube** - Videos, playlists, live streams
- **Instagram** - Posts, reels, stories
- **TikTok** - Videos and profiles
- **Facebook** - Videos and watch content
- **Twitter/X** - Video tweets
- **Vimeo** - All video content
- **Dailymotion** - Videos and playlists
- **Twitch** - VODs and clips
- **Reddit** - Video posts
- **SoundCloud** - Audio tracks
- **Bilibili** - Chinese video platform
- **And 1000+ more sites!**

For a complete list, visit: [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 📥 Installation

### Option 1: Download Executable (Recommended)
1. Download the latest `.exe` file from the [Releases](../../releases) page
2. Run the executable - no installation required!
3. Start downloading videos immediately

### Option 2: Run from Source

#### Requirements
- **Python 3.10+** (Python 3.11 or 3.12 recommended)
- **FFmpeg** (required for video merging and audio extraction)
- **Windows 10/11**

#### Install FFmpeg
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract and add to system PATH
3. Verify installation: `ffmpeg -version`

#### Install Python Dependencies
```bash
pip install customtkinter yt-dlp pillow
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

#### Run the Application
```bash
python main.py
```

---

## 🚀 Usage

### Basic Download
1. Launch the application
2. Paste a video URL (or copy it - auto-detection will fill it automatically!)
3. Select desired quality
4. Click **"⬇ DOWNLOAD NOW"**
5. Videos are saved to: `C:\Users\YourName\Downloads\VideoDownloader\`

### Batch Download
1. Go to the **Download** tab
2. Paste multiple URLs in the **BATCH** text area (one per line)
3. Click **"📦 ADD BATCH TO QUEUE"**
4. All videos will be queued and downloaded

### Schedule Downloads
1. Paste a video URL
2. Click **"⏰ SCHEDULE DOWNLOAD"**
3. Choose a time (30 min, 1 hour, 2 hours, or Tonight 11PM)
4. The download will start automatically at the scheduled time

### Download Thumbnails Only
1. Go to the **🖼 Thumbnails** tab
2. Paste a video URL
3. Click **"🖼 Get Thumbnail"**
4. Preview the thumbnail
5. Click **"💾 Save Thumbnail to Downloads"**

### Using Cookies for HD Quality
1. Install the Chrome extension: **"Get cookies.txt LOCALLY"**
2. Visit YouTube and export cookies.txt
3. Save it to: `C:\Users\YourName\cookies.txt`
4. Go to **⚙ Settings** tab
5. Verify the cookie path
6. You'll see **"✔ HD Quality Enabled!"**

---

## ⚙️ Settings

### Clipboard Auto-Detect
- Toggle automatic URL detection from clipboard
- When enabled, copying a video URL auto-fills the download field

### Speed Limiter
- Limit download speed from 1-10 MB/s
- Set to 0 for unlimited speed

### Concurrent Downloads
- Download 1-5 videos simultaneously
- Higher values use more bandwidth and system resources

### Theme
- **Dark Mode** - Default dark theme
- **Light Mode** - Light theme
- **System** - Follow system theme

---

## 🐛 Bug Reports & Issues

Found a bug or have a feature request? Please report it on our [GitHub Issues](../../issues) page.

When reporting bugs, please include:
- Windows version
- Python version (if running from source)
- Steps to reproduce
- Error messages or screenshots
- Video URL (if applicable)

---

## 📋 Requirements

### For Executable Version
- Windows 10 or Windows 11
- FFmpeg (auto-included in some builds)

### For Source Version
- Python 3.10 or higher
- customtkinter >= 5.2.0
- yt-dlp >= 2024.1.0
- Pillow >= 10.0.0
- FFmpeg (system installation)

---

## 🔧 Building from Source

### Create Executable with PyInstaller
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

The executable will be in the `dist/` folder.

---

## 📜 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Ultimate Video Downloader

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Credits

Built with:
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern UI framework
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Video download engine
- **[Pillow](https://python-pillow.org/)** - Image processing
- **[FFmpeg](https://ffmpeg.org/)** - Video/audio processing

---

## ⚠️ Disclaimer

This tool is for **personal use only**. Please respect copyright laws and the terms of service of the websites you download from. The developers are not responsible for any misuse of this application.

Always ensure you have the right to download content before doing so.

---

## 💖 Support

If you find this project useful, please consider:
- ⭐ Starring this repository
- 🐛 Reporting bugs
- 💡 Suggesting new features
- 📢 Sharing with others

---

**Made with ❤️ by the Ultimate Video Downloader Team**

**Version 5.1 ULTRA - FREE Forever**
