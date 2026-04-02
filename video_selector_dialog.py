"""
视频选择对话框 - 支持鼠标拖拽批量勾选
"""
import platform
import tkinter as tk
from tkinter import ttk, messagebox

IS_MAC = platform.system() == "Darwin"
UI_FONT = "PingFang SC" if IS_MAC else "Microsoft YaHei UI"


class VideoSelectorDialog:
    def __init__(self, parent, playlist_info):
        self.result = None
        self.playlist_info = playlist_info
        self.is_dragging = False
        self.drag_state = None
        self.last_toggled_index = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"选择视频 - {playlist_info['title']}")
        self.dialog.geometry("750x580")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 375
        y = (self.dialog.winfo_screenheight() // 2) - 290
        self.dialog.geometry(f"+{x}+{y}")

    def _build_ui(self):
        main = ttk.Frame(self.dialog)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        ttk.Label(main,
                  text=f"{self.playlist_info['title']}  ({len(self.playlist_info['videos'])} 个视频)",
                  font=(UI_FONT, 14, "bold")).pack(anchor="w", pady=(0, 8))

        # 快速选择按钮
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btn_row, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="取消全选", command=self.deselect_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="反选", command=self.invert_selection).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(btn_row, text="快速：", font=(UI_FONT, 10)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="前10", command=lambda: self.select_range(0, 10)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="前20", command=lambda: self.select_range(0, 20)).pack(side=tk.LEFT)
        ttk.Label(btn_row, text="按住拖拽可批量勾选", font=(UI_FONT, 10), foreground="gray").pack(side=tk.RIGHT)

        # 视频列表
        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        canvas = tk.Canvas(list_frame, highlightthickness=0, relief=tk.SUNKEN, bd=1)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.checkboxes = []
        self.checkbox_vars = []
        self.checkbox_frames = []

        for idx, video in enumerate(self.playlist_info['videos']):
            var = tk.BooleanVar(value=True)
            self.checkbox_vars.append(var)

            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill=tk.X, padx=8, pady=1)
            self.checkbox_frames.append(frame)

            cb = ttk.Checkbutton(frame,
                text=f"[{video['playlist_index']:02d}] {video['title']}",
                variable=var)
            cb.pack(anchor="w")
            self.checkboxes.append(cb)

            frame.bind("<ButtonPress-1>", lambda e, i=idx: self.on_drag_start(e, i))
            frame.bind("<B1-Motion>", self.on_drag_motion)
            frame.bind("<ButtonRelease-1>", self.on_drag_end)

        # 统计
        self.info_label = ttk.Label(main,
            text=f"已选择: {len(self.playlist_info['videos'])} / {len(self.playlist_info['videos'])}",
            font=(UI_FONT, 11))
        self.info_label.pack(pady=(0, 8))
        for var in self.checkbox_vars:
            var.trace_add("write", lambda *a: self.update_info())

        # 底部
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="确认选择", command=self.confirm).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(bottom, text="取消", command=self.cancel).pack(side=tk.LEFT)

    def on_drag_start(self, event, index):
        self.is_dragging = True
        self.drag_state = not self.checkbox_vars[index].get()
        self.checkbox_vars[index].set(self.drag_state)
        self.last_toggled_index = index

    def on_drag_motion(self, event):
        if not self.is_dragging: return
        w = event.widget.winfo_containing(event.x_root, event.y_root)
        if not w: return
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

    def select_all(self):
        for v in self.checkbox_vars: v.set(True)

    def deselect_all(self):
        for v in self.checkbox_vars: v.set(False)

    def invert_selection(self):
        for v in self.checkbox_vars: v.set(not v.get())

    def select_range(self, start, end):
        for i, v in enumerate(self.checkbox_vars): v.set(start <= i < end)

    def update_info(self):
        sel = sum(1 for v in self.checkbox_vars if v.get())
        self.info_label.config(text=f"已选择: {sel} / {len(self.checkbox_vars)}")

    def confirm(self):
        sel = [v for i, v in enumerate(self.playlist_info['videos']) if self.checkbox_vars[i].get()]
        if not sel:
            messagebox.showwarning("提示", "请至少选择一个视频", parent=self.dialog); return
        self.result = sel
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result
