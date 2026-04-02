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
from datetime import datetime
from video_selector_dialog import VideoSelectorDialog
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ── 平台适配 ─────────────────────────────────────────────
IS_MAC = platform.system() == "Darwin"
UI_FONT = "PingFang SC" if IS_MAC else "Microsoft YaHei UI"
MONO_FONT = "Menlo" if IS_MAC else "Consolas"

def _find_python():
    if IS_MAC:
        return shutil.which("python3") or shutil.which("python") or sys.executable
    for p in [r"C:\Python314\python.exe", r"C:\Python313\python.exe"]:
        if os.path.exists(p):
            return p
    return shutil.which("python3") or shutil.which("python") or sys.executable

PYTHON_PATH = _find_python()
BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube视频合集")
MAX_RETRIES = 3
RETRY_DELAY = 5


class YouTubeBatchDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 合集批量下载工具")
        self.root.geometry("900x750")
        self.root.minsize(700, 550)

        if IS_MAC:
            try:
                self.root.createcommand('tk::mac::Quit', self.root.destroy)
            except Exception:
                pass

        self.playlists = []
        self.is_downloading = False
        self.download_thread = None
        self.failed_items = []
        self.download_subtitles = tk.BooleanVar(value=False)
        self.use_proxy = tk.BooleanVar(value=False)
        self.proxy_host = tk.StringVar(value="127.0.0.1")
        self.proxy_port = tk.StringVar(value="7897")
        self.error_log_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "error_log.txt")

        self._build_ui()

    def _build_ui(self):
        # macOS 使用 aqua 原生主题，Windows 使用 clam
        s = ttk.Style()
        if not IS_MAC:
            s.theme_use("clam")

        pad = {"padx": 16, "pady": 4}

        # ═══ 标题 ════════════════════════════════════════
        title = ttk.Label(self.root, text="YouTube 合集批量下载工具",
                          font=(UI_FONT, 20, "bold"))
        title.pack(pady=(16, 4), **{"padx": 16})

        subtitle = ttk.Label(self.root, text="批量下载 YouTube 播放列表，支持视频选择、字幕下载、断点续传",
                             font=(UI_FONT, 11), foreground="gray")
        subtitle.pack(pady=(0, 12), **{"padx": 16})

        ttk.Separator(self.root).pack(fill=tk.X, padx=16)

        # ─── 主容器 ──────────────────────────────────────
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        # ═══ 1. 链接输入 ════════════════════════════════
        ttk.Label(main, text="播放列表链接", font=(UI_FONT, 13, "bold")).pack(anchor="w", pady=(8, 4))

        url_frame = ttk.Frame(main)
        url_frame.pack(fill=tk.X)

        self.url_text = tk.Text(url_frame, font=(UI_FONT, 12), height=4,
                                wrap=tk.WORD, relief=tk.SUNKEN, bd=1)
        url_sb = ttk.Scrollbar(url_frame, orient=tk.VERTICAL, command=self.url_text.yview)
        self.url_text.configure(yscrollcommand=url_sb.set)
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        url_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._set_placeholder()
        self.url_text.bind("<FocusIn>", self._on_focus_in)
        self.url_text.bind("<FocusOut>", self._on_focus_out)

        # ─── 按钮行 ──────────────────────────────────────
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(8, 4))

        self.parse_btn = ttk.Button(btn_row, text="解析合集", command=self.parse_all_playlists)
        self.parse_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.select_btn = ttk.Button(btn_row, text="挑选视频", command=self.select_videos_from_playlists, state=tk.DISABLED)
        self.select_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.direct_download_btn = ttk.Button(btn_row, text="直接下载", command=self.direct_download)
        self.direct_download_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.download_btn = ttk.Button(btn_row, text="开始批量下载", command=self.start_batch_download, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(btn_row, text="清空", command=self.clear_urls).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="粘贴", command=self.paste_from_clipboard).pack(side=tk.RIGHT)

        # ─── 保存位置 ────────────────────────────────────
        dir_row = ttk.Frame(main)
        dir_row.pack(fill=tk.X, pady=(4, 2))

        ttk.Label(dir_row, text="保存位置：", font=(UI_FONT, 11)).pack(side=tk.LEFT)
        self.dir_label = ttk.Label(dir_row, text=BASE_DOWNLOAD_DIR, font=(UI_FONT, 11), foreground="gray")
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        ttk.Button(dir_row, text="更改", command=self.change_directory).pack(side=tk.RIGHT)

        # ─── 字幕选项 ────────────────────────────────────
        ttk.Checkbutton(main, text="同时下载字幕（中英文 SRT）",
                         variable=self.download_subtitles).pack(anchor="w", pady=(2, 0))

        # ─── 代理设置 ────────────────────────────────────
        proxy_row = ttk.Frame(main)
        proxy_row.pack(fill=tk.X, pady=(2, 4))

        ttk.Checkbutton(proxy_row, text="使用代理",
                         variable=self.use_proxy).pack(side=tk.LEFT)

        ttk.Label(proxy_row, text="  地址：", font=(UI_FONT, 11)).pack(side=tk.LEFT)
        proxy_host_entry = ttk.Entry(proxy_row, textvariable=self.proxy_host, width=14, font=(UI_FONT, 11))
        proxy_host_entry.pack(side=tk.LEFT)

        ttk.Label(proxy_row, text=" 端口：", font=(UI_FONT, 11)).pack(side=tk.LEFT)
        proxy_port_entry = ttk.Entry(proxy_row, textvariable=self.proxy_port, width=6, font=(UI_FONT, 11))
        proxy_port_entry.pack(side=tk.LEFT)

        ttk.Separator(main).pack(fill=tk.X, pady=4)

        # ═══ 2. 合集列表 ════════════════════════════════
        ttk.Label(main, text="待下载合集", font=(UI_FONT, 13, "bold")).pack(anchor="w", pady=(4, 4))

        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.X)

        list_sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.playlist_listbox = tk.Listbox(list_frame, font=(UI_FONT, 11), height=3,
                                           relief=tk.SUNKEN, bd=1,
                                           yscrollcommand=list_sb.set)
        list_sb.config(command=self.playlist_listbox.yview)
        self.playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_sb.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Separator(main).pack(fill=tk.X, pady=4)

        # ═══ 3. 日志 ════════════════════════════════════
        ttk.Label(main, text="下载日志", font=(UI_FONT, 13, "bold")).pack(anchor="w", pady=(4, 4))

        self.log_text = scrolledtext.ScrolledText(
            main, font=(MONO_FONT, 11), height=10, wrap=tk.WORD,
            bg="#1E1E1E", fg="#D4D4D4", insertbackground="#D4D4D4",
            relief=tk.SUNKEN, bd=1, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_text.tag_config("INFO",    foreground="#56B6C2")
        self.log_text.tag_config("WARN",    foreground="#E5C07B")
        self.log_text.tag_config("ERROR",   foreground="#E06C75")
        self.log_text.tag_config("SUCCESS", foreground="#98C379")
        self.log_text.tag_config("DETAIL",  foreground="#ABB2BF")

        # ═══ 4. 进度 ════════════════════════════════════
        prog_frame = ttk.Frame(main)
        prog_frame.pack(fill=tk.X, pady=(6, 2))

        self.progress_label = ttk.Label(prog_frame, text="准备就绪", font=(UI_FONT, 11))
        self.progress_label.pack(fill=tk.X, pady=(0, 4))
        self.progress_bar = ttk.Progressbar(prog_frame, mode="determinate", length=300)
        self.progress_bar.pack(fill=tk.X)

        # ═══ 5. 底栏 ════════════════════════════════════
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(8, 4))

        self.retry_btn = ttk.Button(bottom, text="重试失败", command=self.retry_failed, state=tk.DISABLED)
        self.retry_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.stop_btn = ttk.Button(bottom, text="停止下载", command=self.stop_download)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(bottom, text="打赏支持", command=self.show_donate_dialog).pack(side=tk.RIGHT)

    # ── 占位文字 ──────────────────────────────────────────
    def _set_placeholder(self):
        self.url_text.delete("1.0", tk.END)
        self.url_text.insert("1.0", "在此粘贴播放列表链接，每行一个\n例如：https://www.youtube.com/playlist?list=...")
        self.url_text.config(fg="gray")

    def _on_focus_in(self, e):
        if self.url_text.get("1.0", tk.END).strip().startswith("在此粘贴"):
            self.url_text.delete("1.0", tk.END)
            self.url_text.config(fg="black")

    def _on_focus_out(self, e):
        if not self.url_text.get("1.0", tk.END).strip():
            self._set_placeholder()

    # ── 日志 ──────────────────────────────────────────────
    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        if level in ("ERROR", "WARN"):
            try:
                with open(self.error_log_file, "a", encoding="utf-8", errors="replace") as f:
                    f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [{level}] {msg}\n")
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
        self._set_placeholder()
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []

    def paste_from_clipboard(self):
        try:
            clip = self.root.clipboard_get()
            if clip:
                self.url_text.delete("1.0", tk.END)
                self.url_text.config(fg="black")
                self.url_text.insert("1.0", clip)
                self.log("已粘贴剪贴板内容", "SUCCESS")
        except Exception as e:
            self.log(f"粘贴失败: {e}", "ERROR")

    def _proxy_args(self):
        """返回代理相关的 yt-dlp 参数"""
        if self.use_proxy.get():
            host = self.proxy_host.get().strip() or "127.0.0.1"
            port = self.proxy_port.get().strip() or "7897"
            return ["--proxy", f"http://{host}:{port}"]
        return []

    @staticmethod
    def sanitize_filename(name):
        name = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
        return name[:200]

    # ── 解析 ──────────────────────────────────────────────
    def parse_all_playlists(self):
        txt = self.url_text.get("1.0", tk.END).strip()
        if not txt or txt.startswith("在此粘贴"):
            messagebox.showwarning("提示", "请输入至少一个播放列表链接"); return
        urls = [u.strip() for u in txt.split("\n") if u.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("提示", "未找到有效链接"); return

        self.log(f"开始解析 {len(urls)} 个播放列表...", "INFO")
        self.parse_btn.config(state=tk.DISABLED)
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []

        def _work():
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
                    parse_cmd = [PYTHON_PATH, "-m", "yt_dlp", "--dump-single-json", "--flat-playlist"] + self._proxy_args() + [url]
                    res = subprocess.run(parse_cmd,
                        capture_output=True, text=True, encoding="utf-8", timeout=30)
                    if res.returncode != 0:
                        self.log(f"解析失败: {url[:50]}", "ERROR"); continue
                    data = json.loads(res.stdout)
                    title = self.sanitize_filename(data.get("title", f"Playlist_{i}"))
                    videos = []
                    for vi, e in enumerate(data.get("entries", []), 1):
                        if e:
                            videos.append({"id": e.get("id"), "title": e.get("title", f"Video_{vi}"),
                                "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}",
                                "playlist_index": vi})
                    info = {"title": title, "url": url, "videos": videos,
                            "folder": os.path.join(BASE_DOWNLOAD_DIR, title)}
                    self.playlists.append(info)
                    self.root.after(0, lambda t=f"[{len(videos)} 个视频] {title}": self.playlist_listbox.insert(tk.END, t))
                    self.log(f"解析成功: {title} ({len(videos)} 个视频)", "SUCCESS"); ok += 1
                except Exception as e:
                    self.log(f"解析出错: {e}", "ERROR")
            self.log(f"解析完成 {ok}/{len(urls)}", "SUCCESS")
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            if self.playlists:
                self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.select_btn.config(state=tk.NORMAL))
        threading.Thread(target=_work, daemon=True).start()

    # ── 视频选择 ──────────────────────────────────────────
    def select_videos_from_playlists(self):
        if not self.playlists:
            messagebox.showwarning("提示", "请先解析播放列表"); return
        for pl in self.playlists:
            sel = VideoSelectorDialog(self.root, pl).show()
            if sel is None:
                self.log(f"取消选择: {pl['title']}", "WARN"); continue
            pl['videos'] = sel
            self.log(f"{pl['title']}: 已选 {len(sel)} 个视频", "SUCCESS")
        self.playlist_listbox.delete(0, tk.END)
        for pl in self.playlists:
            self.playlist_listbox.insert(tk.END, f"[{len(pl['videos'])} 个视频] {pl['title']}")
        self.download_btn.config(state=tk.NORMAL)

    # ── 直接下载 ──────────────────────────────────────────
    def direct_download(self):
        urls = [u.strip() for u in self.url_text.get("1.0", tk.END).strip().split("\n") if u.strip().startswith("http")]
        if not urls:
            messagebox.showwarning("提示", "请先输入链接"); return
        self.log("直接下载模式", "INFO")
        for b in (self.parse_btn, self.select_btn, self.download_btn, self.direct_download_btn):
            b.config(state=tk.DISABLED)

        def _work():
            for idx, url in enumerate(urls, 1):
                self.root.after(0, lambda i=idx, t=len(urls): self.progress_label.config(text=f"下载: {i}/{t}"))
                self.root.after(0, lambda i=idx, t=len(urls): self.progress_bar.config(value=(i/t)*100))
                self.log(f"[{idx}/{len(urls)}] {url[:60]}", "INFO")
                cmd = [PYTHON_PATH, "-m", "yt_dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                    "--merge-output-format", "mp4",
                    "-o", os.path.join(BASE_DOWNLOAD_DIR, "%(playlist_title)s", "%(playlist_index)02d_%(title)s.%(ext)s"),
                    "--yes-playlist", "--newline"] + self._proxy_args() + [url]
                if self.download_subtitles.get():
                    cmd.extend(["--write-sub", "--write-auto-sub", "--sub-lang", "zh-Hans,zh-Hant,en", "--convert-subs", "srt"])
                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            text=True, encoding="utf-8", errors="replace")
                    last_p = -1
                    for line in proc.stdout:
                        line = line.strip()
                        if not line: continue
                        if "[download]" in line:
                            if "has already been downloaded" in line:
                                self.root.after(0, lambda: self.log("  已存在，跳过", "INFO"))
                            elif re.search(r'(\d+) of (\d+)', line):
                                m = re.search(r'(\d+) of (\d+)', line)
                                self.root.after(0, lambda a=m.group(1), b=m.group(2): self.log(f"  下载第 {a}/{b} 个视频", "INFO"))
                            elif "%" in line and "ETA" in line:
                                m = re.search(r'(\d+\.\d+)%', line)
                                if m:
                                    p = int(float(m.group(1))); t = p // 10
                                    if t > last_p:
                                        self.root.after(0, lambda p=p: self.log(f"  {p}%", "DETAIL")); last_p = t
                            elif "100%" in line:
                                self.root.after(0, lambda: self.log("  下载完成", "SUCCESS"))
                        elif "[Merger]" in line:
                            self.root.after(0, lambda: self.log("  合并中...", "DETAIL"))
                    proc.wait()
                    lv = "SUCCESS" if proc.returncode == 0 else "ERROR"
                    self.root.after(0, lambda i=idx, t=len(urls), l=lv: self.log(f"[{i}/{t}] {'完成' if l == 'SUCCESS' else '失败'}", l))
                except Exception as e:
                    self.root.after(0, lambda e=str(e): self.log(f"出错: {e[:200]}", "ERROR"))
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.direct_download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.progress_label.config(text="下载完成"))
        threading.Thread(target=_work, daemon=True).start()

    # ── 批量下载 ──────────────────────────────────────────
    def start_batch_download(self):
        if not self.playlists: return
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.parse_btn.config(state=tk.DISABLED)
        self.failed_items = []
        total = sum(len(p["videos"]) for p in self.playlists)
        self.log(f"开始批量下载 {len(self.playlists)} 个合集，共 {total} 个视频", "INFO")

        def _work():
            ok = fail = done = 0
            for pi, pl in enumerate(self.playlists, 1):
                if not self.is_downloading: break
                self.log(f"\n[{pi}/{len(self.playlists)}] {pl['title']}", "INFO")
                os.makedirs(pl["folder"], exist_ok=True)
                pf = os.path.join(pl["folder"], ".download_progress.json")
                pd = {}
                if os.path.exists(pf):
                    with open(pf, "r", encoding="utf-8", errors="replace") as f: pd = json.load(f)
                for vi, v in enumerate(pl["videos"], 1):
                    if not self.is_downloading: break
                    done += 1
                    self.root.after(0, lambda p=(done/total)*100: self.progress_bar.config(value=p))
                    self.root.after(0, lambda a=pi, b=len(self.playlists), c=vi, d=len(pl["videos"]), e=done, f=total:
                        self.progress_label.config(text=f"合集 {a}/{b} | 视频 {c}/{d} | 总进度 {e}/{f}"))
                    if self._dl_video(v, pl["folder"], pd, pf): ok += 1
                    else: fail += 1; self.failed_items.append({"playlist": pl, "video": v})
            self.log(f"\n批量下载完成 | 成功: {ok} | 失败: {fail}", "SUCCESS")
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            if fail > 0: self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))
        self.download_thread = threading.Thread(target=_work, daemon=True)
        self.download_thread.start()

    def _dl_video(self, video, folder, pd, pf, retry=0):
        vid, title, idx = video["id"], video["title"], video.get("playlist_index", 0)
        if vid in pd and pd[vid].get("completed"):
            self.log(f"已下载，跳过: [{idx:02d}] {title}", "INFO"); return True
        self.log(f"下载 [{idx:02d}] {title}", "INFO")
        try:
            out = os.path.join(folder, f"{idx:02d}_%(title)s.%(ext)s")
            cmd = [PYTHON_PATH, "-m", "yt_dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4", "-o", out,
                "--no-playlist", "--newline"] + self._proxy_args() + [video["url"]]
            if self.download_subtitles.get():
                sd = os.path.join(folder, "字幕"); os.makedirs(sd, exist_ok=True)
                st = os.path.join(sd, f"{idx:02d}_%(title)s.%(ext)s")
                cmd.extend(["--write-sub", "--write-auto-sub", "--sub-lang", "zh-Hans,zh-Hant,en",
                            "--convert-subs", "srt", "-o", f"subtitle:{st}"])
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            last_p = -1
            error_lines = []
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                if "[download]" in line and "%" in line:
                    m = re.search(r'(\d+\.\d+)%', line)
                    if m:
                        p = int(float(m.group(1))); t = p // 10
                        if t > last_p: self.log(f"  {p}%", "DETAIL"); last_p = t
                elif "[Merger]" in line:
                    self.log("  合并中...", "DETAIL")
                elif "ERROR" in line or "error" in line.lower():
                    error_lines.append(line)
            proc.wait()
            if proc.returncode == 0:
                self.log(f"完成: [{idx:02d}] {title}", "SUCCESS")
                pd[vid] = {"title": title, "completed": True, "timestamp": datetime.now().isoformat()}
                with open(pf, "w", encoding="utf-8") as f: json.dump(pd, f, ensure_ascii=False, indent=2)
                return True
            else:
                err_msg = "; ".join(error_lines[-3:]) if error_lines else f"yt-dlp 返回代码 {proc.returncode}"
                # 分析常见错误原因
                hint = ""
                err_lower = err_msg.lower()
                if "urlopen" in err_lower or "connection" in err_lower or "timed out" in err_lower or "ssl" in err_lower:
                    hint = "（网络连接失败，请检查代理设置）"
                elif "private" in err_lower or "unavailable" in err_lower:
                    hint = "（视频不可用或为私有视频）"
                elif "geo" in err_lower or "blocked" in err_lower:
                    hint = "（地区限制）"
                elif "removed" in err_lower or "deleted" in err_lower:
                    hint = "（视频已被删除）"
                raise Exception(f"{err_msg}{hint}")
        except Exception as e:
            if retry < MAX_RETRIES:
                self.log(f"失败，{RETRY_DELAY}s 后重试 ({retry+1}/{MAX_RETRIES}): {str(e)[:150]}", "WARN")
                time.sleep(RETRY_DELAY)
                return self._dl_video(video, folder, pd, pf, retry+1)
            self.log(f"下载失败: {title}", "ERROR")
            self.log(f"  原因: {str(e)[:200]}", "ERROR")
            pd[vid] = {"title": title, "completed": False, "error": str(e)[:200], "timestamp": datetime.now().isoformat()}
            with open(pf, "w", encoding="utf-8") as f: json.dump(pd, f, ensure_ascii=False, indent=2)
            return False

    def retry_failed(self):
        if not self.failed_items: return
        self.is_downloading = True
        self.retry_btn.config(state=tk.DISABLED)
        def _work():
            ok = fail = 0; nf = []
            for i, it in enumerate(self.failed_items, 1):
                if not self.is_downloading: break
                pl, v = it["playlist"], it["video"]
                self.root.after(0, lambda p=(i/len(self.failed_items))*100: self.progress_bar.config(value=p))
                pf = os.path.join(pl["folder"], ".download_progress.json"); pd = {}
                if os.path.exists(pf):
                    with open(pf, "r", encoding="utf-8", errors="replace") as f: pd = json.load(f)
                if v["id"] in pd: del pd[v["id"]]
                if self._dl_video(v, pl["folder"], pd, pf): ok += 1
                else: fail += 1; nf.append(it)
            self.failed_items = nf
            self.log(f"重试完成 | 成功: {ok} | 失败: {fail}", "SUCCESS")
            self.is_downloading = False
            if fail > 0: self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))
        threading.Thread(target=_work, daemon=True).start()

    def stop_download(self):
        self.is_downloading = False
        self.log("正在停止...", "WARN")

    def show_donate_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("打赏支持")
        dlg.geometry("520x520")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.update_idletasks()
        dlg.geometry(f"+{dlg.winfo_screenwidth()//2-260}+{dlg.winfo_screenheight()//2-260}")

        ttk.Label(dlg, text="感谢您的支持！", font=(UI_FONT, 18, "bold")).pack(pady=(20, 4))
        ttk.Label(dlg, text="如果这个工具对您有帮助，欢迎扫码打赏", font=(UI_FONT, 12)).pack(pady=(0, 16))

        qr_row = ttk.Frame(dlg)
        qr_row.pack(padx=30, pady=(0, 12))
        qr_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donate_qr")

        TARGET_SIZE = 200  # 统一目标尺寸

        for label, fn in [("微信支付", "wechat.png"), ("支付宝", "alipay.png")]:
            col = ttk.Frame(qr_row)
            col.pack(side=tk.LEFT, padx=12)
            ttk.Label(col, text=label, font=(UI_FONT, 13, "bold")).pack(pady=(0, 8))
            path = os.path.join(qr_dir, fn)
            if os.path.exists(path):
                try:
                    img = tk.PhotoImage(file=path)
                    # 计算缩放因子，使两张图片统一到 TARGET_SIZE
                    w, h = img.width(), img.height()
                    max_dim = max(w, h)
                    if max_dim > TARGET_SIZE:
                        factor = max(max_dim // TARGET_SIZE, 1)
                        img = img.subsample(factor)
                    # 用固定大小的 Canvas 居中显示，确保对称
                    canvas = tk.Canvas(col, width=TARGET_SIZE, height=TARGET_SIZE,
                                       highlightthickness=0, bd=0)
                    canvas.pack()
                    # 居中放置图片
                    canvas.create_image(TARGET_SIZE // 2, TARGET_SIZE // 2,
                                        image=img, anchor="center")
                    canvas.image = img  # 防止被垃圾回收
                except Exception:
                    ttk.Label(col, text="加载失败").pack()
            else:
                ttk.Label(col, text=f"未找到 {fn}").pack()

        ttk.Label(dlg, text="金额随意，您的支持是最大的动力！", font=(UI_FONT, 11)).pack(pady=(12, 16))
        ttk.Button(dlg, text="关闭", command=dlg.destroy).pack()


def main():
    root = tk.Tk()
    YouTubeBatchDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
