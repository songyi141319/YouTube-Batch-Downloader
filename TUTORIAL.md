# YouTube 合集批量下载工具 — 新手教程

欢迎使用 YouTube 合集批量下载工具！本教程将手把手教你从零开始使用这个工具。

---

## 第一步：安装准备

### 1.1 安装 Python

你的电脑需要安装 Python 3.10 或更高版本。

**Windows 用户：**
1. 打开 https://www.python.org/downloads/
2. 点击黄色的「Download Python」按钮
3. 运行下载的安装程序
4. **重要：勾选「Add Python to PATH」**
5. 点击「Install Now」

**macOS 用户：**
1. 打开终端（按 Command + 空格，输入 Terminal）
2. 输入 `python3 --version`
3. 如果显示版本号（如 3.12.x），说明已安装
4. 如果未安装，从 https://www.python.org/downloads/ 下载

### 1.2 安装 FFmpeg

FFmpeg 是一个视频处理工具，我们需要它来合并视频和音频。

**Windows 用户：**
1. 打开 https://www.gyan.dev/ffmpeg/builds/
2. 下载 "ffmpeg-release-essentials.zip"
3. 解压到一个目录，比如 `C:\ffmpeg`
4. 将 `C:\ffmpeg\bin` 添加到系统 PATH 环境变量：
   - 右键「此电脑」→ 属性 → 高级系统设置 → 环境变量
   - 在「系统变量」中找到 Path，点击编辑
   - 新建，输入 `C:\ffmpeg\bin`
   - 确定保存
5. 重启命令提示符，输入 `ffmpeg -version` 验证

**macOS 用户：**
1. 先安装 Homebrew（如果没有）：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. 安装 FFmpeg：
   ```bash
   brew install ffmpeg
   ```

### 1.3 下载本工具

**方式一：从 GitHub 下载**
```bash
git clone https://github.com/songyi141319/YouTube-Batch-Downloader.git
```

**方式二：下载 Release 压缩包**
1. 打开 https://github.com/songyi141319/YouTube-Batch-Downloader/releases
2. 下载对应系统的 zip 文件
3. 解压到任意目录

### 1.4 安装依赖

打开终端/命令提示符，进入工具目录：

```bash
cd YouTube-Batch-Downloader
pip install -r requirements.txt
```

---

## 第二步：启动工具

### Windows

双击 `启动批量下载工具.bat` 即可启动。

或者在命令提示符中运行：
```bash
python youtube_batch_downloader_gui_v2.py
```

### macOS

双击 `启动下载工具.command` 即可启动。

首次运行可能会提示「无法验证开发者」：
1. 右键点击 `启动下载工具.command`
2. 选择「打开」
3. 在弹出的对话框中点击「打开」

或者在终端中运行：
```bash
python3 youtube_batch_downloader_gui_v2.py
```

---

## 第三步：基本使用

### 场景一：下载一个播放列表的全部视频

这是最简单的用法。

1. 打开 YouTube，进入你想下载的播放列表页面
2. 复制浏览器地址栏中的链接，格式类似：
   ```
   https://www.youtube.com/playlist?list=PLxxxxxxxx
   ```
3. 在工具界面中，点击「粘贴」按钮（或直接粘贴到输入框中）
4. 点击「直接下载」按钮
5. 等待下载完成

下载的视频会保存在 `~/Downloads/YouTube视频合集/播放列表名称/` 目录下。

### 场景二：下载播放列表中的部分视频

如果你只想下载其中几个视频：

1. 粘贴播放列表链接到输入框
2. 点击「解析合集」按钮，等待解析完成
3. 点击「挑选视频」按钮
4. 在弹出的视频列表中，勾选你想下载的视频
   - 默认是全选状态
   - 点击复选框可以取消/勾选
   - 按住鼠标左键拖拽可以批量操作
   - 使用「全选」「取消全选」「反选」按钮快速操作
5. 点击「确定下载」
6. 点击「开始批量下载」按钮

### 场景三：同时下载多个播放列表

1. 在输入框中粘贴多个播放列表链接，每行一个：
   ```
   https://www.youtube.com/playlist?list=PLaaa
   https://www.youtube.com/playlist?list=PLbbb
   https://www.youtube.com/playlist?list=PLccc
   ```
2. 点击「解析合集」按钮
3. 所有合集解析完成后，可以选择：
   - 点击「挑选视频」逐个合集选择
   - 或点击「开始批量下载」全部下载
4. 每个合集会自动创建独立的文件夹

---

## 第四步：进阶功能

### 4.1 更改保存位置

默认保存在 `~/Downloads/YouTube视频合集/`。

要更改保存位置：
1. 找到界面上的「保存位置」
2. 点击右侧的「更改」按钮
3. 在弹出的对话框中选择新的文件夹

### 4.2 下载字幕

如果你需要字幕：
1. 在界面上勾选「同时下载字幕」
2. 字幕文件（SRT 格式）会保存在视频同目录下的「字幕」子文件夹
3. 支持中文简体、中文繁体、英文三种语言

注意：不是所有视频都有字幕。没有字幕的视频会自动跳过字幕下载。

### 4.3 处理下载失败

如果有视频下载失败：
1. 下载完成后，底部的「重试失败」按钮会变为可用
2. 点击该按钮，程序会重新下载所有失败的视频
3. 每个视频最多自动重试 3 次

常见失败原因：
- 网络不稳定 → 重试通常能解决
- 视频被删除或设为私有 → 无法下载
- 地区限制 → 需要特殊网络环境

### 4.4 中断后继续下载

如果下载中途关闭了程序：
1. 重新打开程序
2. 输入相同的播放列表链接
3. 开始下载
4. 已经下载过的视频会自动跳过

这得益于每个播放列表文件夹中的 `.download_progress.json` 进度文件。

### 4.5 查看日志

- 界面下方的深色区域是实时日志窗口
- 不同颜色代表不同信息类型：
  - 青色 = 一般信息
  - 绿色 = 操作成功
  - 黄色 = 警告
  - 红色 = 错误
- 错误日志也会保存到 `error_log.txt` 文件

---

## 第五步：打赏支持

如果你觉得这个工具好用：
1. 点击右上角的「打赏支持」按钮
2. 在弹出窗口中扫描微信或支付宝二维码
3. 金额随意，感谢你的支持！

---

## 常见问题解答

### Q: 提示"yt-dlp 未找到"怎么办？
A: 程序首次运行会自动安装 yt-dlp。如果自动安装失败，手动运行：
```bash
pip install yt-dlp
```

### Q: 下载速度很慢怎么办？
A: 下载速度取决于网络环境，与本工具无关。确保网络稳定即可。

### Q: 如何更新 yt-dlp？
A: YouTube 经常更新，建议定期更新 yt-dlp：
```bash
pip install --upgrade yt-dlp
```

### Q: 可以下载单个视频吗？
A: 本工具主要针对播放列表。单个视频链接也可以粘贴到输入框，使用「直接下载」功能。

### Q: 下载的视频保存在哪里？
A: 默认保存在 `用户目录/Downloads/YouTube视频合集/` 下。可以通过界面上的「更改」按钮修改。

### Q: macOS 上提示无法打开？
A: 右键点击启动脚本 → 打开 → 确认。这是 macOS 的安全机制，首次打开需要手动确认。

---

恭喜你已经掌握了这个工具的使用方法！如有其他问题，欢迎在 GitHub 上提 Issue。
