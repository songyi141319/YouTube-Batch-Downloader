"""
YouTube 合集批量下载工具 v2
支持批量下载、视频选择、字幕下载、断点续传、失败重试
"""

import os
import sys
import json
import time
import subprocess
import re
import shutil
import platform
import threading
from pathlib import Path
from datetime import datetime
from video_selector_dialog import VideoSelectorDialog
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ── 平台适配 ──────────────────────────────────────────────
IS_MAC = platform.system() == "Darwin"
UI_FONT = "PingFang SC" if IS_MAC else "Microsoft YaHei UI"
MONO_FONT = "SF Mono" if IS_MAC else "Consolas"

def _find_python():
    if IS_MAC:
        found = shutil.which("python3") or shutil.which("python")
        return found or sys.executable
    for p in [r"C:\Python314\python.exe", r"C:\Python313\python.exe"]:
        if os.path.exists(p):
            return p
    found = shutil.which("python3") or shutil.which("python")
    return found or sys.executable

PYTHON_PATH = _find_python()
BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube视频合集")
MAX_RETRIES = 3
RETRY_DELAY = 5

# ── 配色方案（主色 / 副色） ───────────────────────────────
class Theme:
    # 主色：深靛蓝
    PRIMARY = "#1A1A2E"
    PRIMARY_LIGHT = "#16213E"
    # 副色：琥珀金
    ACCENT = "#E2B714"
    ACCENT_HOVER = "#F0C830"

    BG = "#FAFAFA"
    CARD = "#FFFFFF"
    CARD_BORDER = "#E8E8ED"
    TEXT = "#1D1D1F"
    TEXT_SEC = "#86868B"
    TEXT_HINT = "#AEAEB2"
    SUCCESS = "#34C759"
    ERROR = "#FF3B30"
    WARNING = "#FF9500"

    LOG_BG = "#1A1A2E"
    LOG_FG = "#E5E5EA"
    LOG_INFO = "#64D2FF"
    LOG_DETAIL = "#A2AAAD"
    LOG_SUCCESS = "#30D158"
    LOG_ERROR = "#FF453A"
    LOG_WARN = "#FFD60A"

    BTN_RADIUS = 8


class YouTubeBatchDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 合集批量下载工具")
        self.root.geometry("980x820")
        self.root.minsize(800, 650)
        self.root.configure(bg=Theme.BG)

        if IS_MAC:
            self.root.createcommand('tk::mac::Quit', self.root.destroy)

        self.playlists = []
        self.current_playlist_index = 0
        self.is_downloading = False
        self.download_thread = None
        self.failed_items = []
        self.download_subtitles = tk.BooleanVar(value=False)
        self.error_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error_log.txt")

        self._setup_styles()
        self._build_ui()

    # ── ttk 样式 ──────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam" if not IS_MAC else "aqua")

        s.configure("Card.TFrame", background=Theme.CARD)
        s.configure("BG.TFrame", background=Theme.BG)

        # 进度条
        s.configure("Accent.Horizontal.TProgressbar",
                     troughcolor=Theme.CARD_BORDER,
                     background=Theme.ACCENT,
                     lightcolor=Theme.ACCENT,
                     darkcolor=Theme.ACCENT,
                     bordercolor=Theme.CARD_BORDER)

    # ── 圆角按钮工厂 ─────────────────────────────────────
    def _make_btn(self, parent, text, cmd, style="primary", **kw):
        colors = {
            "primary":  (Theme.PRIMARY, "#FFFFFF"),
            "accent":   (Theme.ACCENT, Theme.PRIMARY),
            "success":  (Theme.SUCCESS, "#FFFFFF"),
            "danger":   (Theme.ERROR, "#FFFFFF"),
            "ghost":    (Theme.CARD_BORDER, Theme.TEXT),
            "donate":   ("#FF2D55", "#FFFFFF"),
        }
        bg, fg = colors.get(style, colors["primary"])
        btn = tk.Button(
            parent, text=text, command=cmd,
            font=(UI_FONT, 12, "bold") if style in ("primary", "accent") else (UI_FONT, 11),
            bg=bg, fg=fg,
            activebackground=bg, activeforeground=fg,
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=6,
            highlightthickness=0, bd=0,
            **kw,
        )
        return btn

    # ── 区域标题 ──────────────────────────────────────────
    def _section_label(self, parent, text):
        lbl = tk.Label(parent, text=text,
                       font=(UI_FONT, 13, "bold"),
                       bg=Theme.BG, fg=Theme.TEXT, anchor="w")
        lbl.pack(fill=tk.X, padx=4, pady=(12, 6))
        return lbl

    # ── 卡片容器 ──────────────────────────────────────────
    def _card(self, parent, **kw):
        outer = tk.Frame(parent, bg=Theme.CARD_BORDER,
                         highlightthickness=0, bd=0)
        inner = tk.Frame(outer, bg=Theme.CARD, padx=14, pady=10, **kw)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        return outer, inner

    # ── 主界面 ────────────────────────────────────────────
    def _build_ui(self):
        # ─── 顶栏 ────────────────────────────────────────
        header = tk.Frame(self.root, bg=Theme.PRIMARY, height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="YouTube 合集批量下载工具",
                 font=(UI_FONT, 17, "bold"),
                 bg=Theme.PRIMARY, fg="#FFFFFF").pack(side=tk.LEFT, padx=24, pady=14)

        donate_btn = self._make_btn(header, "打赏支持", self.show_donate_dialog, style="donate")
        donate_btn.pack(side=tk.RIGHT, padx=24, pady=12)

        # 金色装饰线
        tk.Frame(self.root, bg=Theme.ACCENT, height=3).pack(fill=tk.X)

        # ─── 滚动主区域 ──────────────────────────────────
        container = tk.Frame(self.root, bg=Theme.BG)
        container.pack(fill=tk.BOTH, expand=True, padx=24, pady=0)

        # ═══ 1. 链接输入 ═══════════════════════════════
        self._section_label(container, "播放列表链接")

        card_out, card_in = self._card(container)
        card_out.pack(fill=tk.X, pady=(0, 4))

        self.url_text = tk.Text(
            card_in, font=(UI_FONT, 12), height=5,
            bg=Theme.CARD, fg=Theme.TEXT,
            insertbackground=Theme.TEXT,
            relief=tk.FLAT, wrap=tk.WORD,
            highlightthickness=0, bd=0,
        )
        self.url_text.pack(fill=tk.BOTH, expand=True)
        self._set_placeholder()
        self.url_text.bind("<FocusIn>", self.on_url_focus_in)
        self.url_text.bind("<FocusOut>", self.on_url_focus_out)

        # ─── 按钮行 ──────────────────────────────────────
        btn_row = tk.Frame(container, bg=Theme.BG)
        btn_row.pack(fill=tk.X, pady=(6, 4))

        self.parse_btn = self._make_btn(btn_row, "解析合集", self.parse_all_playlists, "primary")
        self.parse_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.select_btn = self._make_btn(btn_row, "挑选视频", self.select_videos_from_playlists, "accent", state=tk.DISABLED)
        self.select_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.direct_download_btn = self._make_btn(btn_row, "直接下载", self.direct_download, "ghost")
        self.direct_download_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.download_btn = self._make_btn(btn_row, "开始批量下载", self.start_batch_download, "success", state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._make_btn(btn_row, "清空", self.clear_urls, "ghost").pack(side=tk.LEFT, padx=(0, 8))

        paste_btn = self._make_btn(btn_row, "粘贴", self.paste_from_clipboard, "ghost")
        paste_btn.pack(side=tk.RIGHT)

        # ─── 保存位置 & 字幕 ─────────────────────────────
        opt_row = tk.Frame(container, bg=Theme.BG)
        opt_row.pack(fill=tk.X, pady=(2, 4))

        tk.Label(opt_row, text="保存位置：", font=(UI_FONT, 11),
                 bg=Theme.BG, fg=Theme.TEXT_SEC).pack(side=tk.LEFT)

        self.dir_label = tk.Label(opt_row, text=BASE_DOWNLOAD_DIR,
                                  font=(UI_FONT, 11), bg=Theme.BG,
                                  fg=Theme.TEXT, anchor="w")
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))

        self._make_btn(opt_row, "更改", self.change_directory, "ghost").pack(side=tk.LEFT)

        sub_row = tk.Frame(container, bg=Theme.BG)
        sub_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(sub_row, text="同时下载字幕（中英文 SRT）",
                         variable=self.download_subtitles).pack(side=tk.LEFT)

        # ═══ 2. 合集列表 ═══════════════════════════════
        self._section_label(container, "待下载合集")

        card_out2, card_in2 = self._card(container)
        card_out2.pack(fill=tk.X, pady=(0, 4))

        scrollbar = tk.Scrollbar(card_in2)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.playlist_listbox = tk.Listbox(
            card_in2, font=(UI_FONT, 11), height=4,
            bg=Theme.CARD, fg=Theme.TEXT,
            selectbackground=Theme.ACCENT,
            selectforeground=Theme.PRIMARY,
            relief=tk.FLAT, highlightthickness=0, bd=0,
            yscrollcommand=scrollbar.set,
        )
        self.playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.playlist_listbox.yview)

        # ═══ 3. 日志 ═══════════════════════════════════
        self._section_label(container, "下载日志")

        log_outer = tk.Frame(container, bg=Theme.PRIMARY, highlightthickness=0, bd=0)
        log_outer.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.log_text = scrolledtext.ScrolledText(
            log_outer, font=(MONO_FONT, 11), height=10,
            wrap=tk.WORD, relief=tk.FLAT,
            bg=Theme.LOG_BG, fg=Theme.LOG_FG,
            insertbackground=Theme.LOG_FG,
            state=tk.DISABLED, highlightthickness=0, bd=8,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO",    foreground=Theme.LOG_INFO)
        self.log_text.tag_config("WARN",    foreground=Theme.LOG_WARN)
        self.log_text.tag_config("ERROR",   foreground=Theme.LOG_ERROR)
        self.log_text.tag_config("SUCCESS", foreground=Theme.LOG_SUCCESS)
        self.log_text.tag_config("DETAIL",  foreground=Theme.LOG_DETAIL)

        # ═══ 4. 进度 ═══════════════════════════════════
        prog_frame = tk.Frame(container, bg=Theme.BG)
        prog_frame.pack(fill=tk.X, pady=(6, 4))

        self.progress_label = tk.Label(prog_frame, text="准备就绪",
                                        font=(UI_FONT, 11),
                                        bg=Theme.BG, fg=Theme.TEXT_SEC,
                                        anchor="w")
        self.progress_label.pack(fill=tk.X, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(
            prog_frame, style="Accent.Horizontal.TProgressbar",
            mode="determinate", length=300,
        )
        self.progress_bar.pack(fill=tk.X)

        # ═══ 5. 底栏按钮 ═══════════════════════════════
        bottom = tk.Frame(container, bg=Theme.BG)
        bottom.pack(fill=tk.X, pady=(8, 12))

        self.retry_btn = self._make_btn(bottom, "重试失败", self.retry_failed, "accent", state=tk.DISABLED)
        self.retry_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = self._make_btn(bottom, "停止下载", self.stop_download, "danger")
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))

    # ── 占位文字 ──────────────────────────────────────────
    def _set_placeholder(self):
        self.url_text.insert("1.0",
            "在此粘贴播放列表链接，每行一个\n"
            "例如：https://www.youtube.com/playlist?list=...")
        self.url_text.config(fg=Theme.TEXT_HINT)

    def on_url_focus_in(self, event):
        if self.url_text.get("1.0", tk.END).strip().startswith("在此粘贴"):
            self.url_text.delete("1.0", tk.END)
            self.url_text.config(fg=Theme.TEXT)

    def on_url_focus_out(self, event):
        if not self.url_text.get("1.0", tk.END).strip():
            self._set_placeholder()

    # ── 日志 ──────────────────────────────────────────────
    def log(self, message, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, entry, level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        if level in ("ERROR", "WARN"):
            try:
                with open(self.error_log_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {message}\n")
            except Exception:
                pass

    # ── 工具方法 ──────────────────────────────────────────
    def change_directory(self):
        global BASE_DOWNLOAD_DIR
        d = filedialog.askdirectory(initialdir=BASE_DOWNLOAD_DIR)
        if d:
            BASE_DOWNLOAD_DIR = d
            self.dir_label.config(text=d)
            self.log(f"保存位置已更改为: {d}", "INFO")

    def clear_urls(self):
        self.url_text.delete("1.0", tk.END)
        self._set_placeholder()
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []

    def paste_from_clipboard(self):
        try:
            clip = self.root.clipboard_get()
            if clip:
                self.url_text.delete("1.0", tk.END)
                self.url_text.config(fg=Theme.TEXT)
                self.url_text.insert("1.0", clip)
                self.log("已粘贴剪贴板内容", "SUCCESS")
            else:
                self.log("剪贴板为空", "WARN")
        except Exception as e:
            self.log(f"粘贴失败: {e}", "ERROR")

    @staticmethod
    def sanitize_filename(name):
        name = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
        return name[:200] if len(name) > 200 else name

    # ── 解析 ──────────────────────────────────────────────
    def parse_all_playlists(self):
        urls_text = self.url_text.get("1.0", tk.END).strip()
        if not urls_text or urls_text.startswith("在此粘贴"):
            messagebox.showwarning("提示", "请输入至少一个播放列表链接")
            return
        urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("提示", "未找到有效链接")
            return

        self.log(f"开始解析 {len(urls)} 个播放列表...", "INFO")
        self.parse_btn.config(state=tk.DISABLED, text="解析中...")
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []

        def _thread():
            # 确保 yt-dlp 已安装
            r = subprocess.run([PYTHON_PATH, "-m", "pip", "show", "yt-dlp"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                self.log("正在安装 yt-dlp...", "WARN")
                subprocess.run([PYTHON_PATH, "-m", "pip", "install", "yt-dlp"],
                               capture_output=True, text=True)

            ok = 0
            for i, url in enumerate(urls, 1):
                self.log(f"[{i}/{len(urls)}] 正在解析: {url[:60]}...", "INFO")
                try:
                    cmd = [PYTHON_PATH, "-m", "yt_dlp",
                           "--dump-single-json", "--flat-playlist", url]
                    res = subprocess.run(cmd, capture_output=True, text=True,
                                         encoding="utf-8", timeout=30)
                    if res.returncode != 0:
                        self.log(f"解析失败: {url[:50]}...", "ERROR")
                        self.log(f"  {(res.stderr or '')[:200]}", "ERROR")
                        continue

                    data = json.loads(res.stdout)
                    title = self.sanitize_filename(data.get("title", f"Playlist_{i}"))
                    videos = []
                    for vi, entry in enumerate(data.get("entries", []), 1):
                        if entry:
                            videos.append({
                                "id": entry.get("id"),
                                "title": entry.get("title", f"Video_{vi}"),
                                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "playlist_index": vi,
                            })

                    info = {"title": title, "url": url, "videos": videos,
                            "folder": os.path.join(BASE_DOWNLOAD_DIR, title)}
                    self.playlists.append(info)
                    txt = f"[{len(videos)} 个视频] {title}"
                    self.root.after(0, lambda t=txt: self.playlist_listbox.insert(tk.END, t))
                    self.log(f"解析成功: {title} ({len(videos)} 个视频)", "SUCCESS")
                    ok += 1
                except Exception as e:
                    self.log(f"解析出错: {e}", "ERROR")

            self.log(f"解析完成 {ok}/{len(urls)}", "SUCCESS")
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL, text="解析合集"))
            if self.playlists:
                self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.select_btn.config(state=tk.NORMAL))

        threading.Thread(target=_thread, daemon=True).start()

    # ── 视频选择 ──────────────────────────────────────────
    def select_videos_from_playlists(self):
        if not self.playlists:
            messagebox.showwarning("提示", "请先解析播放列表")
            return
        self.log("开始选择视频...", "INFO")
        for pl in self.playlists:
            dialog = VideoSelectorDialog(self.root, pl)
            sel = dialog.show()
            if sel is None:
                self.log(f"取消选择: {pl['title']}", "WARN")
                continue
            pl['videos'] = sel
            self.log(f"{pl['title']}: 已选 {len(sel)} 个视频", "SUCCESS")

        self.playlist_listbox.delete(0, tk.END)
        for pl in self.playlists:
            self.playlist_listbox.insert(tk.END, f"[{len(pl['videos'])} 个视频] {pl['title']}")
        self.log("视频选择完成", "SUCCESS")
        self.download_btn.config(state=tk.NORMAL)

    # ── 直接下载 ──────────────────────────────────────────
    def direct_download(self):
        urls = [u.strip() for u in self.url_text.get("1.0", tk.END).strip().split("\n")
                if u.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("提示", "请先输入链接")
            return

        self.log("直接下载模式", "INFO")
        for btn in (self.parse_btn, self.select_btn, self.download_btn, self.direct_download_btn):
            btn.config(state=tk.DISABLED)

        def _thread():
            for idx, url in enumerate(urls, 1):
                self.root.after(0, lambda i=idx, t=len(urls): self.progress_label.config(text=f"下载: {i}/{t}"))
                self.root.after(0, lambda i=idx, t=len(urls): self.progress_bar.config(value=(i/t)*100))
                self.root.after(0, lambda u=url: self.log(f"\n{'='*50}", "INFO"))
                self.root.after(0, lambda i=idx, t=len(urls): self.log(f"[{i}/{t}] 正在下载播放列表", "INFO"))
                self.root.after(0, lambda u=url: self.log(f"  URL: {u}", "DETAIL"))

                cmd = [
                    PYTHON_PATH, "-m", "yt_dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                    "--merge-output-format", "mp4",
                    "-o", os.path.join(BASE_DOWNLOAD_DIR, "%(playlist_title)s", "%(playlist_index)02d_%(title)s.%(ext)s"),
                    "--yes-playlist", "--newline", url,
                ]
                if self.download_subtitles.get():
                    cmd.extend(["--write-sub", "--write-auto-sub",
                                "--sub-lang", "zh-Hans,zh-Hant,en", "--convert-subs", "srt"])

                # 先获取播放列表信息
                try:
                    info_cmd = [PYTHON_PATH, "-m", "yt_dlp", "--flat-playlist", "--dump-single-json", url]
                    info_res = subprocess.run(info_cmd, capture_output=True, text=True,
                                              encoding="utf-8", errors="replace", timeout=30)
                    if info_res.returncode == 0:
                        pi = json.loads(info_res.stdout)
                        self.root.after(0, lambda t=pi.get("title", "?"): self.log(f"  播放列表: {t}", "DETAIL"))
                        self.root.after(0, lambda c=len(pi.get("entries", [])): self.log(f"  视频数: {c}", "DETAIL"))
                except Exception:
                    pass

                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, encoding="utf-8", errors="replace")
                    last_p = -1
                    for line in proc.stdout:
                        line = line.strip()
                        if not line:
                            continue
                        if "[download]" in line:
                            if "has already been downloaded" in line:
                                self.root.after(0, lambda: self.log("  已存在，跳过", "INFO"))
                            elif "Downloading item" in line or "Downloading video" in line:
                                m = re.search(r'(\d+) of (\d+)', line)
                                if m:
                                    self.root.after(0, lambda a=m.group(1), b=m.group(2): self.log(f"\n  下载第 {a}/{b} 个视频", "INFO"))
                            elif "Destination:" in line:
                                bn = os.path.basename(line.split("Destination:")[-1].strip())
                                if bn:
                                    self.root.after(0, lambda f=bn: self.log(f"  文件: {f}", "DETAIL"))
                            elif "%" in line and "ETA" in line:
                                m = re.search(r'(\d+\.\d+)%', line)
                                if m:
                                    p = int(float(m.group(1)))
                                    t = p // 10
                                    if t > last_p:
                                        sm = re.search(r'at\s+([\d\.]+\w+/s)', line)
                                        em = re.search(r'ETA\s+([\d:]+)', line)
                                        self.root.after(0, lambda p=p, s=sm and sm.group(1) or "?", e=em and em.group(1) or "?": self.log(f"  {p}% | {s} | ETA {e}", "DETAIL"))
                                        last_p = t
                            elif "100%" in line:
                                self.root.after(0, lambda: self.log("  下载完成", "SUCCESS"))
                        elif "[Merger]" in line:
                            self.root.after(0, lambda: self.log("  合并视频和音频...", "DETAIL"))
                        elif "Writing video subtitles" in line:
                            self.root.after(0, lambda: self.log("  下载字幕...", "DETAIL"))

                    proc.wait()
                    if proc.returncode == 0:
                        self.root.after(0, lambda i=idx, t=len(urls): self.log(f"[{i}/{t}] 完成", "SUCCESS"))
                    else:
                        self.root.after(0, lambda i=idx, t=len(urls): self.log(f"[{i}/{t}] 失败", "ERROR"))
                except Exception as e:
                    self.root.after(0, lambda e=str(e): self.log(f"出错: {e[:200]}", "ERROR"))

            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.direct_download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.log("直接下载完成", "SUCCESS"))
            self.root.after(0, lambda: self.progress_label.config(text="下载完成"))

        threading.Thread(target=_thread, daemon=True).start()

    # ── 批量下载 ──────────────────────────────────────────
    def start_batch_download(self):
        if not self.playlists:
            messagebox.showwarning("提示", "没有可下载的播放列表")
            return
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.parse_btn.config(state=tk.DISABLED)
        self.failed_items = []
        total = sum(len(p["videos"]) for p in self.playlists)
        self.log(f"开始批量下载 {len(self.playlists)} 个合集，共 {total} 个视频", "INFO")

        def _thread():
            ok = fail = done = 0
            for pi, pl in enumerate(self.playlists, 1):
                if not self.is_downloading:
                    self.log("已停止", "WARN"); break
                self.log(f"\n{'='*50}", "INFO")
                self.log(f"[{pi}/{len(self.playlists)}] {pl['title']}", "INFO")
                os.makedirs(pl["folder"], exist_ok=True)
                pf = os.path.join(pl["folder"], ".download_progress.json")
                pd = {}
                if os.path.exists(pf):
                    with open(pf, "r", encoding="utf-8", errors="replace") as f:
                        pd = json.load(f)
                for vi, v in enumerate(pl["videos"], 1):
                    if not self.is_downloading:
                        break
                    done += 1
                    self.root.after(0, lambda p=(done/total)*100: self.progress_bar.config(value=p))
                    self.root.after(0, lambda a=pi, b=len(self.playlists), c=vi, d=len(pl["videos"]), e=done, f=total:
                        self.progress_label.config(text=f"合集 {a}/{b} | 视频 {c}/{d} | 总进度 {e}/{f}"))
                    if self.download_video(v, pl["folder"], pd, pf):
                        ok += 1
                    else:
                        fail += 1
                        self.failed_items.append({"playlist": pl, "video": v})

            self.log(f"\n{'='*50}", "INFO")
            self.log(f"批量下载完成 | 成功: {ok} | 失败: {fail}", "SUCCESS")
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            if fail > 0:
                self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))

        self.download_thread = threading.Thread(target=_thread, daemon=True)
        self.download_thread.start()

    # ── 下载单个视频 ──────────────────────────────────────
    def download_video(self, video, folder, progress_data, progress_file, retry_count=0):
        vid = video["id"]
        title = video["title"]
        idx = video.get("playlist_index", 0)

        if vid in progress_data and progress_data[vid].get("completed"):
            self.log(f"已下载，跳过: [{idx:02d}] {title}", "INFO")
            return True

        self.log(f"开始下载 [{idx:02d}] {title}", "INFO")
        try:
            # 获取信息
            try:
                info_res = subprocess.run(
                    [PYTHON_PATH, "-m", "yt_dlp", "--dump-single-json", video["url"]],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                if info_res.returncode == 0:
                    vi = json.loads(info_res.stdout)
                    fmts = vi.get("formats", [])
                    vf = [f for f in fmts if f.get("vcodec") != "none"]
                    af = [f for f in fmts if f.get("acodec") != "none" and f.get("vcodec") == "none"]
                    if vf:
                        bv = max(vf, key=lambda x: (x.get("height") or 0))
                        self.log(f"  画质: {bv.get('height', '?')}p", "DETAIL")
            except Exception:
                pass

            # 下载
            out = os.path.join(folder, f"{idx:02d}_%(title)s.%(ext)s")
            cmd = [
                PYTHON_PATH, "-m", "yt_dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", out, "--no-playlist", "--newline", video["url"],
            ]
            if self.download_subtitles.get():
                sub_dir = os.path.join(folder, "字幕")
                os.makedirs(sub_dir, exist_ok=True)
                sub_tpl = os.path.join(sub_dir, f"{idx:02d}_%(title)s.%(ext)s")
                cmd.extend(["--write-sub", "--write-auto-sub",
                            "--sub-lang", "zh-Hans,zh-Hant,en",
                            "--convert-subs", "srt", "-o", f"subtitle:{sub_tpl}"])

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            last_p = -1
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if "[download]" in line and "%" in line:
                    m = re.search(r'(\d+\.\d+)%', line)
                    if m:
                        p = int(float(m.group(1)))
                        t = p // 10
                        if t > last_p:
                            self.log(f"  进度: {p}%", "DETAIL")
                            last_p = t
                elif "[Merger]" in line:
                    self.log("  合并中...", "DETAIL")

            proc.wait()
            if proc.returncode == 0:
                self.log(f"下载完成: [{idx:02d}] {title}", "SUCCESS")
                progress_data[vid] = {"title": title, "completed": True,
                                      "timestamp": datetime.now().isoformat()}
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                return True
            else:
                raise Exception(f"yt-dlp 返回错误代码 {proc.returncode}")

        except Exception as e:
            if retry_count < MAX_RETRIES:
                self.log(f"失败，{RETRY_DELAY}s 后重试 ({retry_count+1}/{MAX_RETRIES})", "WARN")
                time.sleep(RETRY_DELAY)
                return self.download_video(video, folder, progress_data, progress_file, retry_count+1)
            else:
                self.log(f"下载失败（已重试{MAX_RETRIES}次）: {title}", "ERROR")
                progress_data[vid] = {"title": title, "completed": False,
                                      "error": str(e)[:200], "timestamp": datetime.now().isoformat()}
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                return False

    # ── 重试 ──────────────────────────────────────────────
    def retry_failed(self):
        if not self.failed_items:
            messagebox.showinfo("提示", "没有失败的视频")
            return
        self.log(f"重试 {len(self.failed_items)} 个失败视频", "INFO")
        self.is_downloading = True
        self.retry_btn.config(state=tk.DISABLED)
        self.download_btn.config(state=tk.DISABLED)

        def _thread():
            ok = fail = 0
            new_failed = []
            for i, item in enumerate(self.failed_items, 1):
                if not self.is_downloading:
                    break
                pl, v = item["playlist"], item["video"]
                self.root.after(0, lambda p=(i/len(self.failed_items))*100: self.progress_bar.config(value=p))
                pf = os.path.join(pl["folder"], ".download_progress.json")
                pd = {}
                if os.path.exists(pf):
                    with open(pf, "r", encoding="utf-8", errors="replace") as f:
                        pd = json.load(f)
                if v["id"] in pd:
                    del pd[v["id"]]
                if self.download_video(v, pl["folder"], pd, pf):
                    ok += 1
                else:
                    fail += 1
                    new_failed.append(item)
            self.failed_items = new_failed
            self.log(f"重试完成 | 成功: {ok} | 失败: {fail}", "SUCCESS")
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            if fail > 0:
                self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))

        threading.Thread(target=_thread, daemon=True).start()

    # ── 停止 ──────────────────────────────────────────────
    def stop_download(self):
        self.is_downloading = False
        self.log("正在停止下载...", "WARN")

    # ── 打赏 ──────────────────────────────────────────────
    def show_donate_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("打赏支持")
        dlg.geometry("520x560")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=Theme.BG)

        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() // 2) - 260
        y = (dlg.winfo_screenheight() // 2) - 280
        dlg.geometry(f"+{x}+{y}")

        # 标题
        hdr = tk.Frame(dlg, bg=Theme.PRIMARY, height=56)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="感谢您的支持", font=(UI_FONT, 16, "bold"),
                 bg=Theme.PRIMARY, fg="#FFFFFF").pack(pady=14)
        tk.Frame(dlg, bg=Theme.ACCENT, height=3).pack(fill=tk.X)

        body = tk.Frame(dlg, bg=Theme.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        tk.Label(body, text="如果这个工具对您有帮助，欢迎扫码打赏！",
                 font=(UI_FONT, 12), bg=Theme.BG, fg=Theme.TEXT_SEC,
                 wraplength=420).pack(pady=(0, 20))

        qr_row = tk.Frame(body, bg=Theme.BG)
        qr_row.pack(fill=tk.X, pady=(0, 16))

        qr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donate_qr")

        for label_text, color, filename in [
            ("微信支付", "#07C160", "wechat.png"),
            ("支付宝", "#1677FF", "alipay.png"),
        ]:
            col = tk.Frame(qr_row, bg=Theme.BG)
            col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6)

            tk.Label(col, text=label_text, font=(UI_FONT, 12, "bold"),
                     bg=Theme.BG, fg=color).pack(pady=(0, 8))

            path = os.path.join(qr_dir, filename)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    w = img.width()
                    if w > 180:
                        factor = max(w // 180, 1)
                        img = img.subsample(factor)
                    lbl = tk.Label(col, image=img, bg=Theme.BG)
                    lbl.image = img
                    lbl.pack()
                except Exception:
                    tk.Label(col, text=f"加载失败\n{filename}",
                             font=(UI_FONT, 10), bg=Theme.BG, fg=Theme.TEXT_HINT,
                             height=8).pack()
            else:
                tk.Label(col, text=f"未找到\n{filename}",
                         font=(UI_FONT, 10), bg=Theme.BG, fg=Theme.TEXT_HINT,
                         height=8).pack()

        tk.Label(body, text="金额随意，您的支持是最大的动力！",
                 font=(UI_FONT, 11), bg=Theme.BG, fg=Theme.TEXT_HINT).pack(pady=(8, 16))

        self._make_btn(body, "关闭", dlg.destroy, "ghost").pack()


def main():
    root = tk.Tk()
    YouTubeBatchDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
