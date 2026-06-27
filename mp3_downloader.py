#!/usr/bin/env python3
"""
MP3 / MP4 Downloader - fast, ad-free downloader for YouTube.
Tkinter GUI + yt-dlp + ffmpeg. Single file, no external GUI dependency.

Features:
  - Audio (mp3/m4a/wav/flac/opus) or Video (mp4/mkv/webm) mode
  - Quality selection: audio bitrate or video resolution
  - Speed limit (MB/s)
  - Advanced settings: concurrent fragments, playlist, cover+tags,
    subtitles, SponsorBlock, filename template, browser cookies
"""

import os
import sys
import io
import glob
import json
import time
import queue
import shutil
import threading
import webbrowser
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Install: python -m pip install yt-dlp")
    sys.exit(1)

try:
    from PIL import Image, ImageTk
    HAVE_PIL = True
except ImportError:                            # preview is optional
    HAVE_PIL = False


APP_NAME = "MP3 / MP4 Downloader"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".mp3_downloader.json")
AUTHOR_URL = "https://github.com/bugrahanceker17"

# ---------- Theme ----------
BG = "#1e1e2e"
BG2 = "#27293d"
FG = "#e0e0e0"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9277ff"
OK = "#3ddc97"
ERR = "#ff5c7c"
MUTED = "#8a8aa0"

AUDIO_FORMATS = ["mp3", "m4a", "wav", "flac", "opus"]
VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_QUALITIES = ["320", "256", "192", "128", "96"]
VIDEO_QUALITIES = ["Best", "2160", "1440", "1080", "720", "480", "360"]

# ---------- Languages / translations ----------
# display name -> language code
LANGUAGES = {"English": "en", "Türkçe": "tr"}

# key -> (english, turkish). Use self.t(key, **fmt) to resolve.
I18N = {
    "title":        ("🎵 MP3 / 🎬 MP4 Downloader", "🎵 MP3 / 🎬 MP4 İndirici"),
    "subtitle":     ("Paste a link, pick a folder, download. No ads.",
                     "Bağlantıyı yapıştır, klasör seç, indir. Reklamsız."),
    "language":     ("Language", "Dil"),
    "url_label":    ("Video / Playlist link", "Video / Oynatma listesi bağlantısı"),
    "preview_ph":   ("🎬  Preview", "🎬  Önizleme"),
    "preview_pil":  ("Preview needs Pillow (pip install pillow)",
                     "Önizleme için Pillow gerekli (pip install pillow)"),
    "preview_load": ("Loading preview…", "Önizleme yükleniyor…"),
    "preview_none": ("No preview", "Önizleme yok"),
    "folder_label": ("Save folder", "Kayıt klasörü"),
    "browse":       ("Browse", "Gözat"),
    "mode":         ("Mode", "Mod"),
    "audio_mode":   ("🎵 Audio (MP3)", "🎵 Ses (MP3)"),
    "video_mode":   ("🎬 Video (MP4)", "🎬 Video (MP4)"),
    "quality_kbps": ("Quality (kbps)", "Kalite (kbps)"),
    "resolution":   ("Resolution", "Çözünürlük"),
    "format":       ("Format", "Format"),
    "speed_limit":  ("Speed limit MB/s", "Hız sınırı MB/s"),
    "adv_show":     ("▸ Advanced settings", "▸ Gelişmiş ayarlar"),
    "adv_hide":     ("▾ Advanced settings", "▾ Gelişmiş ayarlar"),
    "playlist":     ("Download playlist", "Oynatma listesini indir"),
    "meta":         ("Embed cover + tags", "Kapak + etiket göm"),
    "sponsor":      ("SponsorBlock (skip sponsors)", "SponsorBlock (sponsorları atla)"),
    "subs":         ("Embed subtitles (video)", "Altyazı göm (video)"),
    "lang_word":    ("lang", "dil"),
    "frag":         ("Concurrent fragments", "Eşzamanlı parça"),
    "cookies":      ("Browser cookies (for age/member restricted)",
                     "Tarayıcı çerezleri (yaş/üyelik kısıtlı için)"),
    "tmpl":         ("Filename template", "Dosya adı şablonu"),
    "download":     ("⬇  Download", "⬇  İndir"),
    "cancel":       ("Cancel", "İptal"),
    "ready":        ("Ready.", "Hazır."),
    "warn_link":    ("Please enter a link.", "Lütfen bir bağlantı girin."),
    "warn_folder":  ("Please choose a save folder.", "Lütfen bir kayıt klasörü seçin."),
    "ffmpeg_warn":  ("WARNING: ffmpeg not found. Conversion/merging won't work.",
                     "UYARI: ffmpeg bulunamadı. Dönüştürme/birleştirme çalışmaz."),
    "starting":     ("Starting [{mode}]: {url}", "Başlıyor [{mode}]: {url}"),
    "cancelling":   ("Cancelling...", "İptal ediliyor..."),
    "downloading":  ("⬇ Downloading: {label}", "⬇ İndiriliyor: {label}"),
    "downloaded":   ("✓ Downloaded: {label}", "✓ İndirildi: {label}"),
    "failed":       ("✗ Failed: {label}", "✗ Başarısız: {label}"),
    "processing":   ("⚙ Processing ({name}): {label}", "⚙ İşleniyor ({name}): {label}"),
    "ready_track":  ("♪ Ready: {label}", "♪ Hazır: {label}"),
    "prog_dl":      ("Downloading  {pct:.0f}%  •  {spd}  •  ETA {eta}s",
                     "İndiriliyor  {pct:.0f}%  •  {spd}  •  ETA {eta}s"),
    "dl_finished":  ("Download finished, processing...", "İndirme bitti, işleniyor..."),
    "proc_status":  ("Processing: {name} ...", "İşleniyor: {name} ..."),
    "done":         ("Done! Folder: {folder}", "Bitti! Klasör: {folder}"),
    "cancelled":    ("Cancelled.", "İptal edildi."),
    "error":        ("Error: {e}", "Hata: {e}"),
}


