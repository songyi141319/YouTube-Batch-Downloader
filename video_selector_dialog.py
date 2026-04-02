"""
视频选择对话框 - 用于选择要下载的视频
支持鼠标拖拽批量勾选
"""
import tkinter as tk
from tkinter import ttk, messagebox

class VideoSelectorDialog:
    def __init__(self, parent, playlist_info):
        self.result = None
        self.playlist_info = playlist_info
        
        # 拖拽状态
        self.is_dragging = False
        self.drag_state = None  # True=勾选, False=取消勾选
        self.last_toggled_index = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"选择视频 - {playlist_info['title']}")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 设置颜色
        self.bg_color = "#f0f0f0"
        self.primary_color = "#2196F3"
        self.success_color = "#4CAF50"
        
        self.dialog.configure(bg=self.bg_color)
        
        self.setup_ui()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def setup_ui(self):
        # 标题
        title_frame = tk.Frame(self.dialog, bg=self.primary_color, height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text=f"📹 {self.playlist_info['title']} ({len(self.playlist_info['videos'])} 个视频)",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg=self.primary_color,
            fg="white"
        ).pack(pady=12)
        
        # 主容器
        main_frame = tk.Frame(self.dialog, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 快速选择按钮
        button_frame = tk.Frame(main_frame, bg=self.bg_color)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(
            button_frame,
            text="✓ 全选",
            font=("Microsoft YaHei UI", 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.select_all,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(
            button_frame,
            text="✗ 取消全选",
            font=("Microsoft YaHei UI", 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.deselect_all,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(
            button_frame,
            text="⇅ 反选",
            font=("Microsoft YaHei UI", 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.invert_selection,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Label(
            button_frame,
            text="快速选择:",
            font=("Microsoft YaHei UI", 9),
            bg=self.bg_color,
            fg="#666"
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        tk.Button(
            button_frame,
            text="前10个",
            font=("Microsoft YaHei UI", 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.select_range(0, 10),
            padx=10,
            pady=5
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(
            button_frame,
            text="前20个",
            font=("Microsoft YaHei UI", 9),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.select_range(0, 20),
            padx=10,
            pady=5
        ).pack(side=tk.LEFT)
        
        # 提示文字
        tk.Label(
            button_frame,
            text="💡 提示: 按住鼠标左键拖动可批量勾选",
            font=("Microsoft YaHei UI", 8),
            bg=self.bg_color,
            fg="#999"
        ).pack(side=tk.RIGHT)
        
        # 视频列表（带复选框）
        list_frame = tk.Frame(main_frame, bg="white", relief=tk.FLAT, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建 Canvas 和 Scrollbar
        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg="white")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加视频复选框
        self.checkboxes = []
        self.checkbox_vars = []
        self.checkbox_frames = []
        
        for idx, video in enumerate(self.playlist_info['videos']):
            var = tk.BooleanVar(value=True)  # 默认全选
            self.checkbox_vars.append(var)
            
            frame = tk.Frame(self.scrollable_frame, bg="white")
            frame.pack(fill=tk.X, padx=10, pady=2)
            self.checkbox_frames.append(frame)
            
            cb = tk.Checkbutton(
                frame,
                text=f"[{video['playlist_index']:02d}] {video['title']}",
                variable=var,
                font=("Microsoft YaHei UI", 9),
                bg="white",
                fg="#333",
                activebackground="white",
                selectcolor="white",
                cursor="hand2"
            )
            cb.pack(anchor="w")
            self.checkboxes.append(cb)
            
            # 只在 frame 上绑定拖拽事件，不在 checkbox 上绑定
            frame.bind("<ButtonPress-1>", lambda e, i=idx: self.on_drag_start(e, i))
            frame.bind("<B1-Motion>", self.on_drag_motion)
            frame.bind("<ButtonRelease-1>", self.on_drag_end)
        
        # 统计信息
        self.info_label = tk.Label(
            main_frame,
            text=f"已选择: {len(self.playlist_info['videos'])} / {len(self.playlist_info['videos'])} 个视频",
            font=("Microsoft YaHei UI", 9),
            bg=self.bg_color,
            fg="#666"
        )
        self.info_label.pack(pady=(0, 15))
        
        # 绑定复选框变化事件
        for var in self.checkbox_vars:
            var.trace_add("write", lambda *args: self.update_info())
        
        # 底部按钮
        bottom_frame = tk.Frame(main_frame, bg=self.bg_color)
        bottom_frame.pack(fill=tk.X)
        
        tk.Button(
            bottom_frame,
            text="✓ 确定下载",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg=self.success_color,
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.confirm,
            padx=30,
            pady=10
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(
            bottom_frame,
            text="✗ 取消",
            font=("Microsoft YaHei UI", 11, "bold"),
            bg="#e0e0e0",
            fg="#333",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.cancel,
            padx=30,
            pady=10
        ).pack(side=tk.LEFT)
    
    def on_drag_start(self, event, index):
        """开始拖拽"""
        self.is_dragging = True
        # 记录拖拽的目标状态（与当前状态相反）
        current_state = self.checkbox_vars[index].get()
        self.drag_state = not current_state
        # 切换第一个复选框
        self.checkbox_vars[index].set(self.drag_state)
        self.last_toggled_index = index
    
    def on_drag_motion(self, event):
        """拖拽中"""
        if not self.is_dragging:
            return
        
        # 获取鼠标下的widget
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        if not widget:
            return
        
        # 查找对应的复选框索引
        for i, frame in enumerate(self.checkbox_frames):
            if widget == frame or widget.master == frame:
                # 避免重复切换同一个
                if i != self.last_toggled_index:
                    # 设置为拖拽状态
                    self.checkbox_vars[i].set(self.drag_state)
                    self.last_toggled_index = i
                break
    
    def on_drag_end(self, event):
        """结束拖拽"""
        self.is_dragging = False
        self.drag_state = None
        self.last_toggled_index = None
    
    def select_all(self):
        """全选"""
        for var in self.checkbox_vars:
            var.set(True)
    
    def deselect_all(self):
        """取消全选"""
        for var in self.checkbox_vars:
            var.set(False)
    
    def invert_selection(self):
        """反选"""
        for var in self.checkbox_vars:
            var.set(not var.get())
    
    def select_range(self, start, end):
        """选择范围"""
        for i, var in enumerate(self.checkbox_vars):
            var.set(start <= i < end)
    
    def update_info(self):
        """更新统计信息"""
        selected_count = sum(1 for var in self.checkbox_vars if var.get())
        total_count = len(self.checkbox_vars)
        self.info_label.config(text=f"已选择: {selected_count} / {total_count} 个视频")
    
    def confirm(self):
        """确认选择"""
        selected_videos = [
            video for i, video in enumerate(self.playlist_info['videos'])
            if self.checkbox_vars[i].get()
        ]
        
        if not selected_videos:
            messagebox.showwarning("警告", "请至少选择一个视频！", parent=self.dialog)
            return
        
        self.result = selected_videos
        self.dialog.destroy()
    
    def cancel(self):
        """取消"""
        self.result = None
        self.dialog.destroy()
    
    def show(self):
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result
