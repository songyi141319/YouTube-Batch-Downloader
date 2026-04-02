@echo off
chcp 65001 >nul
title YouTube Batch Downloader v2
cd /d "%~dp0"
C:\Python314\python.exe youtube_batch_downloader_gui_v2.py
if errorlevel 1 (
    echo.
    echo Program failed to start!
    pause
)
