"""
视频选择对话框 - 支持鼠标拖拽批量勾选
Apple 风格 UI
"""
import platform
import tkinter as tk
from tkinter import ttk, messagebox

IS_MAC = platform.system() == "Darwin"
UI_FONT = "PingFang SC" if IS_MAC else "Microsoft YaHei UI"

# 配色与主界面一致
PRIMARY = "#1A1A2E"
ACCENT = "#E2B714"
BG = "#FAFAFA"
CARD = "#FFFFFF"
TEXT = "#1D1D1F"
TEXT_SEC = "#86868B"
SUCCESS = "#34C759"


class VideoSelectorDialog:
    def __init__(self, parent, playlist_info):
        self.result = None
        self.playlist_info = playlist_info

        # 拖拽状态
        self.is_dragging = False
        self.drag_state = None
        self.last_toggled_index = None

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"选择视频 - {playlist_info['title']}")
        self.dialog.geometry("800x620")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=BG)

        self._build_ui()

        # 居中
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 400
        y = (self.dialog.winfo_screenheight() // 2) - 310
        self.dialog.geometry(f"+{x}+{y}")

    def _btn(self, parent, text, cmd, style="ghost", **kw):
        colors = {
            "primary": (PRIMARY, "#FFFFFF"),
            "accent":  (ACCENT, PRIMARY),
            "success": (SUCCESS, "#FFFFFF"),
            "ghost":   ("#E8E8ED", TEXT),
        }
        bg, fg = colors.get(style, colors["ghost"])
        return tk.Button(parent, text=text, command=cmd,
                         font=(UI_FONT, 11), bg=bg, fg=fg,
                         activebackground=bg, activeforeground=fg,
                         relief=tk.FLAT, cursor="hand2",
                         padx=12, pady=4, highlightthickness=0, bd=0, **kw)

    def _build_ui(self):
        # 标题栏
        hdr = tk.Frame(self.dialog, bg=PRIMARY, height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr,
                 text=f"{self.playlist_info['title']}  ({len(self.playlist_info['videos'])} 个视频)",
                 font=(UI_FONT, 13, "bold"), bg=PRIMARY, fg="#FFFFFF").pack(pady=12)
        tk.Frame(self.dialog, bg=ACCENT, height=2).pack(fill=tk.X)

        # 主区域
        main = tk.Frame(self.dialog, bg=BG)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # 快速选择按钮
        btn_row = tk.Frame(main, bg=BG)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        self._btn(btn_row, "全选", self.select_all).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(btn_row, "取消全选", self.deselect_all).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(btn_row, "反选", self.invert_selection).pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(btn_row, text="快速：", font=(UI_FONT, 10),
                 bg=BG, fg=TEXT_SEC).pack(side=tk.LEFT, padx=(0, 4))
        self._btn(btn_row, "前10", lambda: self.select_range(0, 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._btn(btn_row, "前20", lambda: self.select_range(0, 20)).pack(side=tk.LEFT)

        tk.Label(btn_row, text="按住拖拽可批量勾选",
                 font=(UI_FONT, 10), bg=BG, fg=TEXT_SEC).pack(side=tk.RIGHT)

        # 视频列表
        list_frame = tk.Frame(main, bg=CARD, highlightthickness=1,
                              highlightbackground="#E8E8ED")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        canvas = tk.Canvas(list_frame, bg=CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=CARD)

        self.scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 复选框列表
        self.checkboxes = []
        self.checkbox_vars = []
        self.checkbox_frames = []

        for idx, video in enumerate(self.playlist_info['videos']):
            var = tk.BooleanVar(value=True)
            self.checkbox_vars.append(var)

            frame = tk.Frame(self.scrollable_frame, bg=CARD)
            frame.pack(fill=tk.X, padx=12, pady=2)
            self.checkbox_frames.append(frame)

            cb = tk.Checkbutton(
                frame,
                text=f"[{video['playlist_index']:02d}] {video['title']}",
                variable=var,
                font=(UI_FONT, 11), bg=CARD, fg=TEXT,
                activebackground=CARD, selectcolor=CARD,
                cursor="hand2", highlightthickness=0,
            )
            cb.pack(anchor="w")
            self.checkboxes.append(cb)

            frame.bind("<ButtonPress-1>", lambda e, i=idx: self.on_drag_start(e, i))
            frame.bind("<B1-Motion>", self.on_drag_motion)
            frame.bind("<ButtonRelease-1>", self.on_drag_end)

        # 统计
        self.info_label = tk.Label(main,
            text=f"已选择: {len(self.playlist_info['videos'])} / {len(self.playlist_info['videos'])}",
            font=(UI_FONT, 11), bg=BG, fg=TEXT_SEC)
        self.info_label.pack(pady=(0, 12))

        for var in self.checkbox_vars:
            var.trace_add("write", lambda *a: self.update_info())

        # 底部按钮
        bottom = tk.Frame(main, bg=BG)
        bottom.pack(fill=tk.X)

        self._btn(bottom, "确定下载", self.confirm, "success").pack(side=tk.LEFT, padx=(0, 10))
        self._btn(bottom, "取消", self.cancel, "ghost").pack(side=tk.LEFT)

    # ── 拖拽逻辑 ─────────────────────────────────────
    def on_drag_start(self, event, index):
        self.is_dragging = True
        cur = self.checkbox_vars[index].get()
        self.drag_state = not cur
        self.checkbox_vars[index].set(self.drag_state)
        self.last_toggled_index = index

    def on_drag_motion(self, event):
        if not self.is_dragging:
            return
        w = event.widget.winfo_containing(event.x_root, event.y_root)
        if not w:
            return
        for i, frame in enumerate(self.checkbox_frames):
            if w == frame or w.master == frame:
                if i != self.last_toggled_index:
                    self.checkbox_vars[i].set(self.drag_state)
                    self.last_toggled_index = i
                break

    def on_drag_end(self, event):
        self.is_dragging = False
        self.drag_state = None
        self.last_toggled_index = None

    # ── 选择操作 ─────────────────────────────────────
    def select_all(self):
        for v in self.checkbox_vars: v.set(True)

    def deselect_all(self):
        for v in self.checkbox_vars: v.set(False)

    def invert_selection(self):
        for v in self.checkbox_vars: v.set(not v.get())

    def select_range(self, start, end):
        for i, v in enumerate(self.checkbox_vars):
            v.set(start <= i < end)

    def update_info(self):
        sel = sum(1 for v in self.checkbox_vars if v.get())
        self.info_label.config(text=f"已选择: {sel} / {len(self.checkbox_vars)}")

    def confirm(self):
        sel = [v for i, v in enumerate(self.playlist_info['videos'])
               if self.checkbox_vars[i].get()]
        if not sel:
            messagebox.showwarning("提示", "请至少选择一个视频", parent=self.dialog)
            return
        self.result = sel
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result
