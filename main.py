import sys
import os
import socket
import threading
import subprocess
import time
import json
import urllib.request
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta

# ── Single Instance Lock ───────────────────────────────────────────────────────
def is_already_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 47832))
        s.listen(1)
        return False, s
    except OSError:
        return True, None

already_running, _lock = is_already_running()
if already_running:
    sys.exit(0)

# ── Tcl/Tk Fix ────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    for k, f in [('TCL_LIBRARY','tcl'),('TK_LIBRARY','tk')]:
        p = os.path.join(base, f)
        if os.path.exists(p):
            os.environ[k] = p

# ── FFmpeg Path Fix ───────────────────────────────────────────────────────────
def get_ffmpeg_path():
    """Get FFmpeg path - works both in development and in bundled EXE"""
    if getattr(sys, 'frozen', False):
        # Running as EXE - FFmpeg is bundled inside
        base_path = sys._MEIPASS
    else:
        # Running as Python script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    ffmpeg_exe = os.path.join(base_path, 'bin', 'ffmpeg.exe')
    
    # If bundled ffmpeg not found, try system ffmpeg
    if not os.path.exists(ffmpeg_exe):
        return None
    
    return os.path.join(base_path, 'bin')

FFMPEG_LOCATION = get_ffmpeg_path()

import customtkinter as ctk
from PIL import Image, ImageDraw
import io
import yt_dlp

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME          = Path.home()
COOKIES_PATH  = str(HOME / "cookies.txt")
HISTORY_FILE  = str(HOME / "Downloads" / "VideoDownloader" / ".history.json")
SETTINGS_FILE = str(HOME / "Downloads" / "VideoDownloader" / ".settings.json")
SCHEDULE_FILE = str(HOME / "Downloads" / "VideoDownloader" / ".schedule.json")
DOWNLOAD_PATH = str(HOME / "Downloads" / "VideoDownloader")
MAX_RETRIES   = 3

GITHUB_URL    = "https://github.com/TayyabAliDogar/ultimate-video-downloader"
GITHUB_ISSUES = "https://github.com/TayyabAliDogar/ultimate-video-downloader/issues/new"

VIDEO_DOMAINS = [
    "youtube.com", "youtu.be", "instagram.com", "tiktok.com",
    "facebook.com", "fb.watch", "twitter.com", "x.com",
    "vimeo.com", "dailymotion.com", "twitch.tv", "reddit.com",
    "soundcloud.com", "bilibili.com", "ok.ru", "rumble.com",
]

def is_video_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    return any(domain in url.lower() for domain in VIDEO_DOMAINS)

# ── Colors ────────────────────────────────────────────────────────────────────
BG        = "#07070f"
CARD      = "#0e0e1c"
CARD2     = "#141428"
CARD3     = "#1c1c35"
ACCENT    = "#4f8ef7"
ACCENT2   = "#00d68f"
PURPLE    = "#a855f7"
PINK      = "#ec4899"
ORANGE    = "#f97316"
DANGER    = "#ff4757"
WARN      = "#ffa502"
TEXT      = "#e8eaf6"
SUBTEXT   = "#8892b0"
DIM       = "#3d3d5c"
BTN_DL    = "#3b5bdb"
BTN_UP    = "#0ca678"
BTN_GRAY  = "#2d2d4e"
BTN_PAUSE = "#d97706"
BTN_RED   = "#dc2626"

STATUS_WAITING     = "⏳ Waiting"
STATUS_SCHEDULED   = "⏰ Scheduled"
STATUS_FETCHING    = "🔍 Fetching"
STATUS_DOWNLOADING = "⬇ Downloading"
STATUS_MERGING     = "⚙ Merging"
STATUS_DONE        = "✅ Complete"
STATUS_FAILED      = "❌ Failed"
STATUS_PAUSED      = "⏸ Paused"
STATUS_CANCELLED   = "🚫 Cancelled"

STATUS_COLORS = {
    STATUS_WAITING:    BTN_GRAY,
    STATUS_SCHEDULED:  ORANGE,
    STATUS_FETCHING:   ACCENT,
    STATUS_DOWNLOADING:BTN_DL,
    STATUS_MERGING:    PURPLE,
    STATUS_DONE:       BTN_UP,
    STATUS_FAILED:     DANGER,
    STATUS_PAUSED:     BTN_PAUSE,
    STATUS_CANCELLED:  BTN_GRAY,
}


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class DownloadItem:
    def __init__(self, url, quality, cookies, dl_path,
                 subtitles=False, playlist=False, speed_limit=0,
                 scheduled_time=None):
        self.url            = url
        self.quality        = quality
        self.cookies        = cookies
        self.dl_path        = dl_path
        self.subtitles      = subtitles
        self.playlist       = playlist
        self.speed_limit    = speed_limit
        self.scheduled_time = scheduled_time
        self.status         = STATUS_SCHEDULED if scheduled_time else STATUS_WAITING
        self.progress       = 0.0
        self.speed          = ""
        self.eta            = ""
        self.size           = ""
        self.title          = url[:55] + "…" if len(url) > 55 else url
        self.paused         = False
        self.cancelled      = False
        self._pause_ev      = threading.Event()
        self._pause_ev.set()

    def pause(self):
        self.paused = True
        self._pause_ev.clear()
        self.status = STATUS_PAUSED

    def resume(self):
        self.paused = False
        self._pause_ev.set()
        self.status = STATUS_DOWNLOADING

    def cancel(self):
        self.cancelled = True
        self._pause_ev.set()
        self.status = STATUS_CANCELLED


