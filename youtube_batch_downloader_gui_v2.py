"""
YouTube 合集批量下载工具 - 图形界面增强版
功能：
1. 批量下载多个合集
2. 自动为每个合集创建文件夹
3. 美观的现代化界面
4. 实时日志显示（自然语言）
5. 下载进度条
6. 手动重试按钮
"""

import os
import sys
import json
import time
import subprocess
import re
import threading
from pathlib import Path
from datetime import datetime
from video_selector_dialog import VideoSelectorDialog
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# 配置
import shutil
import platform

def _ui_font():
    """根据平台选择合适的 UI 字体"""
    _sys = platform.system()
    if _sys == "Darwin":
        return "PingFang SC"
    elif _sys == "Windows":
        return UI_FONT
    return "sans-serif"

UI_FONT = _ui_font()

def _find_python():
    """自动检测 Python 路径"""
    # Windows 特定路径
    win_paths = [r"C:\Python314\python.exe", r"C:\Python313\python.exe"]
    for p in win_paths:
        if os.path.exists(p):
            return p
    # 系统 PATH 中查找
    found = shutil.which("python3") or shutil.which("python")
    return found or sys.executable

PYTHON_PATH = _find_python()
BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube视频合集")
MAX_RETRIES = 3
RETRY_DELAY = 5

class YouTubeBatchDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 合集批量下载工具 v2")
        self.root.geometry("950x800")
        self.root.resizable(True, True)
        
        # 设置主题颜色
        self.bg_color = "#f0f0f0"
        self.primary_color = "#2196F3"
        self.success_color = "#4CAF50"
        self.error_color = "#f44336"
        self.warning_color = "#FF9800"
        
        self.root.configure(bg=self.bg_color)
        
        # 变量
        self.playlists = []  # 存储所有播放列表信息
        self.current_playlist_index = 0
        self.is_downloading = False
        self.download_thread = None
        self.failed_items = []
        self.download_subtitles = tk.BooleanVar(value=False)
        self.error_log_file = os.path.join(os.path.dirname(__file__), "error_log.txt")
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg=self.primary_color, height=60)
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎬 YouTube 合集批量下载工具",
            font=(UI_FONT, 18, "bold"),
            bg=self.primary_color,
            fg="white"
        )
        title_label.pack(pady=15)
        
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # URL 输入区域（批量）
        url_frame = tk.LabelFrame(
            main_frame,
            text="📎 播放列表链接（每行一个，支持批量）",
            font=(UI_FONT, 10, "bold"),
            bg=self.bg_color,
            fg="#333"
        )
        url_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 多行文本输入框
        url_text_frame = tk.Frame(url_frame, bg="white")
        url_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        url_scrollbar = tk.Scrollbar(url_text_frame)
        url_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.url_text = tk.Text(
            url_text_frame,
            font=(UI_FONT, 10),
            relief=tk.FLAT,
            bg="white",
            fg="#333",
            yscrollcommand=url_scrollbar.set,
            height=6,
            wrap=tk.WORD
        )
        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 粘贴按钮
        paste_btn_frame = tk.Frame(url_frame, bg=self.bg_color)
        paste_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Button(
            paste_btn_frame,
            text="📋 一键粘贴",
            font=(UI_FONT, 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.paste_from_clipboard,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT)

        url_scrollbar.config(command=self.url_text.yview)
        
        # 提示文本
        self.url_text.insert("1.0", "请输入播放列表链接，每行一个\n例如：\nhttps://www.youtube.com/playlist?list=...\nhttps://www.youtube.com/playlist?list=...")
        self.url_text.config(fg="#999")
        
        # 绑定焦点事件（清除提示文本）
        self.url_text.bind("<FocusIn>", self.on_url_focus_in)
        self.url_text.bind("<FocusOut>", self.on_url_focus_out)
        
        # 按钮区域
        url_button_frame = tk.Frame(url_frame, bg=self.bg_color)
        url_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.parse_btn = tk.Button(
            url_button_frame,
            text="📋 解析所有合集",
            font=(UI_FONT, 10, "bold"),
            bg=self.primary_color,
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.parse_all_playlists,
            padx=20,
            pady=8
        )
        self.parse_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.select_btn = tk.Button(
            url_button_frame,
            text="🎯 挑选视频",
            font=(UI_FONT, 10, "bold"),
            bg="#FF9800",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.select_videos_from_playlists,
            padx=20,
            pady=8,
            state=tk.DISABLED
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.direct_download_btn = tk.Button(
            url_button_frame,
            text="⚡ 直接下载",
            font=(UI_FONT, 10, "bold"),
            bg="#9C27B0",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.direct_download,
            padx=20,
            pady=8
        )
        self.direct_download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.download_btn = tk.Button(
            url_button_frame,
            text="🚀 开始批量下载",
            font=(UI_FONT, 10, "bold"),
            bg="#4CAF50",
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.start_batch_download,
            padx=20,
            pady=8,
            state=tk.DISABLED
        )
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(
            url_button_frame,
            text="🗑 清空",
            font=(UI_FONT, 10),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.clear_urls,
            padx=15,
            pady=8
        ).pack(side=tk.LEFT)
        
        # 下载目录选择
        dir_frame = tk.Frame(url_frame, bg=self.bg_color)
        dir_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(
            dir_frame,
            text="保存位置:",
            font=(UI_FONT, 9),
            bg=self.bg_color,
            fg="#666"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.dir_label = tk.Label(
            dir_frame,
            text=BASE_DOWNLOAD_DIR,
            font=(UI_FONT, 9),
            bg=self.bg_color,
            fg="#333",
            anchor="w"
        )
        self.dir_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(
            dir_frame,
            text="更改",
            font=(UI_FONT, 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.change_directory,
            padx=15
        ).pack(side=tk.RIGHT)
        
        subtitle_frame = tk.Frame(url_frame, bg=self.bg_color)
        subtitle_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Checkbutton(
            subtitle_frame, text="📝 同时下载字幕（保存到字幕子文件夹）",
            variable=self.download_subtitles, font=(UI_FONT, 9),
            bg=self.bg_color, fg="#333", activebackground=self.bg_color,
            selectcolor="white"
        ).pack(side=tk.LEFT)

        # 合集列表区域
        list_frame = tk.LabelFrame(
            main_frame,
            text="📚 待下载合集列表",
            font=(UI_FONT, 10, "bold"),
            bg=self.bg_color,
            fg="#333"
        )
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 合集列表（带滚动条）
        list_container = tk.Frame(list_frame, bg="white")
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_listbox = tk.Listbox(
            list_container,
            font=(UI_FONT, 9),
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            bg="white",
            fg="#333",
            selectbackground=self.primary_color,
            selectforeground="white",
            height=6
        )
        self.playlist_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.playlist_listbox.yview)
        
        # 日志区域
        log_frame = tk.LabelFrame(
            main_frame,
            text="📋 下载日志",
            font=(UI_FONT, 10, "bold"),
            bg=self.bg_color,
            fg="#333"
        )
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            state=tk.DISABLED,
            height=8
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置日志颜色标签
        self.log_text.tag_config("INFO", foreground="#4EC9B0")
        self.log_text.tag_config("WARN", foreground="#FFA500")
        self.log_text.tag_config("ERROR", foreground="#F44336")
        self.log_text.tag_config("SUCCESS", foreground="#4CAF50")
        self.log_text.tag_config("DETAIL", foreground="#9CDCFE")
        
        # 进度条
        progress_frame = tk.Frame(main_frame, bg=self.bg_color)
        progress_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.progress_label = tk.Label(
            progress_frame,
            text="准备就绪",
            font=(UI_FONT, 9),
            bg=self.bg_color,
            fg="#666"
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("green.Horizontal.TProgressbar",
                       troughcolor='#e0e0e0', bordercolor='#4CAF50',
                       background='#4CAF50', lightcolor='#4CAF50', darkcolor='#4CAF50')
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, style="green.Horizontal.TProgressbar",
            mode='determinate', length=300
        )
        self.progress_bar.pack(fill=tk.X)
        
        retry_frame = tk.Frame(main_frame, bg=self.bg_color)
        retry_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.retry_btn = tk.Button(
            retry_frame, text="🔄 重试失败的视频",
            font=(UI_FONT, 10, "bold"),
            bg=self.warning_color, fg="white", relief=tk.FLAT,
            cursor="hand2", command=self.retry_failed,
            padx=20, pady=8, state=tk.DISABLED
        )
        self.retry_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = tk.Button(
            retry_frame, text="⏹ 停止下载",
            font=(UI_FONT, 10, "bold"),
            bg=self.error_color, fg="white", relief=tk.FLAT,
            cursor="hand2", command=self.stop_download,
            padx=20, pady=8
        )
        self.stop_btn.pack(side=tk.LEFT)

        # 打赏按钮（放在右侧）
        donate_btn = tk.Button(
            retry_frame, text="☕ 打赏作者",
            font=(UI_FONT, 10),
            bg="#FF6B6B", fg="white", relief=tk.FLAT,
            cursor="hand2", command=self.show_donate_dialog,
            padx=15, pady=8
        )
        donate_btn.pack(side=tk.RIGHT)


    
    def on_url_focus_in(self, event):
        """URL输入框获得焦点时清除提示文本"""
        if self.url_text.get("1.0", tk.END).strip().startswith("请输入播放列表链接"):
            self.url_text.delete("1.0", tk.END)
            self.url_text.config(fg="#333")
    
    def on_url_focus_out(self, event):
        """URL输入框失去焦点时恢复提示文本"""
        if not self.url_text.get("1.0", tk.END).strip():
            self.url_text.insert("1.0", "请输入播放列表链接，每行一个\n例如：\nhttps://www.youtube.com/playlist?list=...\nhttps://www.youtube.com/playlist?list=...")
            self.url_text.config(fg="#999")
    
    def log(self, message, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry, level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        if level in ["ERROR", "WARN"]:
            try:
                with open(self.error_log_file, "a", encoding="utf-8", errors="replace") as f:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{ts}] [{level}] {message}\n")
            except:
                pass
    
    def change_directory(self):
        """更改下载目录"""
        global BASE_DOWNLOAD_DIR
        directory = filedialog.askdirectory(initialdir=BASE_DOWNLOAD_DIR)
        if directory:
            BASE_DOWNLOAD_DIR = directory
            self.dir_label.config(text=directory)
            self.log(f"下载目录已更改为: {directory}", "INFO")
    
    def clear_urls(self):
        """清空URL输入框"""
        self.url_text.delete("1.0", tk.END)
        self.url_text.insert("1.0", "请输入播放列表链接，每行一个\n例如：\nhttps://www.youtube.com/playlist?list=...\nhttps://www.youtube.com/playlist?list=...")
        self.url_text.config(fg="#999")
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []
    
    def sanitize_filename(self, name):
        """清理文件名"""
        illegal_chars = r'[<>:"/\\|?*]'
        name = re.sub(illegal_chars, '_', name)
        name = name.strip()
        if len(name) > 200:
            name = name[:200]
        return name
    
    def parse_all_playlists(self):
        """解析所有播放列表"""
        urls_text = self.url_text.get("1.0", tk.END).strip()
        
        if not urls_text or urls_text.startswith("请输入播放列表链接"):
            messagebox.showwarning("警告", "请输入至少一个播放列表链接！")
            return
        
        # 提取所有URL
        urls = [url.strip() for url in urls_text.split("\n") if url.strip() and url.strip().startswith("http")]
        
        if not urls:
            messagebox.showwarning("警告", "未找到有效的播放列表链接！")
            return
        
        self.log(f"开始解析 {len(urls)} 个播放列表...", "INFO")
        self.parse_btn.config(state=tk.DISABLED, text="解析中...")
        self.playlist_listbox.delete(0, tk.END)
        self.playlists = []
        
        def parse_thread():
            # 检查 yt-dlp
            result = subprocess.run(
                [PYTHON_PATH, "-m", "pip", "show", "yt-dlp"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.log("正在安装 yt-dlp...", "WARN")
                subprocess.run(
                    [PYTHON_PATH, "-m", "pip", "install", "yt-dlp"],
                    capture_output=True,
                    text=True
                )
            
            success_count = 0
            for idx, url in enumerate(urls, 1):
                self.log(f"[{idx}/{len(urls)}] 正在解析: {url[:50]}...", "INFO")
                
                try:
                    cmd = [
                        PYTHON_PATH, "-m", "yt_dlp",
                        "--dump-single-json",
                        "--flat-playlist",
                        url
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=30)
                    
                    if result.returncode != 0:
                        self.log(f"✗ 解析失败: {url[:50]}...", "ERROR")
                        self.log(f"错误详情: {(result.stderr or '')[:200]}", "ERROR")
                        continue
                    
                    playlist_data = json.loads(result.stdout)
                    playlist_title = playlist_data.get("title", f"Playlist_{idx}")
                    playlist_title = self.sanitize_filename(playlist_title)
                    
                    # 获取视频列表
                    videos = []
                    entries = playlist_data.get("entries", [])
                    for video_idx, entry in enumerate(entries, 1):
                        if entry:
                            videos.append({
                                "id": entry.get("id"),
                                "title": entry.get("title", f"Video_{video_idx}"),
                                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "playlist_index": video_idx
                            })
                    
                    playlist_info = {
                        "title": playlist_title,
                        "url": url,
                        "videos": videos,
                        "folder": os.path.join(BASE_DOWNLOAD_DIR, playlist_title)
                    }
                    
                    self.playlists.append(playlist_info)
                    
                    display_text = f"[{len(videos)} 个视频] {playlist_title}"
                    self.root.after(0, lambda t=display_text: self.playlist_listbox.insert(tk.END, t))
                    
                    self.log(f"✓ 解析成功: {playlist_title} ({len(videos)} 个视频)", "SUCCESS")
                    success_count += 1
                    
                except Exception as e:
                    self.log(f"✗ 解析出错: {str(e)}", "ERROR")
            
            self.log(f"解析完成！成功: {success_count}/{len(urls)}", "SUCCESS")
            
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL, text="📋 解析所有合集"))
            if self.playlists:
                self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.select_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=parse_thread, daemon=True).start()
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴内容"""
        try:
            clipboard_content = self.root.clipboard_get()
            if clipboard_content:
                self.url_text.delete("1.0", tk.END)
                self.url_text.insert("1.0", clipboard_content)
                self.log("✓ 已粘贴剪贴板内容", "SUCCESS")
            else:
                self.log("剪贴板为空", "WARN")
        except Exception as e:
            self.log(f"粘贴失败: {str(e)}", "ERROR")

    def direct_download(self):
        """直接下载（跳过解析和挑选）- 带详细日志"""
        urls = self.url_text.get("1.0", tk.END).strip().split("\n")
        urls = [url.strip() for url in urls if url.strip() and url.startswith("http")]
        
        if not urls:
            messagebox.showwarning("警告", "请先输入播放列表链接！")
            return
        
        self.log("=" * 60, "INFO")
        self.log("⚡ 直接下载模式 - 跳过解析和挑选", "INFO")
        self.log("=" * 60, "INFO")
        
        self.parse_btn.config(state=tk.DISABLED)
        self.select_btn.config(state=tk.DISABLED)
        self.download_btn.config(state=tk.DISABLED)
        self.direct_download_btn.config(state=tk.DISABLED)
        
        def download_thread():
            for idx, url in enumerate(urls, 1):
                self.root.after(0, lambda i=idx, total=len(urls): self.progress_label.config(
                    text=f"直接下载: {i}/{total}"
                ))
                self.root.after(0, lambda i=idx, total=len(urls): self.progress_bar.config(
                    value=(i/total)*100
                ))
                
                self.root.after(0, lambda u=url: self.log(f"\n{'='*60}", "INFO"))
                self.root.after(0, lambda i=idx, total=len(urls), u=url: self.log(
                    f"[{i}/{total}] 正在下载播放列表", "INFO"
                ))
                self.root.after(0, lambda u=url: self.log(f"  URL: {u}", "DETAIL"))
                self.root.after(0, lambda u=url: self.log(f"{'='*60}", "INFO"))
                
                # 准备下载目录
                output_dir = os.path.join(BASE_DOWNLOAD_DIR, "%(playlist_title)s")
                self.root.after(0, lambda d=BASE_DOWNLOAD_DIR: self.log(
                    f"📁 保存位置: {d}", "DETAIL"
                ))
                
                cmd = [
                    PYTHON_PATH, "-m", "yt_dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                    "--merge-output-format", "mp4",
                    "-o", os.path.join(BASE_DOWNLOAD_DIR, "%(playlist_title)s", "%(playlist_index)02d_%(title)s.%(ext)s"),
                    "--yes-playlist",
                    "--newline",
                    url
                ]
                
                if self.download_subtitles.get():
                    cmd.extend([
                        "--write-sub", "--write-auto-sub",
                        "--sub-lang", "zh-Hans,zh-Hant,en",
                        "--convert-subs", "srt"
                    ])
                    self.root.after(0, lambda: self.log("📝 已启用字幕下载", "INFO"))
                
                self.root.after(0, lambda: self.log("🚀 开始下载...", "INFO"))
                
                # 先获取播放列表信息
                try:
                    info_cmd = [PYTHON_PATH, "-m", "yt_dlp", "--flat-playlist", "--dump-single-json", url]
                    info_result = subprocess.run(info_cmd, capture_output=True, text=True, 
                                                encoding="utf-8", errors="replace", timeout=30)
                    if info_result.returncode == 0:
                        playlist_info = json.loads(info_result.stdout)
                        playlist_title = playlist_info.get("title", "未知")
                        video_count = len(playlist_info.get("entries", []))
                        self.root.after(0, lambda t=playlist_title, c=video_count: self.log(
                            f"  播放列表: {t}", "DETAIL"
                        ))
                        self.root.after(0, lambda c=video_count: self.log(
                            f"  视频数量: {c} 个", "DETAIL"
                        ))
                except Exception:
                    pass

                try:
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace"
                    )
                    
                    last_progress = -1
                    for line in process.stdout:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 检测各种操作
                        if "[download]" in line:
                            # 已下载跳过
                            if "has already been downloaded" in line:
                                self.root.after(0, lambda: self.log(
                                    f"  ⊙ 文件已存在，跳过下载", "INFO"
                                ))
                            
                            # 开始下载新视频
                            elif "Downloading item" in line or "Downloading video" in line:
                                match = re.search(r'(\d+) of (\d+)', line)
                                if match:
                                    current = match.group(1)
                                    total = match.group(2)
                                    self.root.after(0, lambda c=current, t=total: self.log(
                                        f"\n📥 正在下载第 {c}/{t} 个视频", "INFO"
                                    ))
                            
                            # 检测目标文件名
                            elif "Destination:" in line:
                                filename = line.split("Destination:")[-1].strip()
                                # 提取文件名（不含路径）
                                basename = os.path.basename(filename) if filename else filename
                                if basename:
                                    self.root.after(0, lambda f=basename: self.log(
                                        f"  文件名: {f}", "DETAIL"
                                    ))
                            
                            # 下载进度
                            elif "%" in line and "ETA" in line:
                                match = re.search(r'(\d+\.\d+)%', line)
                                if match:
                                    percent = float(match.group(1))
                                    current_tenth = int(percent / 10)
                                    if current_tenth > last_progress:
                                        speed_match = re.search(r'at\s+([\d\.]+\w+/s)', line)
                                        eta_match = re.search(r'ETA\s+([\d:]+)', line)
                                        speed = speed_match.group(1) if speed_match else "?"
                                        eta = eta_match.group(1) if eta_match else "?"
                                        
                                        self.root.after(0, lambda p=int(percent), s=speed, e=eta: self.log(
                                            f"  进度: {p}% | 速度: {s} | 剩余: {e}", "DETAIL"
                                        ))
                                        last_progress = current_tenth
                            
                            # 100%完成
                            elif "100%" in line:
                                self.root.after(0, lambda: self.log(
                                    f"  ✓ 下载完成", "SUCCESS"
                                ))
                        
                        # 创建目录
                        elif "[mkdir]" in line or "Creating directory" in line:
                            self.root.after(0, lambda: self.log(
                                f"  📁 创建文件夹", "DETAIL"
                            ))
                        
                        # 合并操作
                        elif "[Merger]" in line or "Merging formats" in line:
                            self.root.after(0, lambda: self.log(
                                f"  🔄 正在合并视频和音频...", "DETAIL"
                            ))
                        
                        # 后处理（重命名等）
                        elif "[post-processor]" in line or "Post-processing" in line:
                            if "Moving" in line or "Renaming" in line:
                                self.root.after(0, lambda: self.log(
                                    f"  ✏️ 正在重命名文件...", "DETAIL"
                                ))
                            else:
                                self.root.after(0, lambda: self.log(
                                    f"  ⚙️ 后处理中...", "DETAIL"
                                ))
                        
                        # 字幕下载
                        elif "Writing video subtitles" in line or "Downloading subtitle" in line:
                            self.root.after(0, lambda: self.log(
                                f"  📝 正在下载字幕...", "DETAIL"
                            ))
                        
                        # 提取音频
                        elif "Extracting audio" in line:
                            self.root.after(0, lambda: self.log(
                                f"  🎵 正在提取音频...", "DETAIL"
                            ))
                        
                        # 删除临时文件
                        elif "Deleting original file" in line:
                            self.root.after(0, lambda: self.log(
                                f"  🗑️ 清理临时文件...", "DETAIL"
                            ))
                    
                    process.wait()
                    
                    if process.returncode == 0:
                        self.root.after(0, lambda i=idx, total=len(urls): self.log(
                            f"✓ [{i}/{total}] 下载完成", "SUCCESS"
                        ))
                    else:
                        self.root.after(0, lambda i=idx, total=len(urls): self.log(
                            f"✗ [{i}/{total}] 下载失败", "ERROR"
                        ))
                
                except Exception as e:
                    self.root.after(0, lambda e=str(e): self.log(f"✗ 下载出错: {e[:200]}", "ERROR"))
            
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.direct_download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.log("=" * 60, "INFO"))
            self.root.after(0, lambda: self.log("⚡ 直接下载完成！", "SUCCESS"))
            self.root.after(0, lambda: self.log("=" * 60, "INFO"))
            self.root.after(0, lambda: self.progress_label.config(text="下载完成"))
        
        threading.Thread(target=download_thread, daemon=True).start()

    def select_videos_from_playlists(self):
        """为每个播放列表选择要下载的视频"""
        if not self.playlists:
            messagebox.showwarning("警告", "请先解析播放列表！")
            return
        
        self.log("开始选择视频...", "INFO")
        
        # 为每个播放列表打开选择对话框
        for playlist in self.playlists:
            dialog = VideoSelectorDialog(self.root, playlist)
            selected_videos = dialog.show()
            
            if selected_videos is None:
                # 用户取消了
                self.log(f"取消选择: {playlist['title']}", "WARN")
                continue
            
            # 更新播放列表的视频列表
            playlist['videos'] = selected_videos
            self.log(f"✓ {playlist['title']}: 已选择 {len(selected_videos)} 个视频", "SUCCESS")
        
        # 更新显示
        self.playlist_listbox.delete(0, tk.END)
        for playlist in self.playlists:
            display_text = f"[{len(playlist['videos'])} 个视频] {playlist['title']}"
            self.playlist_listbox.insert(tk.END, display_text)
        
        self.log("视频选择完成", "SUCCESS")

        # 启用下载按钮
        self.download_btn.config(state=tk.NORMAL)
        self.log("💡 提示: 点击 [🚀 开始批量下载] 按钮开始下载", "INFO")

    def start_batch_download(self):
        """开始批量下载"""
        if not self.playlists:
            messagebox.showwarning("警告", "没有可下载的播放列表！")
            return
        
        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.parse_btn.config(state=tk.DISABLED)
        self.failed_items = []
        
        total_videos = sum(len(p["videos"]) for p in self.playlists)
        self.log(f"开始批量下载 {len(self.playlists)} 个合集，共 {total_videos} 个视频", "INFO")
        
        def download_thread():
            total_success = 0
            total_fail = 0
            completed_videos = 0
            
            for playlist_idx, playlist in enumerate(self.playlists, 1):
                if not self.is_downloading:
                    self.log("下载已停止", "WARN")
                    break
                
                self.log(f"\n{'='*60}", "INFO")
                self.log(f"[{playlist_idx}/{len(self.playlists)}] 开始下载合集: {playlist['title']}", "INFO")
                self.log(f"{'='*60}", "INFO")
                
                # 创建合集文件夹
                os.makedirs(playlist["folder"], exist_ok=True)
                self.log(f"✓ 创建文件夹: {playlist['folder']}", "SUCCESS")
                
                # 加载进度
                progress_file = os.path.join(playlist["folder"], ".download_progress.json")
                progress_data = {}
                if os.path.exists(progress_file):
                    with open(progress_file, "r", encoding="utf-8", errors="replace") as f:
                        progress_data = json.load(f)
                
                # 下载视频
                for video_idx, video in enumerate(playlist["videos"], 1):
                    if not self.is_downloading:
                        break
                    
                    completed_videos += 1
                    overall_progress = (completed_videos / total_videos) * 100
                    self.root.after(0, lambda p=overall_progress: self.progress_bar.config(value=p))
                    self.root.after(0, lambda: self.progress_label.config(
                        text=f"合集 {playlist_idx}/{len(self.playlists)} | 视频 {video_idx}/{len(playlist['videos'])} | 总进度 {completed_videos}/{total_videos}"
                    ))
                    
                    if self.download_video(video, playlist["folder"], progress_data, progress_file):
                        total_success += 1
                    else:
                        total_fail += 1
                        self.failed_items.append({
                            "playlist": playlist,
                            "video": video
                        })
            
            self.log(f"\n{'='*60}", "INFO")
            self.log(f"✓ 批量下载完成！", "SUCCESS")
            self.log(f"  成功: {total_success} 个视频", "SUCCESS")
            self.log(f"  失败: {total_fail} 个视频", "ERROR" if total_fail > 0 else "INFO")
            self.log(f"  合集数: {len(self.playlists)}", "INFO")
            self.log(f"{'='*60}", "INFO")
            
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.parse_btn.config(state=tk.NORMAL))
            
            if total_fail > 0:
                self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))
        
        self.download_thread = threading.Thread(target=download_thread, daemon=True)
        self.download_thread.start()
    
    def download_video(self, video, folder, progress_data, progress_file, retry_count=0):
        """下载单个视频（带详细日志）"""
        video_id = video["id"]
        video_title = video["title"]
        playlist_index = video.get("playlist_index", 0)
        
        if video_id in progress_data and progress_data[video_id].get("completed"):
            self.log(f"⊙ 已下载，跳过: [{playlist_index:02d}] {video_title}", "INFO")
            return True
        
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"开始下载 [{playlist_index:02d}] {video_title}", "INFO")
        self.log(f"  视频URL: {video['url']}", "DETAIL")
        self.log(f"{'='*60}", "INFO")
        
        try:
            # 第一步：获取视频信息
            self.log("📊 正在获取视频信息...", "INFO")
            info_cmd = [PYTHON_PATH, "-m", "yt_dlp", "--dump-single-json", video["url"]]
            
            try:
                info_result = subprocess.run(info_cmd, capture_output=True, text=True, 
                                            encoding="utf-8", errors="replace", timeout=30)
                
                if info_result.returncode == 0:
                    video_info = json.loads(info_result.stdout)
                    formats = video_info.get("formats", [])
                    
                    video_formats = [f for f in formats if f.get("vcodec") != "none"]
                    audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
                    
                    self.log(f"  可用视频清晰度: {len(video_formats)} 个", "DETAIL")
                    if video_formats:
                        best_video = max(video_formats, key=lambda x: (x.get("height") or 0) * (x.get("width") or 0))
                        height = best_video.get("height", "?")
                        fps = best_video.get("fps", "?")
                        vcodec = (best_video.get("vcodec") or "?")[:20]
                        self.log(f"  选择视频: {height}p @ {fps}fps ({vcodec})", "DETAIL")
                    
                    self.log(f"  可用音频轨道: {len(audio_formats)} 个", "DETAIL")
                    if audio_formats:
                        best_audio = max(audio_formats, key=lambda x: x.get("abr") or 0)
                        abr = best_audio.get("abr", "?")
                        acodec = (best_audio.get("acodec") or "?")[:20]
                        self.log(f"  选择音频: {abr}kbps ({acodec})", "DETAIL")
                else:
                    self.log("  ⚠ 无法获取详细信息，继续下载", "WARN")
            except Exception as e:
                self.log(f"  ⚠ 获取信息失败: {str(e)[:100]}", "WARN")
            
            # 第二步：下载
            output_template = os.path.join(folder, f"{playlist_index:02d}_%(title)s.%(ext)s")
            
            cmd = [
                PYTHON_PATH, "-m", "yt_dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", output_template,
                "--no-playlist",
                "--newline",
                video["url"]
            ]
            
            if self.download_subtitles.get():
                sub_dir = os.path.join(folder, "字幕")
                os.makedirs(sub_dir, exist_ok=True)
                sub_tpl = os.path.join(sub_dir, f"{playlist_index:02d}_%(title)s.%(ext)s")
                cmd.extend([
                    "--write-sub", "--write-auto-sub",
                    "--sub-lang", "zh-Hans,zh-Hant,en",
                    "--convert-subs", "srt",
                    "-o", f"subtitle:{sub_tpl}"
                ])
                self.log("📝 已启用字幕下载", "INFO")
            
            self.log("🚀 开始下载...", "INFO")
            
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            
            last_progress = -1
            video_downloading = False
            audio_downloading = False
            merge_started = False
            
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                if "[download]" in line:
                    if "Destination:" in line:
                        if "m4a" in line or "audio" in line.lower():
                            if not audio_downloading:
                                self.log("  🎵 开始下载音频...", "DETAIL")
                                audio_downloading = True
                        else:
                            if not video_downloading:
                                self.log("  📥 开始下载视频...", "DETAIL")
                                video_downloading = True
                    
                    if "%" in line:
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            percent = float(match.group(1))
                            current_tenth = int(percent / 10)
                            if current_tenth > last_progress:
                                self.log(f"  进度: {int(percent)}%", "DETAIL")
                                last_progress = current_tenth
                
                elif "[Merger]" in line or "Merging formats into" in line:
                    if not merge_started:
                        self.log("  🔄 正在合并视频和音频...", "DETAIL")
                        merge_started = True
                
                elif "Writing video subtitles" in line or "Downloading subtitle" in line:
                    self.log("  📝 正在下载字幕...", "DETAIL")
            
            process.wait()
            
            if process.returncode == 0:
                self.log(f"✓ 下载完成: [{playlist_index:02d}] {video_title}", "SUCCESS")
                progress_data[video_id] = {
                    "title": video_title,
                    "completed": True,
                    "timestamp": datetime.now().isoformat()
                }
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                return True
            else:
                raise Exception(f"yt-dlp 返回错误代码 {process.returncode}")
        
        except Exception as e:
            if retry_count < MAX_RETRIES:
                self.log(f"✗ 下载失败，{RETRY_DELAY}秒后重试 ({retry_count + 1}/{MAX_RETRIES})", "WARN")
                self.log(f"  错误: {str(e)[:200]}", "ERROR")
                time.sleep(RETRY_DELAY)
                return self.download_video(video, folder, progress_data, progress_file, retry_count + 1)
            else:
                self.log(f"✗ 下载失败（已重试{MAX_RETRIES}次）: {video_title}", "ERROR")
                self.log(f"  错误: {str(e)[:200]}", "ERROR")
                progress_data[video_id] = {
                    "title": video_title,
                    "completed": False,
                    "error": str(e)[:200],
                    "timestamp": datetime.now().isoformat()
                }
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                return False
    
    def retry_failed(self):
        """重试失败的视频"""
        if not self.failed_items:
            messagebox.showinfo("提示", "没有失败的视频需要重试！")
            return
        
        self.log(f"开始重试 {len(self.failed_items)} 个失败的视频", "INFO")
        
        self.is_downloading = True
        self.retry_btn.config(state=tk.DISABLED)
        self.download_btn.config(state=tk.DISABLED)
        
        def retry_thread():
            success_count = 0
            fail_count = 0
            new_failed_items = []
            
            for i, item in enumerate(self.failed_items, 1):
                if not self.is_downloading:
                    break
                
                playlist = item["playlist"]
                video = item["video"]
                
                self.root.after(0, lambda p=(i/len(self.failed_items))*100: self.progress_bar.config(value=p))
                self.root.after(0, lambda t=f"重试中: {i}/{len(self.failed_items)}": self.progress_label.config(text=t))
                
                # 加载进度
                progress_file = os.path.join(playlist["folder"], ".download_progress.json")
                progress_data = {}
                if os.path.exists(progress_file):
                    with open(progress_file, "r", encoding="utf-8", errors="replace") as f:
                        progress_data = json.load(f)
                
                # 清除失败记录
                if video["id"] in progress_data:
                    del progress_data[video["id"]]
                
                if self.download_video(video, playlist["folder"], progress_data, progress_file):
                    success_count += 1
                else:
                    fail_count += 1
                    new_failed_items.append(item)
            
            self.failed_items = new_failed_items
            self.log(f"✓ 重试完成！成功: {success_count}, 失败: {fail_count}", "SUCCESS")
            
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            
            if fail_count > 0:
                self.root.after(0, lambda: self.retry_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=retry_thread, daemon=True).start()
    
    def show_donate_dialog(self):
        """显示打赏对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("打赏作者")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="#FFF5F5")

        # 居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 260
        dialog.geometry(f"+{x}+{y}")

        # 标题
        header = tk.Frame(dialog, bg="#FF6B6B", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="感谢您的支持！", font=(UI_FONT, 16, "bold"),
                 bg="#FF6B6B", fg="white").pack(pady=15)

        content = tk.Frame(dialog, bg="#FFF5F5")
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        tk.Label(content, text="如果这个工具对您有帮助，欢迎打赏支持作者继续开发！",
                 font=(UI_FONT, 10), bg="#FFF5F5", fg="#555",
                 wraplength=400).pack(pady=(0, 20))

        # 二维码区域
        qr_frame = tk.Frame(content, bg="#FFF5F5")
        qr_frame.pack(fill=tk.X, pady=(0, 15))

        # 微信收款码
        wechat_frame = tk.LabelFrame(qr_frame, text="微信支付", font=(UI_FONT, 10, "bold"),
                                      bg="#FFF5F5", fg="#07C160", padx=10, pady=10)
        wechat_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))

        qr_dir = os.path.join(os.path.dirname(__file__), "donate_qr")
        wechat_qr = os.path.join(qr_dir, "wechat.png")
        alipay_qr = os.path.join(qr_dir, "alipay.png")

        if os.path.exists(wechat_qr):
            try:
                wechat_img = tk.PhotoImage(file=wechat_qr)
                # 缩放到合适大小
                if wechat_img.width() > 160:
                    factor = wechat_img.width() // 160
                    wechat_img = wechat_img.subsample(max(factor, 1))
                wechat_label = tk.Label(wechat_frame, image=wechat_img, bg="#FFF5F5")
                wechat_label.image = wechat_img
                wechat_label.pack()
            except Exception:
                tk.Label(wechat_frame, text="请将微信收款码\n放入 donate_qr/wechat.png",
                         font=(UI_FONT, 9), bg="#FFF5F5", fg="#999",
                         height=8).pack()
        else:
            tk.Label(wechat_frame, text="请将微信收款码\n放入 donate_qr/wechat.png",
                     font=(UI_FONT, 9), bg="#FFF5F5", fg="#999",
                     height=8).pack()

        # 支付宝收款码
        alipay_frame = tk.LabelFrame(qr_frame, text="支付宝", font=(UI_FONT, 10, "bold"),
                                      bg="#FFF5F5", fg="#1677FF", padx=10, pady=10)
        alipay_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(10, 0))

        if os.path.exists(alipay_qr):
            try:
                alipay_img = tk.PhotoImage(file=alipay_qr)
                if alipay_img.width() > 160:
                    factor = alipay_img.width() // 160
                    alipay_img = alipay_img.subsample(max(factor, 1))
                alipay_label = tk.Label(alipay_frame, image=alipay_img, bg="#FFF5F5")
                alipay_label.image = alipay_img
                alipay_label.pack()
            except Exception:
                tk.Label(alipay_frame, text="请将支付宝收款码\n放入 donate_qr/alipay.png",
                         font=(UI_FONT, 9), bg="#FFF5F5", fg="#999",
                         height=8).pack()
        else:
            tk.Label(alipay_frame, text="请将支付宝收款码\n放入 donate_qr/alipay.png",
                     font=(UI_FONT, 9), bg="#FFF5F5", fg="#999",
                     height=8).pack()

        tk.Label(content, text="打赏金额随意，您的支持是我最大的动力！",
                 font=(UI_FONT, 9), bg="#FFF5F5", fg="#888").pack(pady=(10, 5))

        tk.Label(content, text="提示：将收款二维码图片(PNG格式)放入 donate_qr 文件夹即可显示",
                 font=(UI_FONT, 8), bg="#FFF5F5", fg="#AAA",
                 wraplength=400).pack(pady=(0, 15))

        tk.Button(content, text="关闭", font=(UI_FONT, 10),
                  bg="#e0e0e0", fg="#333", relief=tk.FLAT, cursor="hand2",
                  command=dialog.destroy, padx=30, pady=8).pack()

    def stop_download(self):
        """停止下载"""
        self.is_downloading = False
        self.log("正在停止下载...", "WARN")

def main():
    root = tk.Tk()
    app = YouTubeBatchDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()


