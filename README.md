<div align="center">

# ⬇️ Ultimate Video Downloader

### The most powerful **FREE** video downloader for Windows

[![Version](https://img.shields.io/badge/Version-5.1%20ULTRA-4f8ef7?style=for-the-badge&logo=github)](https://github.com/TayyabAliDogar/ultimate-video-downloader/releases)
[![Free](https://img.shields.io/badge/Price-FREE%20Forever-00d68f?style=for-the-badge)](https://github.com/TayyabAliDogar/ultimate-video-downloader/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?style=for-the-badge&logo=windows)](https://github.com/TayyabAliDogar/ultimate-video-downloader/releases)
[![License](https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge)](LICENSE)

<br>

**Download videos from YouTube, Instagram, TikTok, Facebook, Twitter & 1000+ sites**
**in stunning HD/4K quality — completely FREE, no subscriptions, no limits!**

<br>

## 📥 Download Now — No Installation Required!

### [⬇️ Click Here to Download UltimateVideoDownloader.exe](https://drive.google.com/file/d/1yVfNl1FA-Cst6oLupWL0ifmR6BdYYoz3/view?usp=drive_link)

> ✅ Everything bundled — Python · FFmpeg · All libraries
> ✅ Just download & double-click — works on any Windows PC!

</div>

---

## ⚠️ First Time Setup — Windows Security Warning

When you run the app for the first time, Windows may show:

> *"Windows protected your PC — Unknown publisher"*

**This is completely normal** for new open-source apps without a paid certificate.
The app is **100% safe** — source code is publicly available for anyone to verify.

### Fix in 2 simple steps:
```
1. Click "More info"
2. Click "Run anyway"
```
> 💡 This warning only appears **once** — never again after that!

---

## ✨ Features

<table>
<tr>
<td>

### 🚀 Smart Downloads
- 📋 **Auto Clipboard Detection** — Copy any URL, app auto-fills it
- ⏰ **Scheduled Downloads** — Set downloads for later
- 📦 **Batch Download** — Multiple URLs at once
- ⏸️ **Pause / Resume** — Full download control
- 🔀 **Concurrent Downloads** — Up to 5 at once
- 🔄 **Auto-Retry** — 3 automatic retries on failure

</td>
<td>

### 🎬 Quality Options
- 🔵 **4K (2160p)** — Ultra HD
- 🟢 **1080p Full HD** — Crystal clear
- 🟡 **720p / 480p / 360p** — Flexible options
- 🎵 **Audio Only (MP3)** — Music extraction
- 📝 **Subtitles** — Auto-download captions
- 📋 **Full Playlist** — Entire playlist at once

</td>
</tr>
<tr>
<td>

### 🎨 Professional UI
- 🌑 **Dark / Light / System Theme**
- 📊 **Real-time Speed & ETA**
- 🖼️ **Video Preview** — Thumbnail before download
- 📝 **Download Log** — Detailed activity log
- 🔔 **Toast Notifications** — URL detection alerts

</td>
<td>

### ⚙️ Advanced Tools
- 🖼️ **Thumbnail Downloader** — Save thumbnails separately
- 🕘 **Download History** — Track all downloads
- ⚡ **Speed Limiter** — Control bandwidth usage
- 🍪 **Cookie Support** — HD quality & private videos
- 🐛 **Bug Report Button** — One-click bug reporting
- ⭐ **GitHub Integration** — Star & contribute easily

</td>
</tr>
</table>

---

## 🚀 How to Use

### Basic Download
```
1. Open the app
2. Paste video URL  (or just copy it — auto-detection works!)
3. Select quality   (1080p recommended)
4. Click ⬇ DOWNLOAD NOW
5. Done! Saved to: ~/Downloads/VideoDownloader/
```

### Batch Download
```
1. Paste multiple URLs in the BATCH box (one per line)
2. Click 📦 ADD BATCH TO QUEUE
3. All videos download automatically!
```

### Schedule a Download
```
1. Paste URL
2. Click ⏰ SCHEDULE DOWNLOAD
3. Choose time: 30 min / 1 hour / 2 hours / Tonight
4. App downloads automatically at that time!
```

### Download Thumbnails Only
```
1. Go to 🖼 Thumbnails tab
2. Paste video URL
3. Click Get Thumbnail → Preview → Save!
```

---

## 🌐 Supported Sites

| Platform | Type |
|----------|------|
| **YouTube** | Videos, Playlists, Live Streams, Shorts |
| **Instagram** | Reels, Posts, Stories |
| **TikTok** | Videos, Profiles |
| **Facebook** | Videos, Watch |
| **Twitter / X** | Video Tweets |
| **Vimeo** | All Videos |
| **Dailymotion** | Videos & Playlists |
| **Twitch** | VODs & Clips |
| **Reddit** | Video Posts |
| **SoundCloud** | Audio Tracks |
| **Bilibili** | Chinese Videos |
| **1000+ more** | [See full list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) |

---

## 🍪 Enable HD Quality (Optional but Recommended)

For best YouTube quality, add cookies:

```
1. Install Chrome extension: "Get cookies.txt LOCALLY"
2. Go to YouTube → Login to your account
3. Click extension → Export cookies.txt
4. Save to: C:\Users\YourName\cookies.txt
5. App → Settings → Verify cookie path
6. You'll see: "✔ HD Quality Enabled!"
```

---

## 🐛 Bug Report / Feature Request

Found a bug? Have a suggestion?

👉 **[Open an Issue on GitHub](https://github.com/TayyabAliDogar/ultimate-video-downloader/issues/new)**

Please include:
- Windows version
- Steps to reproduce
- Error message / screenshot
- Video URL (if applicable)

---

## 🛠️ Run from Source Code

```bash
# Clone repository
git clone https://github.com/TayyabAliDogar/ultimate-video-downloader.git
cd ultimate-video-downloader

# Install dependencies
pip install customtkinter yt-dlp pillow

# Run
python main.py
```

**Requirements:**
- Python 3.10+
- FFmpeg (place in `bin/` folder)
- Windows 10 / 11

---

## 📦 Build EXE from Source

```bash
pip install pyinstaller

pyinstaller --noconfirm --onefile --windowed \
  --add-data "bin;bin" \
  --collect-all customtkinter \
  --copy-metadata customtkinter \
  --hidden-import PIL \
  --collect-all PIL \
  --name "UltimateVideoDownloader" \
  main.py
```

---

## 📋 Requirements

| Component | Version |
|-----------|---------|
| Windows | 10 / 11 |
| Python | 3.10+ |
| customtkinter | ≥ 5.2.0 |
| yt-dlp | ≥ 2024.1.0 |
| Pillow | ≥ 10.0.0 |
| FFmpeg | Bundled ✅ |

---

## 📄 License

```
MIT License — Free to use, modify and distribute.
Copyright (c) 2026 Ultimate Video Downloader
```

---

## ⚠️ Disclaimer

This tool is for **personal use only**.
Please respect copyright laws and platform terms of service.
The developers are not responsible for any misuse.

---

<div align="center">

## 💖 Support This Project

If you find this useful, please:

⭐ **[Star on GitHub](https://github.com/TayyabAliDogar/ultimate-video-downloader)** — helps others discover it!

🐛 **[Report Bugs](https://github.com/TayyabAliDogar/ultimate-video-downloader/issues)** — help make it better!

📢 **Share with friends** — spread the word!

<br>

**Made with ❤️ — v5.1 ULTRA — FREE Forever**

*Built with Python · CustomTkinter · yt-dlp · FFmpeg*

</div>