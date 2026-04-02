#!/bin/bash
cd "$(dirname "$0")"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    echo "可以从 https://www.python.org/downloads/ 下载"
    read -p "按回车键退出..."
    exit 1
fi

# 检查 yt-dlp
if ! python3 -c "import yt_dlp" 2>/dev/null; then
    echo "正在安装 yt-dlp..."
    python3 -m pip install yt-dlp
fi

python3 youtube_batch_downloader_gui_v2.py