def set_app_id():
    """Tell Windows this is its own app so the taskbar shows our icon."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "mp3downloader.app")
    except Exception:
        pass


def make_icon():
    """Build a 64x64 app icon (purple tile + white music note) as a PhotoImage."""
    W = H = 64
    bg = ACCENT
    note = "#ffffff"
    # note head: ellipse; stem: vertical bar; flag: small slanted bar
    hx, hy, rx, ry = 23, 45, 11, 8
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            px = bg
            if ((x - hx) / rx) ** 2 + ((y - hy) / ry) ** 2 <= 1.0:
                px = note                      # note head
            elif 32 <= x <= 35 and 15 <= y <= 45:
                px = note                      # stem
            elif 35 <= x <= 47 and (x - 35) >= (y - 15) >= (x - 35) - 5 and y <= 27:
                px = note                      # flag
            row.append(px)
        rows.append("{" + " ".join(row) + "}")
    img = tk.PhotoImage(width=W, height=H)
    img.put(" ".join(rows))
    return img


def find_ffmpeg():
    """Find ffmpeg.exe: PATH -> winget packages -> app folder."""
    exe = shutil.which("ffmpeg")
    if exe:
        return os.path.dirname(exe)
    candidates = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        candidates += glob.glob(
            os.path.join(local, "Microsoft", "WinGet", "Packages",
                         "Gyan.FFmpeg*", "**", "bin", "ffmpeg.exe"),
            recursive=True,
        )
    here = os.path.dirname(os.path.abspath(__file__))
    candidates += glob.glob(os.path.join(here, "**", "ffmpeg.exe"), recursive=True)
    for c in candidates:
        if os.path.isfile(c):
            return os.path.dirname(c)
    return None


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


class YtdlpLogger:
    """Forwards only yt-dlp errors to the log box; the rest is noise.

    Our own progress/post-process hooks already print the clean lines
    (⬇ / ✓ / ⚙ / ♪ / Done), so info/debug/warning chatter is dropped.
    """

    def __init__(self, log_fn):
        self._log = log_fn

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self._log("ERROR: " + msg, ERR)


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.lang = self.cfg.get("ui_lang", "en")
        if self.lang not in ("en", "tr"):
            self.lang = "en"
        self.ffmpeg_dir = find_ffmpeg()
        self.msg_queue = queue.Queue()
        self.worker = None
        self.cancel_flag = threading.Event()
        self.adv_visible = False
        self._cur_file = None
        self._last_pp = None
        self._thumb_img = None                 # keep ref so Tk won't GC it
        self._thumb_seq = 0                     # ignore stale preview loads
        self._thumb_after = None

        self._build_ui()
        self.root.after(80, self._drain_queue)
        if not self.ffmpeg_dir:
            self.log(self.t("ffmpeg_warn"), ERR)

    # ---------------- i18n ----------------
    def t(self, key, **fmt):
        """Resolve a translation key for the current language."""
        pair = I18N.get(key)
        if not pair:
            return key
        s = pair[0] if self.lang == "en" else pair[1]
        return s.format(**fmt) if fmt else s

    # ---------------- UI ----------------
    def _build_ui(self):
        r = self.root
        r.title(APP_NAME)
        r.configure(bg=BG)
        self._set_icon()
        self._center_window(700, 800)
        r.minsize(660, 720)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI Semibold", 18))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground=BG2, foreground=FG, insertcolor=FG, relief="flat")
        style.configure("TCombobox", fieldbackground=BG2, background=BG2, foreground=FG, arrowcolor=FG)
        style.map("TCombobox", fieldbackground=[("readonly", BG2)], foreground=[("readonly", FG)])
        style.configure("TSpinbox", fieldbackground=BG2, foreground=FG, arrowcolor=FG)
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Segoe UI Semibold", 11), borderwidth=0)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", "#444")])
        style.configure("TButton", background=BG2, foreground=FG, borderwidth=0)
        style.map("TButton", background=[("active", "#34374f")])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=BG2,
                        borderwidth=0, thickness=14)
        style.configure("TRadiobutton", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.map("TRadiobutton", background=[("active", BG)])

        pad = {"padx": 18}

        # Header: title on the left, language selector on the right
        header = ttk.Frame(r)
        header.pack(fill="x", pady=(14, 2), **pad)
        self.title_lbl = ttk.Label(header, text=self.t("title"), style="Title.TLabel")
        self.title_lbl.pack(side="left", anchor="w")
        lang_box = ttk.Frame(header)
        lang_box.pack(side="right", anchor="e")
        self.lang_caption = ttk.Label(lang_box, text=self.t("language"), style="Muted.TLabel")
        self.lang_caption.pack(side="left", padx=(0, 6))
        self.lang_display = tk.StringVar(value="English" if self.lang == "en" else "Türkçe")
        lang_cb = ttk.Combobox(lang_box, textvariable=self.lang_display, state="readonly",
                               width=10, values=list(LANGUAGES.keys()))
        lang_cb.pack(side="left")
        lang_cb.bind("<<ComboboxSelected>>", self._on_lang_change)

        self.subtitle_lbl = ttk.Label(r, text=self.t("subtitle"), style="Muted.TLabel")
        self.subtitle_lbl.pack(anchor="w", pady=(0, 10), **pad)

        # URL
        self.url_lbl = ttk.Label(r, text=self.t("url_label"))
        self.url_lbl.pack(anchor="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(r, textvariable=self.url_var, font=("Segoe UI", 11))
        url_entry.pack(fill="x", pady=(2, 10), ipady=5, **pad)
        url_entry.focus()

        # Thumbnail preview (auto-loads a moment after a link is pasted)
        prow = ttk.Frame(r)
        prow.pack(fill="x", pady=(0, 8), **pad)
        self.thumb_box = tk.Frame(prow, bg=BG2, width=256, height=144)
        self.thumb_box.pack()
        self.thumb_box.pack_propagate(False)
        placeholder = self.t("preview_ph") if HAVE_PIL else self.t("preview_pil")
        self.thumb_label = tk.Label(self.thumb_box, bg=BG2, fg=MUTED,
                                    text=placeholder, font=("Segoe UI", 9), wraplength=240)
        self.thumb_label.pack(fill="both", expand=True)
        self.thumb_title = ttk.Label(prow, text="", style="Muted.TLabel",
                                     wraplength=420, anchor="center", justify="center")
        self.thumb_title.pack(fill="x", pady=(4, 0))
        self.url_var.trace_add("write", self._on_url_change)

        # Folder
        self.folder_lbl = ttk.Label(r, text=self.t("folder_label"))
        self.folder_lbl.pack(anchor="w", **pad)
        frow = ttk.Frame(r)
        frow.pack(fill="x", pady=(2, 10), **pad)
        default_dir = self.cfg.get("folder") or os.path.join(os.path.expanduser("~"), "Music")
        self.folder_var = tk.StringVar(value=default_dir)
        ttk.Entry(frow, textvariable=self.folder_var, font=("Segoe UI", 10)).pack(
            side="left", fill="x", expand=True, ipady=5)
        self.browse_btn = ttk.Button(frow, text=self.t("browse"), command=self._browse)
        self.browse_btn.pack(side="left", padx=(8, 0))

        # Mode: Audio / Video
        mrow = ttk.Frame(r)
        mrow.pack(fill="x", pady=(2, 8), **pad)
        self.mode_lbl = ttk.Label(mrow, text=self.t("mode"))
        self.mode_lbl.pack(side="left", padx=(0, 10))
        self.mode_var = tk.StringVar(value=self.cfg.get("mode", "audio"))
        self.audio_rb = ttk.Radiobutton(mrow, text=self.t("audio_mode"), value="audio",
                                        variable=self.mode_var, command=self._on_mode_change)
        self.audio_rb.pack(side="left", padx=(0, 14))
        self.video_rb = ttk.Radiobutton(mrow, text=self.t("video_mode"), value="video",
                                        variable=self.mode_var, command=self._on_mode_change)
        self.video_rb.pack(side="left")

        # Quality + Format + Speed
        orow = ttk.Frame(r)
        orow.pack(fill="x", pady=(2, 10), **pad)
        self.quality_label = ttk.Label(orow, text=self.t("quality_kbps"))
        self.quality_label.pack(side="left")
        self.quality_var = tk.StringVar(value=self.cfg.get("quality", "320"))
        self.quality_cb = ttk.Combobox(orow, textvariable=self.quality_var, state="readonly", width=8)
        self.quality_cb.pack(side="left", padx=(6, 16))

        self.format_lbl = ttk.Label(orow, text=self.t("format"))
        self.format_lbl.pack(side="left")
        self.format_var = tk.StringVar(value=self.cfg.get("format", "mp3"))
        self.format_cb = ttk.Combobox(orow, textvariable=self.format_var, state="readonly", width=8)
        self.format_cb.pack(side="left", padx=(6, 16))

        self.speed_lbl = ttk.Label(orow, text=self.t("speed_limit"))
        self.speed_lbl.pack(side="left")
        self.rate_var = tk.StringVar(value=self.cfg.get("rate", ""))
        ttk.Entry(orow, textvariable=self.rate_var, width=7).pack(side="left", padx=(6, 0))

        # Advanced settings toggle
        self.adv_btn = ttk.Button(r, text=self.t("adv_show"), command=self._toggle_adv)
        self.adv_btn.pack(anchor="w", pady=(2, 4), **pad)

        # Advanced settings panel
        self.adv_frame = tk.Frame(r, bg=BG2)
        ap = {"padx": 12, "pady": 3}

        a1 = tk.Frame(self.adv_frame, bg=BG2); a1.pack(fill="x", **ap)
        self.playlist_var = tk.BooleanVar(value=self.cfg.get("playlist", True))
        self.playlist_chk = self._check(a1, self.t("playlist"), self.playlist_var)
        self.playlist_chk.pack(side="left", padx=(0, 16))
        self.meta_var = tk.BooleanVar(value=self.cfg.get("meta", True))
        self.meta_chk = self._check(a1, self.t("meta"), self.meta_var)
        self.meta_chk.pack(side="left", padx=(0, 16))
        self.sponsor_var = tk.BooleanVar(value=self.cfg.get("sponsor", False))
        self.sponsor_chk = self._check(a1, self.t("sponsor"), self.sponsor_var)
        self.sponsor_chk.pack(side="left")

        a2 = tk.Frame(self.adv_frame, bg=BG2); a2.pack(fill="x", **ap)
        self.subs_var = tk.BooleanVar(value=self.cfg.get("subs", False))
        self.subs_chk = self._check(a2, self.t("subs"), self.subs_var)
        self.subs_chk.pack(side="left", padx=(0, 8))
        self.lang_word_lbl = tk.Label(a2, text=self.t("lang_word"), bg=BG2, fg=MUTED, font=("Segoe UI", 9))
        self.lang_word_lbl.pack(side="left")
        self.sublang_var = tk.StringVar(value=self.cfg.get("sublang", "en"))
        ttk.Entry(a2, textvariable=self.sublang_var, width=10).pack(side="left", padx=(4, 16))
        self.frag_lbl = tk.Label(a2, text=self.t("frag"), bg=BG2, fg=FG, font=("Segoe UI", 9))
        self.frag_lbl.pack(side="left")
        self.frag_var = tk.IntVar(value=self.cfg.get("frag", 8))
        ttk.Spinbox(a2, from_=1, to=32, textvariable=self.frag_var, width=5).pack(side="left", padx=(4, 0))

        a3 = tk.Frame(self.adv_frame, bg=BG2); a3.pack(fill="x", **ap)
        self.cookies_lbl = tk.Label(a3, text=self.t("cookies"), bg=BG2, fg=FG, font=("Segoe UI", 9))
        self.cookies_lbl.pack(side="left")
        cookies_cfg = self.cfg.get("cookies", "none")
        if cookies_cfg == "yok":               # migrate legacy value
            cookies_cfg = "none"
        self.cookies_var = tk.StringVar(value=cookies_cfg)
        ttk.Combobox(a3, textvariable=self.cookies_var, state="readonly", width=10,
                     values=["none", "chrome", "edge", "firefox", "brave", "opera"]).pack(
            side="left", padx=(6, 0))

        a4 = tk.Frame(self.adv_frame, bg=BG2); a4.pack(fill="x", **ap)
        self.tmpl_lbl = tk.Label(a4, text=self.t("tmpl"), bg=BG2, fg=FG, font=("Segoe UI", 9))
        self.tmpl_lbl.pack(side="left")
        self.tmpl_var = tk.StringVar(value=self.cfg.get("tmpl", "%(title)s"))
        ttk.Entry(a4, textvariable=self.tmpl_var, font=("Consolas", 9)).pack(
            side="left", fill="x", expand=True, padx=(6, 0), ipady=2)

        # Download / cancel
        brow = ttk.Frame(r)
        brow.pack(fill="x", pady=(8, 8), **pad)
        self.download_btn = ttk.Button(brow, text=self.t("download"), style="Accent.TButton", command=self._start)
        self.download_btn.pack(side="left", ipadx=14, ipady=6)
        self.cancel_btn = ttk.Button(brow, text=self.t("cancel"), command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0), ipady=6)

        # Progress
        self.progress = ttk.Progressbar(r, style="Horizontal.TProgressbar", maximum=100)
        self.progress.pack(fill="x", pady=(2, 4), **pad)
        self.status_var = tk.StringVar(value=self.t("ready"))
        ttk.Label(r, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w", **pad)

        # Log
        lf = tk.Frame(r, bg=BG2)
        lf.pack(fill="both", expand=True, pady=(8, 6), **pad)
        self.log_box = tk.Text(lf, bg=BG2, fg=FG, bd=0, font=("Consolas", 9), wrap="word",
                               padx=10, pady=8, state="disabled", highlightthickness=0)
        self.log_box.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lf, command=self.log_box.yview)
        sb.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=sb.set)
        self.log_box.tag_config("ok", foreground=OK)
        self.log_box.tag_config("err", foreground=ERR)
        self.log_box.tag_config("muted", foreground=MUTED)

        # Footer: developed by devbgr (clickable link)
        footer = ttk.Frame(r)
        footer.pack(fill="x", pady=(0, 10), **pad)
        inner = ttk.Frame(footer)
        inner.pack(anchor="center")
        ttk.Label(inner, text="developed by ", style="Muted.TLabel").pack(side="left")
        link = tk.Label(inner, text="devbgr", bg=BG, fg=ACCENT, cursor="hand2",
                        font=("Segoe UI", 9, "underline"))
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: webbrowser.open(AUTHOR_URL))
        link.bind("<Enter>", lambda _e: link.config(fg=ACCENT_HOVER))
        link.bind("<Leave>", lambda _e: link.config(fg=ACCENT))

        self._on_mode_change(save=False)

    def _set_icon(self):
        """Use a user-supplied .ico if present, else a generated icon."""
        here = os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(here, "mp3_downloader.ico")
        if os.path.isfile(ico):
            try:
                self.root.iconbitmap(default=ico)
                return
            except Exception:
                pass
        try:
            self._icon = make_icon()          # keep a reference (avoid GC)
            self.root.iconphoto(True, self._icon)
        except Exception:
            pass

    def _center_window(self, w, h):
        """Always open the window in the center of the screen."""
        r = self.root
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        r.geometry(f"{w}x{h}+{x}+{y}")

    def _check(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=BG2, fg=FG, selectcolor=BG,
                              activebackground=BG2, activeforeground=FG, font=("Segoe UI", 9),
                              bd=0, highlightthickness=0)

    def _on_lang_change(self, *_):
        self.lang = LANGUAGES.get(self.lang_display.get(), "en")
        self._retranslate()
        cfg = load_config()                      # persist without touching other fields
        cfg["ui_lang"] = self.lang
        save_config(cfg)

    def _retranslate(self):
        """Re-apply every static label/button for the current language."""
        self.root.title(APP_NAME)
        self.title_lbl.config(text=self.t("title"))
        self.subtitle_lbl.config(text=self.t("subtitle"))
        self.lang_caption.config(text=self.t("language"))
        self.url_lbl.config(text=self.t("url_label"))
        self.folder_lbl.config(text=self.t("folder_label"))
        self.browse_btn.config(text=self.t("browse"))
        self.mode_lbl.config(text=self.t("mode"))
        self.audio_rb.config(text=self.t("audio_mode"))
        self.video_rb.config(text=self.t("video_mode"))
        self.format_lbl.config(text=self.t("format"))
        self.speed_lbl.config(text=self.t("speed_limit"))
        self.playlist_chk.config(text=self.t("playlist"))
        self.meta_chk.config(text=self.t("meta"))
        self.sponsor_chk.config(text=self.t("sponsor"))
        self.subs_chk.config(text=self.t("subs"))
        self.lang_word_lbl.config(text=self.t("lang_word"))
        self.frag_lbl.config(text=self.t("frag"))
        self.cookies_lbl.config(text=self.t("cookies"))
        self.tmpl_lbl.config(text=self.t("tmpl"))
        self.download_btn.config(text=self.t("download"))
        self.cancel_btn.config(text=self.t("cancel"))
        # Texts that also depend on state
        self.adv_btn.config(text=self.t("adv_hide") if self.adv_visible else self.t("adv_show"))
        self.quality_label.config(
            text=self.t("quality_kbps") if self.mode_var.get() == "audio" else self.t("resolution"))
        # Idle preview placeholder (skip if an image is currently shown)
        if self._thumb_img is None:
            self.thumb_label.config(text=self.t("preview_ph") if HAVE_PIL else self.t("preview_pil"))
        # Status line, only while still on the default "Ready." message
        if self.status_var.get() in (I18N["ready"][0], I18N["ready"][1]):
            self.status_var.set(self.t("ready"))

    # ---------------- Actions ----------------
    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.folder_var.get() or os.path.expanduser("~"))
        if d:
            self.folder_var.set(d)

    def _toggle_adv(self):
        self.adv_visible = not self.adv_visible
        if self.adv_visible:
            self.adv_frame.pack(fill="x", padx=18, pady=(0, 6), before=self.download_btn.master)
            self.adv_btn.config(text=self.t("adv_hide"))
        else:
            self.adv_frame.pack_forget()
            self.adv_btn.config(text=self.t("adv_show"))

    def _on_mode_change(self, save=True):
        if self.mode_var.get() == "audio":
            self.quality_label.config(text=self.t("quality_kbps"))
            self.quality_cb.config(values=AUDIO_QUALITIES)
            self.format_cb.config(values=AUDIO_FORMATS)
            if self.quality_var.get() not in AUDIO_QUALITIES:
                self.quality_var.set("320")
            if self.format_var.get() not in AUDIO_FORMATS:
                self.format_var.set("mp3")
        else:
            self.quality_label.config(text=self.t("resolution"))
            self.quality_cb.config(values=VIDEO_QUALITIES)
            self.format_cb.config(values=VIDEO_FORMATS)
            if self.quality_var.get() not in VIDEO_QUALITIES:
                self.quality_var.set("1080")
            if self.format_var.get() not in VIDEO_FORMATS:
                self.format_var.set("mp4")

    def log(self, text, color=None):
        self.msg_queue.put(("log", text, color))

    def _gather_cfg(self):
        return {
            "folder": self.folder_var.get().strip(),
            "mode": self.mode_var.get(),
            "quality": self.quality_var.get(),
            "format": self.format_var.get(),
            "rate": self.rate_var.get().strip(),
            "playlist": self.playlist_var.get(),
            "meta": self.meta_var.get(),
            "sponsor": self.sponsor_var.get(),
            "subs": self.subs_var.get(),
            "sublang": self.sublang_var.get().strip(),
            "frag": int(self.frag_var.get() or 8),
            "cookies": self.cookies_var.get(),
            "tmpl": self.tmpl_var.get().strip() or "%(title)s",
            "ui_lang": self.lang,
        }

    def _start(self):
        url = self.url_var.get().strip()
        c = self._gather_cfg()
        if not url:
            messagebox.showwarning(APP_NAME, self.t("warn_link"))
            return
        if not c["folder"]:
            messagebox.showwarning(APP_NAME, self.t("warn_folder"))
            return
        os.makedirs(c["folder"], exist_ok=True)
        save_config(c)

        self.cancel_flag.clear()
        self._cur_file = None
        self._last_pp = None
        self.download_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0
        self.log(self.t("starting", mode=c["mode"], url=url), MUTED)

        self.worker = threading.Thread(target=self._download_thread, args=(url, c), daemon=True)
        self.worker.start()

    def _cancel(self):
        self.cancel_flag.set()
        self.log(self.t("cancelling"), ERR)
        self.cancel_btn.config(state="disabled")

    # ---------------- yt-dlp hooks ----------------
    def _track_label(self, info):
        """Build a 'track name' from info_dict, with playlist position if any."""
        info = info or {}
        title = info.get("title") or os.path.basename(info.get("filename", "")) or "track"
        idx = info.get("playlist_index")
        n = info.get("n_entries") or info.get("playlist_count")
        if idx and n:
            return f"[{idx}/{n}] {title}"
        if idx:
            return f"[{idx}] {title}"
        return title

    def _progress_hook(self, d):
        if self.cancel_flag.is_set():
            raise yt_dlp.utils.DownloadCancelled()
        if d.get("status") == "downloading":
            # Write the "downloading" line only once per track.
            fn = d.get("filename") or d.get("info_dict", {}).get("filename")
            if fn and fn != self._cur_file:
                self._cur_file = fn
                self.log(self.t("downloading", label=self._track_label(d.get("info_dict"))), None)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            spd = f"{speed/1024/1024:.1f} MB/s" if speed else "-"
            self.msg_queue.put(("progress", pct, self.t("prog_dl", pct=pct, spd=spd, eta=eta)))
        elif d.get("status") == "finished":
            self.log(self.t("downloaded", label=self._track_label(d.get("info_dict"))), OK)
            self.msg_queue.put(("progress", 100, self.t("dl_finished")))
        elif d.get("status") == "error":
            self.log(self.t("failed", label=self._track_label(d.get("info_dict"))), ERR)

    def _postproc_hook(self, d):
        name = d.get("postprocessor", "")
        label = self._track_label(d.get("info_dict"))
        if d.get("status") == "started":
            self.msg_queue.put(("status", self.t("proc_status", name=name)))
            key = (name, label)
            if key != self._last_pp:           # skip duplicate started events
                self._last_pp = key
                self.log(self.t("processing", name=name, label=label), MUTED)
        elif d.get("status") == "finished" and name in ("FFmpegExtractAudio", "Merger"):
            self.log(self.t("ready_track", label=label), OK)

    # ---------------- Thumbnail preview ----------------
    def _on_url_change(self, *_):
        """Debounce: only fetch once the user stops typing/pasting."""
        if self._thumb_after:
            self.root.after_cancel(self._thumb_after)
        self._thumb_after = self.root.after(700, self._request_thumbnail)

    def _request_thumbnail(self):
        self._thumb_after = None
        url = self.url_var.get().strip()
        self._thumb_seq += 1                    # invalidate any in-flight load
        if not url:
            self._show_thumb(None, "")
            self.thumb_label.config(text=self.t("preview_ph"))
            return
        if not HAVE_PIL:
            return
        seq = self._thumb_seq
        self.thumb_title.config(text="")
        self.thumb_label.config(image="", text=self.t("preview_load"))
        threading.Thread(target=self._fetch_thumbnail, args=(url, seq),
                         daemon=True).start()

    def _fetch_thumbnail(self, url, seq):
        """Pull title + thumbnail via yt-dlp (no download), off the UI thread."""
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                    "noplaylist": True, "logger": YtdlpLogger(lambda *a, **k: None)}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False) or {}
            if info.get("entries"):             # playlist -> use first entry
                entries = [e for e in info["entries"] if e]
                info = entries[0] if entries else {}
            title = info.get("title") or ""
            thumb_url = info.get("thumbnail")
            if not thumb_url:
                thumbs = info.get("thumbnails") or []
                thumb_url = thumbs[-1]["url"] if thumbs else None
            im = None
            if thumb_url:
                req = urllib.request.Request(
                    thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                im = self._fit(Image.open(io.BytesIO(data)).convert("RGB"), 256, 144)
            self.msg_queue.put(("thumb", seq, im, title))
        except Exception:
            self.msg_queue.put(("thumb", seq, None, None))

    @staticmethod
    def _fit(im, w, h):
        iw, ih = im.size
        scale = min(w / iw, h / ih)
        return im.resize((max(1, int(iw * scale)), max(1, int(ih * scale))),
                         Image.LANCZOS)

    def _show_thumb(self, im, title):
        if im is None:
            self._thumb_img = None
            self.thumb_label.config(image="", text=self.t("preview_none"))
            self.thumb_title.config(text=title or "")
            return
        self._thumb_img = ImageTk.PhotoImage(im)
        self.thumb_label.config(image=self._thumb_img, text="")
        self.thumb_title.config(text=title or "")

    # ---------------- Download worker ----------------
    def _build_opts(self, c):
        outtmpl = os.path.join(c["folder"], c["tmpl"] + ".%(ext)s")
        opts = {
            "outtmpl": outtmpl,
            "noplaylist": not c["playlist"],
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": False,
            "concurrent_fragment_downloads": c["frag"],
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postproc_hook],
            "logger": YtdlpLogger(self.log),
        }
        if self.ffmpeg_dir:
            opts["ffmpeg_location"] = self.ffmpeg_dir

        # Speed limit (MB/s -> byte/s)
        if c["rate"]:
            try:
                opts["ratelimit"] = float(c["rate"].replace(",", ".")) * 1024 * 1024
            except ValueError:
                pass

        # Cookies ("none"/"yok" = legacy "no cookies" value)
        if c["cookies"] and c["cookies"] not in ("none", "yok"):
            opts["cookiesfrombrowser"] = (c["cookies"],)

        pps = []
        if c["mode"] == "audio":
            opts["format"] = "bestaudio/best"
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": c["format"],
                        "preferredquality": c["quality"]})
            if c["meta"]:
                opts["writethumbnail"] = True
                pps.append({"key": "FFmpegMetadata", "add_metadata": True})
                pps.append({"key": "EmbedThumbnail"})
        else:
            q = c["quality"]
            if q == "Best":
                opts["format"] = "bestvideo+bestaudio/best"
            else:
                opts["format"] = (f"bestvideo[height<={q}]+bestaudio/"
                                  f"best[height<={q}]/best")
            opts["merge_output_format"] = c["format"]
            if c["meta"]:
                pps.append({"key": "FFmpegMetadata", "add_metadata": True})
            if c["subs"]:
                opts["writesubtitles"] = True
                opts["writeautomaticsub"] = True
                opts["subtitleslangs"] = [s.strip() for s in c["sublang"].split(",") if s.strip()]
                pps.append({"key": "FFmpegEmbedSubtitle"})

        if c["sponsor"]:
            pps.append({"key": "SponsorBlock"})
            pps.append({"key": "ModifyChapters",
                        "remove_sponsor_segments": ["sponsor", "selfpromo", "interaction"]})

        opts["postprocessors"] = pps
        return opts

    def _download_thread(self, url, c):
        try:
            opts = self._build_opts(c)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            if self.cancel_flag.is_set():
                self.msg_queue.put(("done", False, self.t("cancelled")))
            else:
                self.msg_queue.put(("done", True, self.t("done", folder=c["folder"])))
        except yt_dlp.utils.DownloadCancelled:
            self.msg_queue.put(("done", False, self.t("cancelled")))
        except Exception as e:
            self.msg_queue.put(("done", False, self.t("error", e=e)))

    # ---------------- Queue ----------------
    def _drain_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._append_log(item[1], item[2])
                elif kind == "progress":
                    self.progress["value"] = item[1]
                    self.status_var.set(item[2])
                elif kind == "status":
                    self.status_var.set(item[1])
                elif kind == "thumb":
                    _, seq, im, title = item
                    if seq == self._thumb_seq:   # ignore stale loads
                        self._show_thumb(im, title)
                elif kind == "done":
                    _, success, msg = item
                    self.status_var.set(msg)
                    self._append_log(msg, OK if success else ERR)
                    if success:
                        self.progress["value"] = 100
                    self.download_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    if success:
                        self._notify_done()
                        self._reset_input()
        except queue.Empty:
            pass
        self.root.after(80, self._drain_queue)

    def _reset_input(self):
        """Clear the link box and preview after a successful download."""
        if self._thumb_after:
            self.root.after_cancel(self._thumb_after)
            self._thumb_after = None
        self._thumb_seq += 1                     # drop any in-flight preview
        self.url_var.set("")                     # also resets preview via trace
        self._show_thumb(None, "")
        self.thumb_label.config(text=self.t("preview_ph"))

    # ---------------- Done notification ----------------
    def _notify_done(self):
        """On a successful finish: a tiny window shake + a short beep."""
        self._shake_window()
        self._play_done_sound()

    def _shake_window(self):
        """Nudge the window left/right a few times so the user notices."""
        try:
            r = self.root
            r.update_idletasks()
            x, y = r.winfo_x(), r.winfo_y()
            offsets = [10, -8, 7, -5, 4, -3, 2, 0]
            for i, dx in enumerate(offsets):
                r.after(i * 35, lambda ox=x + dx: r.geometry(f"+{ox}+{y}"))
            r.after(len(offsets) * 35, lambda: r.geometry(f"+{x}+{y}"))
        except Exception:
            pass

    def _play_done_sound(self):
        """Short notification sound; falls back to the window bell."""
        if sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
                return
            except Exception:
                pass
        try:
            self.root.bell()
        except Exception:
            pass

    def _append_log(self, text, color=None):
        tag = {OK: ("ok",), ERR: ("err",), MUTED: ("muted",)}.get(color, ())
        ts = time.strftime("%H:%M:%S")
        self.log_box.config(state="normal")
        self.log_box.insert("1.0", text + "\n", tag)
        self.log_box.insert("1.0", f"[{ts}] ", ("muted",))
        self.log_box.see("1.0")
        self.log_box.config(state="disabled")


def main():
    set_app_id()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