class SilentLogger:
    def debug(self, m): pass
    def info(self, m):  pass
    def warning(self, m): pass
    def error(self, m): pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ultimate Video Downloader")
        self.geometry("1080x820")
        self.minsize(920, 680)
        self.configure(fg_color=BG)

        self.settings       = load_json(SETTINGS_FILE, {
            'cookies':        COOKIES_PATH,
            'download_path':  DOWNLOAD_PATH,
            'theme':          'dark',
            'speed_limit':    0,
            'max_concurrent': 3,
            'clipboard_watch': True,
        })
        self.history        = load_json(HISTORY_FILE, [])
        self.schedule_list  = load_json(SCHEDULE_FILE, [])
        self.download_queue = []
        self.queue_lock     = threading.Lock()
        self._item_widgets  = {}
        self._thumb_img     = None
        self._fetch_timer   = None
        self._last_clipboard= ""
        self._clipboard_enabled = self.settings.get('clipboard_watch', True)

        self._build_ui()
        threading.Thread(target=self._auto_update, daemon=True).start()
        threading.Thread(target=self._clipboard_watcher, daemon=True).start()
        threading.Thread(target=self._schedule_watcher, daemon=True).start()
        self._load_stats()
        self._restore_schedule()

    def _clipboard_watcher(self):
        while True:
            try:
                time.sleep(1)
                if not self._clipboard_enabled:
                    continue
                text = self.clipboard_get().strip()
                if text and text != self._last_clipboard and is_video_url(text):
                    self._last_clipboard = text
                    self.after(0, lambda t=text: self._on_clipboard_url(t))
            except Exception:
                time.sleep(2)

    def _on_clipboard_url(self, url):
        self._show_clipboard_toast(url)
        self.url_input.delete(0, "end")
        self.url_input.insert(0, url)
        self._switch_tab("download")
        self._fetch_info()

    def _show_clipboard_toast(self, url):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=CARD)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        toast.geometry(f"340x80+{sw-360}+{sh-120}")
        frame = ctk.CTkFrame(toast, fg_color=CARD2, corner_radius=12)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        ctk.CTkLabel(frame, text="📋  Video URL Detected!",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=ACCENT2).pack(padx=14, pady=(10,2), anchor="w")
        domain = [d for d in VIDEO_DOMAINS if d in url.lower()]
        site = domain[0].replace(".com","").title() if domain else "Unknown"
        ctk.CTkLabel(frame, text=f"From {site} — auto-filled & ready!",
                     font=ctk.CTkFont(size=11), text_color=SUBTEXT).pack(
            padx=14, pady=(0,10), anchor="w")
        toast.after(3000, toast.destroy)

    def _schedule_watcher(self):
        while True:
            try:
                now = datetime.now()
                with self.queue_lock:
                    for item in self.download_queue:
                        if (item.status == STATUS_SCHEDULED
                                and item.scheduled_time
                                and now >= item.scheduled_time):
                            item.status = STATUS_WAITING
                            item.scheduled_time = None
                            self.after(0, lambda it=item: self._update_item(it))
                            threading.Thread(target=self._run_item,
                                           args=(item,), daemon=True).start()
                            self.log(f"⏰ Started: {item.title[:45]}")
            except Exception:
                pass
            time.sleep(30)

    def _restore_schedule(self):
        if not self.schedule_list:
            return
        now = datetime.now()
        for s in self.schedule_list:
            try:
                st = datetime.fromisoformat(s['time'])
                if st > now:
                    item = DownloadItem(
                        url=s['url'], quality=s.get('quality','1080p'),
                        cookies=self.settings.get('cookies', COOKIES_PATH),
                        dl_path=self.settings.get('download_path', DOWNLOAD_PATH),
                        scheduled_time=st)
                    item.title = s.get('title', item.title)
                    with self.queue_lock:
                        self.download_queue.append(item)
            except Exception:
                pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_body()

    def _build_header(self):
         # ── Header height thoda bada kiya taake sab fit ho ──
        hdr = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=80)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
 
        # ── Logo ──
        logo = ctk.CTkFrame(hdr, fg_color=BTN_DL, corner_radius=14, width=46, height=46)
        logo.grid(row=0, column=0, padx=(20, 14), pady=17)
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="⬇", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")
 
        # ── Title + subtitle ──
        tc = ctk.CTkFrame(hdr, fg_color="transparent")
        tc.grid(row=0, column=1, sticky="w", pady=17)
        ctk.CTkLabel(tc, text="Ultimate Video Downloader",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(tc,
                     text="YouTube · Instagram · TikTok · Facebook · Twitter · 1000+ sites",
                     font=ctk.CTkFont(size=10), text_color=DIM).pack(anchor="w")
 
        # ── RIGHT SIDE — fixed layout ──
        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.grid(row=0, column=2, padx=(10, 16), pady=10, sticky="e")
 
        # Row 1: FFmpeg status + stats — ek hi line mein
        row1 = ctk.CTkFrame(right, fg_color="transparent")
        row1.pack(anchor="e", pady=(0, 3))
 
        ffmpeg_ok = FFMPEG_LOCATION is not None
        ffmpeg_text = "⚡ FFmpeg Ready" if ffmpeg_ok else "⚠ FFmpeg Missing"
        ffmpeg_color = ACCENT2 if ffmpeg_ok else DANGER
        ctk.CTkLabel(row1, text=ffmpeg_text,
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=ffmpeg_color).pack(side="left", padx=(0, 12))
 
        self.stats_label = ctk.CTkLabel(row1, text="📥 0 today · 0 total",
                                        font=ctk.CTkFont(size=10),
                                        text_color=SUBTEXT)
        self.stats_label.pack(side="left")
 
        # Row 2: Clipboard toggle + version badges
        row2 = ctk.CTkFrame(right, fg_color="transparent")
        row2.pack(anchor="e", pady=(0, 0))
 
        self.cb_toggle = ctk.CTkSwitch(
            row2, text="📋 Auto-detect",
            font=ctk.CTkFont(size=10),
            text_color=ACCENT2 if self._clipboard_enabled else DIM,
            fg_color=DIM, progress_color=ACCENT2,
            width=46, height=22,
            command=self._toggle_clipboard)
        self.cb_toggle.pack(side="left", padx=(0, 8))
        if self._clipboard_enabled:
            self.cb_toggle.select()
 
        for text, color in [(" v5.1 ", BTN_DL), (" FREE ", ACCENT2)]:
            ctk.CTkLabel(row2, text=text,
                         font=ctk.CTkFont(size=9, weight="bold"),
                         fg_color=color, corner_radius=5,
                         text_color="white").pack(side="left", padx=2)

    def _toggle_clipboard(self):
        self._clipboard_enabled = not self._clipboard_enabled
        self.settings['clipboard_watch'] = self._clipboard_enabled
        save_json(SETTINGS_FILE, self.settings)
        color = ACCENT2 if self._clipboard_enabled else DIM
        self.cb_toggle.configure(text_color=color)
        self.cb_badge.configure(
            text="📋 Clipboard: ON" if self._clipboard_enabled else "📋 Clipboard: OFF",
            text_color=ACCENT2 if self._clipboard_enabled else DIM)
        self.log(f"📋 Clipboard: {'ON' if self._clipboard_enabled else 'OFF'}")

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_content(body)

    def _build_sidebar(self, parent):
        sb = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=0, width=205)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="MENU",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=DIM).pack(padx=20, pady=(20,8), anchor="w")

        self._nav_btns = {}
        nav_items = [
            ("⬇  Download",   "download"),
            ("📋  Queue",      "queue"),
            ("⏰  Schedule",   "schedule"),
            ("🖼  Thumbnails", "thumb"),
            ("🕘  History",    "history"),
            ("⚙  Settings",   "settings"),
        ]
        for label, name in nav_items:
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                height=42, width=165,
                font=ctk.CTkFont(size=13),
                fg_color=CARD3 if name=="download" else "transparent",
                hover_color=CARD3, text_color=TEXT, corner_radius=10,
                command=lambda n=name: self._switch_tab(n))
            btn.pack(padx=16, pady=3)
            self._nav_btns[name] = btn

        ctk.CTkLabel(sb, text="─────────────",
                     font=ctk.CTkFont(size=10), text_color=DIM).pack(
            padx=16, pady=(16,4), anchor="w")

        exists = os.path.exists(self.settings['cookies'])
        self.ck_badge = ctk.CTkLabel(
            sb,
            text="🍪 HD Ready" if exists else "🍪 No Cookies",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=ACCENT2 if exists else WARN)
        self.ck_badge.pack(padx=20, pady=2, anchor="w")

        self.cb_badge = ctk.CTkLabel(
            sb,
            text="📋 Clipboard: ON" if self._clipboard_enabled else "📋 Clipboard: OFF",
            font=ctk.CTkFont(size=10),
            text_color=ACCENT2 if self._clipboard_enabled else DIM)
        self.cb_badge.pack(padx=20, pady=(2,12), anchor="w")

        # Bug Report + GitHub buttons
        ctk.CTkButton(sb, text="🐛  Report a Bug",
                      height=36, width=165,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      fg_color=DANGER, hover_color="#a93226",
                      corner_radius=10,
                      command=lambda: webbrowser.open(GITHUB_ISSUES)
                      ).pack(padx=16, pady=(0,6))

        ctk.CTkButton(sb, text="⭐  Star on GitHub",
                      height=36, width=165,
                      font=ctk.CTkFont(size=12),
                      fg_color=BTN_GRAY, hover_color="#3d3d6e",
                      corner_radius=10,
                      command=lambda: webbrowser.open(GITHUB_URL)
                      ).pack(padx=16, pady=(0,8))

        ctk.CTkLabel(sb, text="© 2026 Ultimate DL",
                     font=ctk.CTkFont(size=9), text_color=DIM).pack(
            side="bottom", padx=16, pady=12)

    def _build_content(self, parent):
        self.content = ctk.CTkFrame(parent, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self._build_download_tab()
        self._build_queue_tab()
        self._build_schedule_tab()
        self._build_thumb_tab()
        self._build_history_tab()
        self._build_settings_tab()
        self._switch_tab("download")

    def _switch_tab(self, tab):
        frames = {
            "download": self.dl_frame,
            "queue":    self.q_frame,
            "schedule": self.sc_frame,
            "thumb":    self.th_frame,
            "history":  self.hist_frame,
            "settings": self.set_frame,
        }
        for name, frame in frames.items():
            frame.grid_remove()
            self._nav_btns[name].configure(
                fg_color=CARD3 if name==tab else "transparent")
        frames[tab].grid()
        if tab == "history":  self._refresh_history()
        if tab == "queue":    self._refresh_queue()
        if tab == "schedule": self._refresh_schedule()

    def _build_download_tab(self):
        self.dl_frame = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent", scrollbar_button_color=DIM)
        self.dl_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        self.dl_frame.grid_columnconfigure(0, weight=1)

        # Clipboard banner
        self.cb_banner = ctk.CTkFrame(
            self.dl_frame, fg_color="#0a2a1a", corner_radius=10, height=0)
        self.cb_banner.grid(row=0, column=0, sticky="ew", pady=(0,6))
        self.cb_banner.grid_propagate(False)
        ctk.CTkLabel(self.cb_banner,
                     text="📋  Clipboard monitoring active — copy any video URL to auto-fill!",
                     font=ctk.CTkFont(size=11), text_color=ACCENT2).place(
            relx=0.5, rely=0.5, anchor="center")
        self._update_cb_banner()

        # URL Card
        uc = ctk.CTkFrame(self.dl_frame, fg_color=CARD, corner_radius=16)
        uc.grid(row=1, column=0, sticky="ew", pady=(0,10))
        uc.grid_columnconfigure(0, weight=1)

        uh = ctk.CTkFrame(uc, fg_color="transparent")
        uh.grid(row=0, column=0, padx=18, pady=(14,6), sticky="ew")
        uh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(uh, text="🔗  VIDEO / PLAYLIST URL",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w")

        btn_row = ctk.CTkFrame(uh, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(btn_row, text="📋 Paste", width=75, height=26,
                      font=ctk.CTkFont(size=11), fg_color=CARD3,
                      hover_color=DIM, corner_radius=8,
                      command=self._paste_url).pack(side="left", padx=(0,4))
        ctk.CTkButton(btn_row, text="🔍 Fetch Info", width=100, height=26,
                      font=ctk.CTkFont(size=11), fg_color=ACCENT,
                      hover_color="#3a7ae0", corner_radius=8,
                      command=self._fetch_info).pack(side="left")

        self.url_input = ctk.CTkEntry(
            uc,
            placeholder_text="Paste YouTube / Instagram / TikTok / Facebook / Twitter URL…",
            height=46, font=ctk.CTkFont(size=14),
            fg_color=CARD2, border_color=DIM, border_width=1, text_color=TEXT)
        self.url_input.grid(row=1, column=0, padx=18, pady=(0,8), sticky="ew")
        self.url_input.bind("<Return>", lambda e: self._fetch_info())
        self.url_input.bind("<KeyRelease>", self._on_url_type)

        bh = ctk.CTkFrame(uc, fg_color="transparent")
        bh.grid(row=2, column=0, padx=18, pady=(4,4), sticky="ew")
        ctk.CTkLabel(bh, text="📦  BATCH  (one URL per line)",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=PURPLE).pack(side="left")

        self.batch_input = ctk.CTkTextbox(
            uc, height=70, font=ctk.CTkFont(size=12),
            fg_color=CARD2, border_color=DIM, border_width=1, text_color=TEXT)
        self.batch_input.grid(row=3, column=0, padx=18, pady=(0,14), sticky="ew")

        # Preview Card
        self.preview_card = ctk.CTkFrame(
            self.dl_frame, fg_color=CARD, corner_radius=16, height=0)
        self.preview_card.grid(row=2, column=0, sticky="ew", pady=(0,10))
        self.preview_card.grid_columnconfigure(1, weight=1)
        self.preview_card.grid_propagate(False)

        self.thumb_lbl = ctk.CTkLabel(self.preview_card, text="", width=0)
        self.thumb_lbl.grid(row=0, column=0)

        pi = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        pi.grid(row=0, column=1, padx=16, pady=14, sticky="nsew")
        pi.grid_columnconfigure(0, weight=1)

        self.prev_title = ctk.CTkLabel(pi, text="",
                                        font=ctk.CTkFont(size=15, weight="bold"),
                                        text_color=TEXT, wraplength=460,
                                        justify="left", anchor="w")
        self.prev_title.grid(row=0, column=0, sticky="ew")
        self.prev_meta = ctk.CTkLabel(pi, text="",
                                       font=ctk.CTkFont(size=12),
                                       text_color=SUBTEXT, anchor="w")
        self.prev_meta.grid(row=1, column=0, sticky="w", pady=(4,0))
        self.prev_plat = ctk.CTkLabel(pi, text="",
                                       font=ctk.CTkFont(size=11, weight="bold"),
                                       text_color="white", anchor="w")
        self.prev_plat.grid(row=2, column=0, sticky="w", pady=(6,0))

        # Options + Download
        opt = ctk.CTkFrame(self.dl_frame, fg_color=CARD, corner_radius=16)
        opt.grid(row=3, column=0, sticky="ew", pady=(0,10))
        opt.grid_columnconfigure(1, weight=1)

        qc = ctk.CTkFrame(opt, fg_color=CARD2, corner_radius=12)
        qc.grid(row=0, column=0, padx=16, pady=16, sticky="ns")
        ctk.CTkLabel(qc, text="QUALITY",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=ACCENT).pack(padx=14, pady=(12,2))
        self.quality_var = ctk.StringVar(value="1080p")
        ctk.CTkOptionMenu(
            qc,
            values=["Best Quality","4K (2160p)","1080p","720p","480p","360p","Audio Only (MP3)"],
            variable=self.quality_var,
            width=165, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=CARD3, button_color=ACCENT,
            dropdown_fg_color=CARD2).pack(padx=14, pady=(0,8))

        ctk.CTkLabel(qc, text="OPTIONS",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=SUBTEXT).pack(padx=14, pady=(4,2))

        self.sub_var   = ctk.BooleanVar(value=False)
        self.plist_var = ctk.BooleanVar(value=False)
        for text, var, color in [
            ("📝 Subtitles",    self.sub_var,   ACCENT),
            ("📋 Full Playlist", self.plist_var, PURPLE),
        ]:
            ctk.CTkCheckBox(qc, text=text, variable=var,
                            font=ctk.CTkFont(size=11), text_color=TEXT,
                            fg_color=color, hover_color=color,
                            corner_radius=5).pack(padx=14, pady=2, anchor="w")
        ctk.CTkLabel(qc, text="", height=8).pack()

        dc = ctk.CTkFrame(opt, fg_color="transparent")
        dc.grid(row=0, column=1, padx=10, pady=16, sticky="ew")
        dc.grid_columnconfigure(0, weight=1)

        self.dl_btn = ctk.CTkButton(
            dc, text="⬇   DOWNLOAD NOW",
            height=60, font=ctk.CTkFont(size=17, weight="bold"),
            fg_color=BTN_DL, hover_color="#2d4abf",
            corner_radius=14, command=self._add_single)
        self.dl_btn.grid(row=0, column=0, sticky="ew", pady=(0,6))

        self.sched_btn = ctk.CTkButton(
            dc, text="⏰  SCHEDULE DOWNLOAD",
            height=38, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ORANGE, hover_color="#b45309",
            corner_radius=10, command=self._open_schedule_dialog)
        self.sched_btn.grid(row=1, column=0, sticky="ew", pady=(0,6))

        self.batch_btn = ctk.CTkButton(
            dc, text="📦  ADD BATCH TO QUEUE",
            height=38, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=PURPLE, hover_color="#8b3dce",
            corner_radius=10, command=self._add_batch)
        self.batch_btn.grid(row=2, column=0, sticky="ew")

        rc = ctk.CTkFrame(opt, fg_color="transparent")
        rc.grid(row=0, column=2, padx=(0,16), pady=16)
        for text, color, hover, cmd in [
            ("↺  Update yt-dlp", BTN_UP,   "#0a8a64", self.update_ytdlp),
            ("📁  Open Folder",  BTN_GRAY, "#3d3d6e", self._open_folder),
        ]:
            ctk.CTkButton(rc, text=text, height=30, width=155,
                          font=ctk.CTkFont(size=12), fg_color=color,
                          hover_color=hover, corner_radius=8,
                          command=cmd).pack(pady=(0,7))

        # Progress
        pc = ctk.CTkFrame(self.dl_frame, fg_color=CARD, corner_radius=16)
        pc.grid(row=4, column=0, sticky="ew", pady=(0,10))
        pc.grid_columnconfigure(0, weight=1)

        pt = ctk.CTkFrame(pc, fg_color="transparent")
        pt.grid(row=0, column=0, padx=18, pady=(14,4), sticky="ew")
        pt.grid_columnconfigure(0, weight=1)
        self.status_lbl = ctk.CTkLabel(pt, text="✨ Ready to download",
                                        font=ctk.CTkFont(size=13),
                                        text_color=TEXT, anchor="w")
        self.status_lbl.grid(row=0, column=0, sticky="w")
        self.pct_lbl = ctk.CTkLabel(pt, text="0%",
                                     font=ctk.CTkFont(size=14, weight="bold"),
                                     text_color=ACCENT)
        self.pct_lbl.grid(row=0, column=1, sticky="e")

        self.prog_bar = ctk.CTkProgressBar(pc, height=14, corner_radius=7,
                                            fg_color=CARD2, progress_color=ACCENT)
        self.prog_bar.set(0)
        self.prog_bar.grid(row=1, column=0, padx=18, pady=(0,6), sticky="ew")

        se = ctk.CTkFrame(pc, fg_color="transparent")
        se.grid(row=2, column=0, padx=18, pady=(0,14), sticky="ew")
        se.grid_columnconfigure(1, weight=1)
        self.speed_lbl = ctk.CTkLabel(se, text="⚡ --",
                                       font=ctk.CTkFont(size=11), text_color=SUBTEXT)
        self.speed_lbl.grid(row=0, column=0, sticky="w")
        self.eta_lbl = ctk.CTkLabel(se, text="⏱ ETA: --",
                                     font=ctk.CTkFont(size=11), text_color=SUBTEXT)
        self.eta_lbl.grid(row=0, column=1, sticky="e")
        self.size_lbl = ctk.CTkLabel(se, text="💾 --",
                                      font=ctk.CTkFont(size=11), text_color=SUBTEXT)
        self.size_lbl.grid(row=0, column=2, sticky="e", padx=(12,0))

        # Log
        lc = ctk.CTkFrame(self.dl_frame, fg_color=CARD, corner_radius=16)
        lc.grid(row=5, column=0, sticky="ew", pady=(0,10))
        lc.grid_columnconfigure(0, weight=1)

        lh = ctk.CTkFrame(lc, fg_color="transparent")
        lh.grid(row=0, column=0, padx=18, pady=(12,6), sticky="ew")
        lh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(lh, text="📋  LOG",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(lh, text="Clear", width=55, height=22,
                      font=ctk.CTkFont(size=11), fg_color=BTN_GRAY,
                      hover_color="#3d3d6e", corner_radius=6,
                      command=self._clear_log).grid(row=0, column=1, sticky="e")

        self.log_box = ctk.CTkTextbox(
            lc, font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=CARD2, text_color=TEXT, border_width=0,
            corner_radius=8, wrap="word", state="disabled", height=140)
        self.log_box.grid(row=1, column=0, padx=18, pady=(0,16), sticky="ew")

    def _update_cb_banner(self):
        self.cb_banner.configure(height=36 if self._clipboard_enabled else 0)

    def _open_schedule_dialog(self):
        url = self.url_input.get().strip()
        if not url:
            self._set_status("⚠ Paste a URL first!", WARN)
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("⏰ Schedule Download")
        dialog.geometry("420x300")
        dialog.configure(fg_color=BG)
        dialog.attributes("-topmost", True)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="⏰  Schedule Download",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT).pack(padx=24, pady=(20,4), anchor="w")
        ctk.CTkLabel(dialog, text=url[:55]+"…" if len(url)>55 else url,
                     font=ctk.CTkFont(size=11), text_color=SUBTEXT).pack(
            padx=24, pady=(0,12), anchor="w")

        ctk.CTkLabel(dialog, text="Quick schedule:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=SUBTEXT).pack(padx=24, anchor="w")

        qr = ctk.CTkFrame(dialog, fg_color="transparent")
        qr.pack(padx=24, pady=8, anchor="w")
        selected_time = [None]

        def set_quick(minutes):
            t = datetime.now() + timedelta(minutes=minutes)
            selected_time[0] = t
            time_lbl.configure(
                text=f"⏰ Scheduled: {t.strftime('%d %b %Y  %H:%M')}",
                text_color=ORANGE)

        for label, mins in [("30 min",30),("1 hour",60),("2 hours",120),("Tonight",None)]:
            if mins is None:
                now = datetime.now()
                tonight = now.replace(hour=23, minute=0, second=0)
                mins = max(1, int((tonight-now).total_seconds()//60))
            ctk.CTkButton(qr, text=label, width=88, height=30,
                          font=ctk.CTkFont(size=11), fg_color=CARD2,
                          hover_color=CARD3, corner_radius=8,
                          command=lambda m=mins: set_quick(m)).pack(
                side="left", padx=(0,6))

        time_lbl = ctk.CTkLabel(dialog, text="No time selected",
                                 font=ctk.CTkFont(size=12), text_color=DIM)
        time_lbl.pack(padx=24, pady=8, anchor="w")

        def confirm():
            if not selected_time[0]:
                time_lbl.configure(text="⚠ Select a time!", text_color=DANGER)
                return
            self._schedule_download(url, selected_time[0])
            dialog.destroy()

        ctk.CTkButton(dialog, text="✔  Confirm Schedule",
                      height=42, font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=ORANGE, hover_color="#b45309",
                      corner_radius=10, command=confirm).pack(
            padx=24, pady=12, fill="x")

    def _schedule_download(self, url, scheduled_time):
        ck = self.settings.get('cookies', COOKIES_PATH)
        dl = self.settings.get('download_path', DOWNLOAD_PATH)
        item = DownloadItem(
            url=url, quality=self.quality_var.get(),
            cookies=ck, dl_path=dl,
            subtitles=self.sub_var.get(),
            playlist=self.plist_var.get(),
            scheduled_time=scheduled_time)
        with self.queue_lock:
            self.download_queue.append(item)
        self.schedule_list.append({
            'url': url, 'quality': self.quality_var.get(),
            'time': scheduled_time.isoformat(), 'title': item.title,
        })
        save_json(SCHEDULE_FILE, self.schedule_list)
        time_str = scheduled_time.strftime("%d %b %Y  %H:%M")
        self.log(f"⏰ Scheduled: {item.title[:45]}  →  {time_str}")
        self._set_status(f"⏰ Scheduled for {time_str}", ORANGE)
        self._switch_tab("schedule")
        self._refresh_schedule()

    def _build_queue_tab(self):
        self.q_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.q_frame.grid(row=0, column=0, sticky="nsew")
        self.q_frame.grid_columnconfigure(0, weight=1)
        self.q_frame.grid_rowconfigure(1, weight=1)

        qh = ctk.CTkFrame(self.q_frame, fg_color=CARD, corner_radius=12)
        qh.grid(row=0, column=0, padx=16, pady=(12,8), sticky="ew")
        qh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(qh, text="📋  Download Queue",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=18, pady=10, sticky="w")

        qb = ctk.CTkFrame(qh, fg_color="transparent")
        qb.grid(row=0, column=1, padx=18, pady=10)
        for text, color, hover, cmd in [
            ("▶ Start All",   BTN_DL,    "#2d4abf", self._start_queue),
            ("⏸ Pause All",  BTN_PAUSE, "#b56a1a", self._pause_all),
            ("▶ Resume All", BTN_UP,    "#0a8a64", self._resume_all),
            ("🗑 Clear Done", BTN_GRAY,  "#3d3d6e", self._clear_done),
        ]:
            ctk.CTkButton(qb, text=text, width=108, height=30,
                          font=ctk.CTkFont(size=11), fg_color=color,
                          hover_color=hover, corner_radius=8,
                          command=cmd).pack(side="left", padx=(0,5))

        self.queue_scroll = ctk.CTkScrollableFrame(
            self.q_frame, fg_color="transparent", scrollbar_button_color=DIM)
        self.queue_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,12))
        self.queue_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_queue(self):
        for w in self.queue_scroll.winfo_children():
            w.destroy()
        self._item_widgets.clear()
        active = [i for i in self.download_queue if i.status != STATUS_SCHEDULED]
        if not active:
            ctk.CTkLabel(self.queue_scroll,
                         text="Queue is empty!\nAdd URLs from Download tab.",
                         font=ctk.CTkFont(size=14), text_color=DIM,
                         justify="center").pack(pady=50)
            return
        for i, item in enumerate(active):
            self._create_queue_row(i, item)

    def _create_queue_row(self, idx, item):
        row = ctk.CTkFrame(self.queue_scroll, fg_color=CARD, corner_radius=12)
        row.grid(row=idx, column=0, sticky="ew", pady=4)
        row.grid_columnconfigure(1, weight=1)

        color = STATUS_COLORS.get(item.status, BTN_GRAY)
        sl = ctk.CTkLabel(row, text=item.status,
                          font=ctk.CTkFont(size=10, weight="bold"),
                          fg_color=color, corner_radius=6,
                          text_color="white", width=120, height=26)
        sl.grid(row=0, column=0, padx=(14,10), pady=(12,4))
        ctk.CTkLabel(row, text=f"#{idx+1}",
                     font=ctk.CTkFont(size=10), text_color=DIM).grid(
            row=1, column=0, padx=14, pady=(0,12))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=10)
        info.grid_columnconfigure(0, weight=1)

        tl = ctk.CTkLabel(info, text=item.title[:72],
                          font=ctk.CTkFont(size=13, weight="bold"),
                          text_color=TEXT, anchor="w")
        tl.grid(row=0, column=0, sticky="ew")

        pb = ctk.CTkProgressBar(info, height=6, corner_radius=3,
                                 fg_color=CARD2, progress_color=ACCENT)
        pb.set(item.progress/100)
        pb.grid(row=1, column=0, sticky="ew", pady=(4,2))

        ml = ctk.CTkLabel(info,
                          text=f"{item.quality}  ·  {item.speed}  ·  ETA {item.eta}",
                          font=ctk.CTkFont(size=11), text_color=DIM, anchor="w")
        ml.grid(row=2, column=0, sticky="w")

        bc = ctk.CTkFrame(row, fg_color="transparent")
        bc.grid(row=0, column=2, rowspan=2, padx=14, pady=10)

        if item.status in [STATUS_DOWNLOADING, STATUS_WAITING, STATUS_FETCHING]:
            ctk.CTkButton(bc, text="⏸", width=36, height=32,
                          font=ctk.CTkFont(size=15), fg_color=BTN_PAUSE,
                          hover_color="#b56a1a", corner_radius=6,
                          command=lambda it=item: self._toggle_pause(it)).pack(pady=(0,4))
        elif item.status == STATUS_PAUSED:
            ctk.CTkButton(bc, text="▶", width=36, height=32,
                          font=ctk.CTkFont(size=15), fg_color=BTN_DL,
                          hover_color="#2d4abf", corner_radius=6,
                          command=lambda it=item: self._toggle_pause(it)).pack(pady=(0,4))

        ctk.CTkButton(bc, text="✕", width=36, height=32,
                      font=ctk.CTkFont(size=15), fg_color=BTN_RED,
                      hover_color="#a93226", corner_radius=6,
                      command=lambda it=item: self._cancel_item(it)).pack()

        self._item_widgets[id(item)] = {
            'status': sl, 'progress': pb, 'title': tl, 'meta': ml}

    def _update_item(self, item):
        w = self._item_widgets.get(id(item))
        if not w:
            return
        color = STATUS_COLORS.get(item.status, BTN_GRAY)
        try:
            w['status'].configure(text=item.status, fg_color=color)
            w['progress'].set(item.progress/100)
            w['title'].configure(text=item.title[:72])
            w['meta'].configure(
                text=f"{item.quality}  ·  {item.speed}  ·  ETA {item.eta}")
        except Exception:
            pass

    def _build_schedule_tab(self):
        self.sc_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.sc_frame.grid(row=0, column=0, sticky="nsew")
        self.sc_frame.grid_columnconfigure(0, weight=1)
        self.sc_frame.grid_rowconfigure(1, weight=1)

        sh = ctk.CTkFrame(self.sc_frame, fg_color=CARD, corner_radius=12)
        sh.grid(row=0, column=0, padx=16, pady=(12,8), sticky="ew")
        sh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sh, text="⏰  Scheduled Downloads",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=18, pady=12, sticky="w")
        ctk.CTkLabel(sh, text="Downloads will start automatically at the scheduled time",
                     font=ctk.CTkFont(size=11), text_color=DIM).grid(
            row=1, column=0, padx=18, pady=(0,12), sticky="w")

        self.sc_scroll = ctk.CTkScrollableFrame(
            self.sc_frame, fg_color="transparent", scrollbar_button_color=DIM)
        self.sc_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,12))
        self.sc_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_schedule(self):
        for w in self.sc_scroll.winfo_children():
            w.destroy()
        scheduled = [i for i in self.download_queue
                     if i.status == STATUS_SCHEDULED and i.scheduled_time]
        if not scheduled:
            ctk.CTkLabel(self.sc_scroll,
                         text="No scheduled downloads!\n\nUse ⏰ Schedule button\non the Download tab.",
                         font=ctk.CTkFont(size=14), text_color=DIM,
                         justify="center").pack(pady=50)
            return
        for i, item in enumerate(scheduled):
            row = ctk.CTkFrame(self.sc_scroll, fg_color=CARD, corner_radius=12)
            row.grid(row=i, column=0, sticky="ew", pady=4)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text="⏰", font=ctk.CTkFont(size=24)).grid(
                row=0, column=0, padx=(16,10), pady=14)
            ic = ctk.CTkFrame(row, fg_color="transparent")
            ic.grid(row=0, column=1, sticky="ew", pady=10)
            ctk.CTkLabel(ic, text=item.title[:65],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT, anchor="w").pack(anchor="w")
            time_str = item.scheduled_time.strftime("%d %b %Y  %H:%M")
            ctk.CTkLabel(ic, text=f"⏰ {time_str}  ·  {item.quality}",
                         font=ctk.CTkFont(size=11), text_color=ORANGE,
                         anchor="w").pack(anchor="w")
            ctk.CTkButton(row, text="✕ Cancel", width=85, height=30,
                          font=ctk.CTkFont(size=11), fg_color=BTN_RED,
                          hover_color="#a93226", corner_radius=8,
                          command=lambda it=item: self._cancel_item(it)).grid(
                row=0, column=2, padx=14)

    def _build_thumb_tab(self):
        self.th_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.th_frame.grid(row=0, column=0, sticky="nsew")
        self.th_frame.grid_columnconfigure(0, weight=1)
        self.th_frame.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self.th_frame, fg_color=CARD, corner_radius=12)
        hdr.grid(row=0, column=0, padx=16, pady=(12,8), sticky="ew")
        ctk.CTkLabel(hdr, text="🖼  Thumbnail Downloader",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(padx=18, pady=(12,4), anchor="w")
        ctk.CTkLabel(hdr,
                     text="Download full-resolution thumbnails — no video download needed!",
                     font=ctk.CTkFont(size=11), text_color=DIM).pack(
            padx=18, pady=(0,12), anchor="w")

        card = ctk.CTkFrame(self.th_frame, fg_color=CARD, corner_radius=16)
        card.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(card, text="🔗  URL",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, padx=18, pady=(18,6), sticky="w")

        th_row = ctk.CTkFrame(card, fg_color="transparent")
        th_row.grid(row=1, column=0, padx=18, pady=(0,14), sticky="ew")
        th_row.grid_columnconfigure(0, weight=1)

        self.th_url = ctk.CTkEntry(th_row, placeholder_text="Paste video URL…",
                                    height=42, font=ctk.CTkFont(size=13),
                                    fg_color=CARD2, border_color=DIM,
                                    border_width=1, text_color=TEXT)
        self.th_url.grid(row=0, column=0, sticky="ew", padx=(0,8))
        ctk.CTkButton(th_row, text="🖼 Get Thumbnail", width=140, height=42,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=PINK, hover_color="#c73a7a", corner_radius=10,
                      command=self._fetch_thumbnail).grid(row=0, column=1)

        self.th_preview = ctk.CTkLabel(
            card, text="🖼\n\nPaste a URL above and click Get Thumbnail",
            font=ctk.CTkFont(size=13), text_color=DIM)
        self.th_preview.grid(row=2, column=0, pady=20)

        self.th_save_btn = ctk.CTkButton(
            card, text="💾  Save Thumbnail to Downloads",
            height=40, width=240, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=BTN_UP, hover_color="#0a8a64", corner_radius=10,
            command=self._save_thumbnail, state="disabled")
        self.th_save_btn.grid(row=3, column=0, pady=(0,16))
        self._th_img_data = None

    def _fetch_thumbnail(self):
        url = self.th_url.get().strip()
        if not url:
            return
        self.th_preview.configure(text="🔍 Fetching…", image=None)
        threading.Thread(target=self._do_fetch_thumb, args=(url,), daemon=True).start()

    def _do_fetch_thumb(self, url):
        try:
            ck = self.settings.get('cookies', COOKIES_PATH)
            opts = {'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True}
            if os.path.exists(ck):
                opts['cookiefile'] = ck
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            thumb_url = info.get('thumbnail','')
            title     = info.get('title','thumbnail')
            if not thumb_url:
                self.after(0, lambda: self.th_preview.configure(text="✖ No thumbnail found"))
                return
            req = urllib.request.Request(thumb_url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            self._th_img_data = (data, title)
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            w, h = img.size
            nw = min(600, w)
            nh = int(h*nw/w)
            img = img.resize((nw,nh), Image.LANCZOS)
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0,0,*img.size], radius=14, fill=255)
            img.putalpha(mask)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(nw,nh))
            self.after(0, lambda: (
                self.th_preview.configure(text="", image=ctk_img),
                setattr(self,'_th_ctk_img', ctk_img),
                self.th_save_btn.configure(state="normal")))
        except Exception as e:
            self.after(0, lambda: self.th_preview.configure(
                text=f"✖ Error: {str(e)[:60]}", image=None))

    def _save_thumbnail(self):
        if not self._th_img_data:
            return
        data, title = self._th_img_data
        safe = "".join(c for c in title if c.isalnum() or c in " _-")[:50]
        path = os.path.join(self.settings['download_path'], f"{safe}_thumbnail.jpg")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)
        self.log(f"✔ Thumbnail saved!")
        self.th_preview.configure(text="✔ Saved to Downloads folder!")

    def _build_history_tab(self):
        self.hist_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.hist_frame.grid(row=0, column=0, sticky="nsew")
        self.hist_frame.grid_columnconfigure(0, weight=1)
        self.hist_frame.grid_rowconfigure(1, weight=1)

        hh = ctk.CTkFrame(self.hist_frame, fg_color=CARD, corner_radius=12)
        hh.grid(row=0, column=0, padx=16, pady=(12,8), sticky="ew")
        hh.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hh, text="🕘  Download History",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).grid(row=0, column=0, padx=18, pady=12, sticky="w")
        ctk.CTkButton(hh, text="🗑 Clear All", width=100, height=28,
                      font=ctk.CTkFont(size=11), fg_color=DANGER,
                      hover_color="#c0392b", corner_radius=8,
                      command=self._clear_history).grid(row=0, column=1, padx=18)

        self.hist_scroll = ctk.CTkScrollableFrame(
            self.hist_frame, fg_color="transparent", scrollbar_button_color=DIM)
        self.hist_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0,12))
        self.hist_scroll.grid_columnconfigure(0, weight=1)

    def _refresh_history(self):
        for w in self.hist_scroll.winfo_children():
            w.destroy()
        if not self.history:
            ctk.CTkLabel(self.hist_scroll, text="No downloads yet!",
                         font=ctk.CTkFont(size=14), text_color=DIM).pack(pady=50)
            return
        for i, item in enumerate(reversed(self.history)):
            row = ctk.CTkFrame(self.hist_scroll, fg_color=CARD, corner_radius=12)
            row.grid(row=i, column=0, sticky="ew", pady=4)
            row.grid_columnconfigure(1, weight=1)
            plat = item.get('platform','?')[:2].upper()
            ctk.CTkLabel(row, text=plat,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         fg_color=ACCENT, corner_radius=6,
                         text_color="white", width=38, height=38).grid(
                row=0, column=0, padx=(14,10), pady=12)
            ic = ctk.CTkFrame(row, fg_color="transparent")
            ic.grid(row=0, column=1, sticky="ew", pady=10)
            ctk.CTkLabel(ic, text=item.get('title','Unknown')[:72],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(ic,
                         text=f"🎬 {item.get('quality','?')}  ·  📅 {item.get('date','?')}  ·  ⏱ {item.get('duration','?')}",
                         font=ctk.CTkFont(size=11), text_color=DIM,
                         anchor="w").pack(anchor="w")
            ctk.CTkButton(row, text="⬇ Again", width=85, height=30,
                          font=ctk.CTkFont(size=11), fg_color=BTN_DL,
                          hover_color="#2d4abf", corner_radius=8,
                          command=lambda u=item.get('url',''):
                              self._redownload(u)).grid(row=0, column=2, padx=14)

    def _clear_history(self):
        self.history = []
        save_json(HISTORY_FILE, self.history)
        self._refresh_history()

    def _redownload(self, url):
        self._switch_tab("download")
        self.url_input.delete(0,"end")
        self.url_input.insert(0, url)
        self._fetch_info()

    def _build_settings_tab(self):
        self.set_frame = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent", scrollbar_button_color=DIM)
        self.set_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)
        self.set_frame.grid_columnconfigure(0, weight=1)

        # Clipboard
        cb = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        cb.grid(row=0, column=0, sticky="ew", pady=(0,10))
        cb.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cb, text="📋  CLIPBOARD AUTO-DETECT",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT2).grid(row=0, column=0, padx=18, pady=(14,4), sticky="w")
        ctk.CTkLabel(cb,
                     text="Automatically detect video URLs when copied from any browser or app",
                     font=ctk.CTkFont(size=11), text_color=DIM).grid(
            row=1, column=0, padx=18, pady=(0,12), sticky="w")
        cb_row = ctk.CTkFrame(cb, fg_color="transparent")
        cb_row.grid(row=2, column=0, padx=18, pady=(0,16), sticky="ew")
        self.cb_setting_switch = ctk.CTkSwitch(
            cb_row, text="Enable clipboard monitoring",
            font=ctk.CTkFont(size=12), text_color=TEXT,
            fg_color=DIM, progress_color=ACCENT2,
            command=self._toggle_clipboard)
        self.cb_setting_switch.pack(side="left")
        if self._clipboard_enabled:
            self.cb_setting_switch.select()

        # Cookies
        ck = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        ck.grid(row=1, column=0, sticky="ew", pady=(0,10))
        ck.grid_columnconfigure(0, weight=1)
        ck_h = ctk.CTkFrame(ck, fg_color="transparent")
        ck_h.grid(row=0, column=0, padx=18, pady=(14,6), sticky="ew")
        ck_h.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(ck_h, text="🍪  COOKIES FILE",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=PURPLE).grid(row=0, column=0, sticky="w")
        exists = os.path.exists(self.settings['cookies'])
        self.ck_status = ctk.CTkLabel(
            ck_h,
            text="✔ HD Quality Enabled!" if exists else "✖ No cookies found",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT2 if exists else DANGER)
        self.ck_status.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(ck,
                     text="Export cookies.txt from YouTube using 'Get cookies.txt LOCALLY' Chrome extension",
                     font=ctk.CTkFont(size=11), text_color=DIM).grid(
            row=1, column=0, padx=18, pady=(0,6), sticky="w")
        self.ck_entry = ctk.CTkEntry(ck, height=40, font=ctk.CTkFont(size=13),
                                      fg_color=CARD2, border_color=DIM,
                                      border_width=1, text_color=TEXT)
        self.ck_entry.insert(0, self.settings['cookies'])
        self.ck_entry.grid(row=2, column=0, padx=18, pady=(0,16), sticky="ew")
        self.ck_entry.bind("<KeyRelease>", self._save_cookies_setting)

        # Speed limit
        sl = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        sl.grid(row=2, column=0, sticky="ew", pady=(0,10))
        sl.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sl, text="⚡  SPEED LIMIT",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ORANGE).grid(row=0, column=0, padx=18, pady=(14,6), sticky="w")
        sl_row = ctk.CTkFrame(sl, fg_color="transparent")
        sl_row.grid(row=1, column=0, padx=18, pady=(0,16), sticky="ew")
        sl_row.grid_columnconfigure(0, weight=1)
        self.speed_slider = ctk.CTkSlider(sl_row, from_=0, to=10, number_of_steps=10,
                                           fg_color=CARD2, progress_color=ORANGE,
                                           button_color=ORANGE)
        self.speed_slider.set(self.settings.get('speed_limit',0))
        self.speed_slider.grid(row=0, column=0, sticky="ew")
        self.speed_val_lbl = ctk.CTkLabel(
            sl_row,
            text="Unlimited" if self.settings.get('speed_limit',0)==0
            else f"{int(self.settings['speed_limit'])} MB/s",
            font=ctk.CTkFont(size=12), text_color=ORANGE, width=100)
        self.speed_val_lbl.grid(row=0, column=1, padx=(12,0))
        self.speed_slider.configure(command=self._on_speed_change)

        # Concurrent
        cc = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        cc.grid(row=3, column=0, sticky="ew", pady=(0,10))
        cc.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cc, text="🔀  CONCURRENT DOWNLOADS",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).grid(row=0, column=0, padx=18, pady=(14,6), sticky="w")
        cc_row = ctk.CTkFrame(cc, fg_color="transparent")
        cc_row.grid(row=1, column=0, padx=18, pady=(0,16), sticky="ew")
        self.concurrent_var = ctk.StringVar(value=str(self.settings.get('max_concurrent',3)))
        ctk.CTkOptionMenu(cc_row, values=["1","2","3","4","5"],
                          variable=self.concurrent_var, width=100, height=36,
                          font=ctk.CTkFont(size=13), fg_color=CARD2,
                          button_color=ACCENT, dropdown_fg_color=CARD2).pack(side="left")
        ctk.CTkLabel(cc_row, text=" simultaneous downloads",
                     font=ctk.CTkFont(size=12), text_color=SUBTEXT).pack(side="left")

        # Theme
        th = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        th.grid(row=4, column=0, sticky="ew", pady=(0,10))
        ctk.CTkLabel(th, text="🎨  THEME",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=PINK).pack(padx=18, pady=(14,8), anchor="w")
        th_row = ctk.CTkFrame(th, fg_color="transparent")
        th_row.pack(padx=18, pady=(0,16), anchor="w")
        for label, mode in [("🌑 Dark","dark"),("☀️ Light","light"),("🖥 System","system")]:
            ctk.CTkButton(th_row, text=label, width=100, height=32,
                          font=ctk.CTkFont(size=12), fg_color=CARD2,
                          hover_color=CARD3, corner_radius=8,
                          command=lambda m=mode: self._set_theme(m)).pack(
                side="left", padx=(0,6))

        # About
        ab = ctk.CTkFrame(self.set_frame, fg_color=CARD, corner_radius=16)
        ab.grid(row=5, column=0, sticky="ew")
        ctk.CTkLabel(ab, text="ℹ  ABOUT",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=ACCENT).pack(padx=18, pady=(14,4), anchor="w")
        ffmpeg_ok = FFMPEG_LOCATION is not None
        ctk.CTkLabel(ab,
                     text=f"Ultimate Video Downloader  v5.1 ULTRA  —  FREE\n\n"
                          f"⚡ FFmpeg: {'Bundled ✔' if ffmpeg_ok else 'System'}\n\n"
                          "✔ Auto Clipboard Detection   ✔ Scheduled Downloads\n"
                          "✔ Batch Download             ✔ Pause / Resume\n"
                          "✔ FFmpeg Bundled             ✔ Works on any PC\n"
                          "✔ Thumbnail Downloader       ✔ Download History\n"
                          "✔ Speed Limiter              ✔ Dark / Light Theme\n\n"
                          "Built with Python · CustomTkinter · yt-dlp · FFmpeg",
                     font=ctk.CTkFont(size=12), text_color=SUBTEXT,
                     justify="left").pack(padx=18, pady=(0,8), anchor="w")

        gh_row = ctk.CTkFrame(ab, fg_color="transparent")
        gh_row.pack(padx=18, pady=(0,16), anchor="w")
        ctk.CTkButton(gh_row, text="🐛 Report Bug", width=130, height=32,
                      font=ctk.CTkFont(size=12), fg_color=DANGER,
                      hover_color="#a93226", corner_radius=8,
                      command=lambda: webbrowser.open(GITHUB_ISSUES)).pack(
            side="left", padx=(0,8))
        ctk.CTkButton(gh_row, text="⭐ Star on GitHub", width=140, height=32,
                      font=ctk.CTkFont(size=12), fg_color=BTN_GRAY,
                      hover_color="#3d3d6e", corner_radius=8,
                      command=lambda: webbrowser.open(GITHUB_URL)).pack(side="left")

    def _on_url_type(self, event=None):
        if self._fetch_timer:
            self.after_cancel(self._fetch_timer)
        self._fetch_timer = self.after(1400, self._fetch_info)

    def _paste_url(self):
        try:
            text = self.clipboard_get().strip()
            self.url_input.delete(0,"end")
            self.url_input.insert(0, text)
            self._fetch_info()
        except Exception:
            pass

    def _fetch_info(self):
        url = self.url_input.get().strip()
        if not url or not url.startswith("http"):
            return
        threading.Thread(target=self._do_fetch_info, args=(url,), daemon=True).start()

    def _do_fetch_info(self, url):
        try:
            clean = url.split('&list=')[0] if '&list=' in url else url
            ck = self.settings.get('cookies', COOKIES_PATH)
            opts = {'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True}
            if os.path.exists(ck):
                opts['cookiefile'] = ck
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean, download=False)
            title     = info.get('title','Unknown')
            dur       = info.get('duration',0)
            uploader  = info.get('uploader', info.get('channel','?'))
            views     = info.get('view_count',0)
            extractor = info.get('extractor_key','Unknown')
            thumb     = info.get('thumbnail','')
            dur_str   = f"{int(dur//60)}:{int(dur%60):02d}" if dur else "?"
            meta = f"👤 {uploader}   ⏱ {dur_str}"
            if views: meta += f"   👁 {views:,}"
            self.after(0, lambda: self._show_preview(title, meta, extractor, thumb))
        except Exception:
            self.after(0, self._hide_preview)

    def _show_preview(self, title, meta, platform, thumb_url):
        self.preview_card.configure(height=130)
        self.prev_title.configure(text=title)
        self.prev_meta.configure(text=meta)
        plat_colors = {'Youtube':DANGER,'Instagram':PINK,'TikTok':TEXT,
                       'Facebook':ACCENT,'Twitter':ACCENT}
        color = plat_colors.get(platform, ACCENT)
        self.prev_plat.configure(text=f"  {platform}  ", fg_color=color, corner_radius=6)
        if thumb_url:
            threading.Thread(target=self._load_thumb, args=(thumb_url,), daemon=True).start()

    def _hide_preview(self):
        self.preview_card.configure(height=0)

    def _load_thumb(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = r.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = img.resize((178,100), Image.LANCZOS)
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle([0,0,*img.size], radius=10, fill=255)
            img.putalpha(mask)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(178,100))
            self.after(0, lambda: (
                self.thumb_lbl.configure(image=ctk_img, text=""),
                setattr(self,'_thumb_img', ctk_img),
                self.thumb_lbl.grid(row=0, column=0, padx=(16,0), pady=16)))
        except Exception:
            pass

    def _open_folder(self):
        path = self.settings.get('download_path', DOWNLOAD_PATH)
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0","end")
        self.log_box.configure(state="disabled")

    def log(self, msg):
        self.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, msg, color=TEXT):
        self.after(0, lambda: self.status_lbl.configure(text=msg, text_color=color))

    def _set_progress(self, val, speed="", eta="", size=""):
        def _do():
            self.prog_bar.set(val/100)
            self.pct_lbl.configure(text=f"{int(val)}%")
            if speed: self.speed_lbl.configure(text=f"⚡ {speed}")
            if eta:   self.eta_lbl.configure(text=f"⏱ ETA: {eta}")
            if size:  self.size_lbl.configure(text=f"💾 {size}")
        self.after(0, _do)

    def _save_cookies_setting(self, event=None):
        path = self.ck_entry.get().strip()
        self.settings['cookies'] = path
        save_json(SETTINGS_FILE, self.settings)
        exists = os.path.exists(path)
        self.ck_status.configure(
            text="✔ HD Quality Enabled!" if exists else "✖ No cookies found",
            text_color=ACCENT2 if exists else DANGER)
        self.ck_badge.configure(
            text="🍪 HD Ready" if exists else "🍪 No Cookies",
            text_color=ACCENT2 if exists else WARN)

    def _on_speed_change(self, val):
        v = int(val)
        self.settings['speed_limit'] = v
        save_json(SETTINGS_FILE, self.settings)
        self.speed_val_lbl.configure(text="Unlimited" if v==0 else f"{v} MB/s")

    def _set_theme(self, mode):
        ctk.set_appearance_mode(mode)
        self.settings['theme'] = mode
        save_json(SETTINGS_FILE, self.settings)

    def _load_stats(self):
        total = len(self.history)
        today = sum(1 for h in self.history
                    if h.get('date','').startswith(datetime.now().strftime("%d %b %Y")))
        self.after(0, lambda: self.stats_label.configure(
            text=f"📥 {today} today  ·  {total} total downloads"))

    def _add_single(self):
        url = self.url_input.get().strip()
        if not url:
            self._set_status("⚠ Please paste a URL!", WARN)
            return
        self._enqueue(url)
        self._switch_tab("queue")
        self._start_queue()

    def _add_batch(self):
        lines = self.batch_input.get("1.0","end").strip().splitlines()
        urls = [l.strip() for l in lines if l.strip().startswith("http")]
        single = self.url_input.get().strip()
        if single:
            urls.insert(0, single)
        if not urls:
            self._set_status("⚠ No valid URLs!", WARN)
            return
        for u in urls:
            self._enqueue(u)
        self.log(f"● {len(urls)} URLs added to queue")
        self._switch_tab("queue")
        self._start_queue()

    def _enqueue(self, url, scheduled_time=None):
        ck = self.settings.get('cookies', COOKIES_PATH)
        dl = self.settings.get('download_path', DOWNLOAD_PATH)
        sp = int(self.speed_slider.get())*1024*1024 if hasattr(self,'speed_slider') and self.speed_slider.get()>0 else 0
        item = DownloadItem(
            url=url, quality=self.quality_var.get(),
            cookies=ck, dl_path=dl,
            subtitles=self.sub_var.get(),
            playlist=self.plist_var.get(),
            speed_limit=sp,
            scheduled_time=scheduled_time)
        with self.queue_lock:
            self.download_queue.append(item)
        return item

    def _start_queue(self):
        max_c = int(self.concurrent_var.get()) if hasattr(self,'concurrent_var') else 3
        with self.queue_lock:
            running = sum(1 for i in self.download_queue
                         if i.status in [STATUS_DOWNLOADING, STATUS_FETCHING])
            waiting = [i for i in self.download_queue if i.status==STATUS_WAITING]
        for item in waiting[:max(0, max_c-running)]:
            threading.Thread(target=self._run_item, args=(item,), daemon=True).start()

    def _pause_all(self):
        with self.queue_lock:
            for i in self.download_queue:
                if i.status == STATUS_DOWNLOADING:
                    i.pause()
                    self.after(0, lambda it=i: self._update_item(it))

    def _resume_all(self):
        with self.queue_lock:
            for i in self.download_queue:
                if i.status == STATUS_PAUSED:
                    i.resume()
                    self.after(0, lambda it=i: self._update_item(it))
        self._start_queue()

    def _toggle_pause(self, item):
        if item.paused:
            item.resume()
            self._start_queue()
        else:
            item.pause()
        self.after(0, lambda: self._update_item(item))

    def _cancel_item(self, item):
        item.cancel()
        self.after(0, lambda: self._update_item(item))

    def _clear_done(self):
        with self.queue_lock:
            self.download_queue = [
                i for i in self.download_queue
                if i.status not in [STATUS_DONE, STATUS_CANCELLED, STATUS_FAILED]]
        self._refresh_queue()

    def _run_item(self, item):
        for attempt in range(1, MAX_RETRIES+1):
            if item.cancelled:
                return
            if attempt > 1:
                item.status = f"⟳ Retry {attempt}/{MAX_RETRIES}"
                self.after(0, lambda: self._update_item(item))
                time.sleep(attempt*3)
            if self._do_download(item):
                break
        if not item.cancelled and item.status != STATUS_DONE:
            item.status = STATUS_FAILED
            self.after(0, lambda: self._update_item(item))
        self._start_queue()

    def _do_download(self, item):
        try:
            os.makedirs(item.dl_path, exist_ok=True)
            item.status = STATUS_FETCHING
            self.after(0, lambda: self._update_item(item))

            q = item.quality
            if q == 'Audio Only (MP3)':
                fmt = 'bestaudio/best'
                pp  = [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]
            elif q == '4K (2160p)':
                fmt = 'bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]
            elif q == '1080p':
                fmt = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]
            elif q == '720p':
                fmt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]
            elif q == '480p':
                fmt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]
            elif q == '360p':
                fmt = 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]
            else:
                fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                pp  = [{'key':'FFmpegVideoConvertor','preferedformat':'mp4'}]

            if item.subtitles:
                pp.append({'key':'FFmpegSubtitlesConvertor','format':'srt'})

            opts = {
                'format': fmt, 'postprocessors': pp,
                'outtmpl': os.path.join(item.dl_path,'%(title)s.%(ext)s'),
                'logger': SilentLogger(),
                'progress_hooks': [lambda d, it=item: self._prog_hook(d,it)],
                'nocheckcertificate': True,
                'noplaylist': not item.playlist,
                'merge_output_format': 'mp4',
                'retries': 5, 'fragment_retries': 5, 'socket_timeout': 30,
            }

            # ── KEY FIX: Use bundled FFmpeg ───────────────────────────────────
            if FFMPEG_LOCATION:
                opts['ffmpeg_location'] = FFMPEG_LOCATION

            if item.subtitles:
                opts.update({'writesubtitles':True,'writeautomaticsub':True,
                             'subtitleslangs':['en','ur']})
            if item.speed_limit > 0:
                opts['ratelimit'] = item.speed_limit
            if os.path.exists(item.cookies):
                opts['cookiefile'] = item.cookies

            with yt_dlp.YoutubeDL(opts) as ydl:
                info      = ydl.extract_info(item.url, download=False)
                item.title= info.get('title', item.title)
                dur       = info.get('duration',0)
                platform  = info.get('extractor_key','Unknown')
                self.after(0, lambda: self._update_item(item))
                self.log(f"● {item.title[:55]}")
                item.status = STATUS_DOWNLOADING
                self.after(0, lambda: self._update_item(item))
                ydl.download([item.url])

            item.status   = STATUS_DONE
            item.progress = 100
            self.after(0, lambda: self._update_item(item))
            self._set_status(f"✔ {item.title[:45]}", ACCENT2)
            self._set_progress(100)
            self.log(f"✔ Saved: {item.title[:55]}")

            m, s = divmod(int(dur),60) if dur else (0,0)
            self.history.append({
                'title':    item.title,
                'url':      item.url,
                'quality':  q,
                'platform': platform,
                'duration': f"{m}:{s:02d}" if dur else '?',
                'date':     datetime.now().strftime("%d %b %Y %H:%M"),
            })
            save_json(HISTORY_FILE, self.history[-100:])
            self._load_stats()
            return True

        except Exception as e:
            item.status = STATUS_FAILED
            self.log(f"✖ {str(e)[:80]}")
            self.after(0, lambda: self._update_item(item))
            return False

    def _prog_hook(self, d, item):
        item._pause_ev.wait()
        if item.cancelled:
            raise Exception("Cancelled")
        if d.get('status') == 'downloading':
            try:
                pct   = float(d.get('_percent_str','0%').replace('%','').strip())
                speed = d.get('_speed_str','')
                eta   = d.get('_eta_str','')
                size  = d.get('_total_bytes_str', d.get('_total_bytes_estimate_str',''))
                item.progress = pct
                item.speed = speed
                item.eta   = eta
                item.size  = size
                item.status = STATUS_DOWNLOADING
                self.after(0, lambda: self._update_item(item))
                self._set_progress(pct, speed, eta, size)
                self._set_status(f"⬇ {item.title[:38]}…  {pct:.1f}%")
            except Exception:
                pass
        elif d.get('status') == 'finished':
            item.status = STATUS_MERGING
            self.after(0, lambda: self._update_item(item))

    def _auto_update(self):
        try:
            subprocess.run([sys.executable,'-m','pip','install','--upgrade','yt-dlp'],
                           capture_output=True, timeout=60)
        except Exception:
            pass

    def update_ytdlp(self):
        self.update_btn.configure(state="disabled")
        self.log("● Updating yt-dlp…")
        threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        try:
            r = subprocess.run([sys.executable,'-m','pip','install','-U','yt-dlp'],
                               capture_output=True, text=True, timeout=120)
            self.log("✔ yt-dlp updated!" if r.returncode==0 else "⚠ Update done.")
        except Exception as e:
            self.log(f"✖ Update failed: {e}")
        finally:
            self.after(0, lambda: self.update_btn.configure(state="normal"))


if __name__ == "__main__":
    app = App()
    app.mainloop()