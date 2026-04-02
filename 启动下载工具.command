#!/bin/bash
cd "$(dirname "$0")"
export SSL_CERT_FILE=/etc/ssl/cert.pem

# 优先使用 python.org 安装的 Python 3.12+（带 Tk 8.6，支持 Retina）
if [ -x /usr/local/bin/python3.12 ]; then
    PYTHON=/usr/local/bin/python3.12
elif [ -x /usr/local/bin/python3 ]; then
    PYTHON=/usr/local/bin/python3
else
    PYTHON=python3
fi

echo "使用 Python: $PYTHON"
$PYTHON --version

# 检查 yt-dlp
if ! "$PYTHON" -c "import yt_dlp" 2>/dev/null; then
    echo "正在安装 yt-dlp..."
    "$PYTHON" -m pip install yt-dlp --trusted-host pypi.org --trusted-host files.pythonhosted.org
fi

"$PYTHON" youtube_batch_downloader_gui_v2.py
