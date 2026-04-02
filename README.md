# YouTube 合集批量下载工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/UI-Apple%20Style-000000?style=flat-square&logo=apple" />
</p>

一个基于 Python + tkinter 的 YouTube 播放列表批量下载工具。深靛蓝 + 琥珀金配色，Apple 风格 UI，支持 Windows 和 macOS。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 批量下载 | 同时输入多个播放列表，一键批量下载 |
| 视频选择 | 解析后可逐个合集挑选视频，支持鼠标拖拽批量勾选 |
| 直接下载 | 跳过解析，直接下载整个播放列表 |
| 最高画质 | 自动选择最佳视频+音频，合并为 MP4 |
| 字幕下载 | 可选下载中文/英文字幕（SRT 格式） |
| 断点续传 | 已下载的视频自动跳过，支持中断后继续 |
| 失败重试 | 自动重试（最多3次），支持手动重试 |
| 实时日志 | 彩色终端风格日志，显示进度、速度、剩余时间 |
| 自定义路径 | 自由选择下载保存位置 |
| 打赏功能 | 内置微信/支付宝打赏支持 |

## 快速开始

### 环境要求

- **Python 3.10+**
- **FFmpeg**（用于视频音频合并，需加入系统 PATH）
- **yt-dlp**（首次运行时自动安装）

### 安装

```bash
git clone https://github.com/songyi141319/YouTube-Batch-Downloader.git
cd YouTube-Batch-Downloader
pip install -r requirements.txt
```

### 运行

```bash
# 通用
python youtube_batch_downloader_gui_v2.py

# Windows：双击
启动批量下载工具.bat

# macOS：双击
启动下载工具.command
```

## 界面预览

启动后的主界面采用深靛蓝 + 琥珀金配色：

- **顶栏**：深靛蓝标题 + 金色装饰线 + 打赏按钮
- **链接区**：白色卡片输入框
- **按钮行**：解析 / 挑选 / 直接下载 / 批量下载
- **合集列表**：显示已解析的播放列表
- **日志区**：深色终端风格，彩色日志
- **底栏**：进度条 + 重试/停止按钮

## 文件说明

| 文件 | 说明 |
|------|------|
| `youtube_batch_downloader_gui_v2.py` | 主程序 |
| `video_selector_dialog.py` | 视频选择对话框 |
| `donate_qr/` | 打赏二维码图片 |
| `启动批量下载工具.bat` | Windows 启动脚本 |
| `启动下载工具.command` | macOS 启动脚本 |
| `requirements.txt` | Python 依赖 |
| `MANUAL.md` | 详细使用说明 |
| `TUTORIAL.md` | 新手教程 |

## 打赏支持

如果这个工具对你有帮助，欢迎打赏支持！

| 微信支付 | 支付宝 |
|:---:|:---:|
| <img src="donate_qr/wechat.png" width="200"> | <img src="donate_qr/alipay.png" width="200"> |

## 许可证

MIT License
