"""
Windows-specific config override.
Call setup() early to redirect all paths to AppData / bundle.
"""
import os
import sys


def setup(data_dir, bundle_dir):
    """Override config module paths for Windows."""
    # Create data subdirs
    dirs = {
        "DOWNLOADS_DIR": os.path.join(data_dir, "downloads"),
        "CLIPS_DIR": os.path.join(data_dir, "clips"),
        "SUBTITLES_DIR": os.path.join(data_dir, "subtitles"),
        "JOBS_DIR": os.path.join(data_dir, "jobs"),
        "DB_PATH": os.path.join(data_dir, "drama_reels.db"),
        "LOGS_DIR": os.path.join(data_dir, "logs"),
    }
    for key, path in dirs.items():
        os.makedirs(path, exist_ok=True)
        # Inject into env so config.py picks them up
        os.environ[key] = path

    # Set tools path
    tools_dir = os.path.join(bundle_dir, "tools")
    if os.path.exists(tools_dir):
        ffmpeg = os.path.join(tools_dir, "ffmpeg.exe")
        yt_dlp = os.path.join(tools_dir, "yt-dlp.exe")
        whisper = os.path.join(tools_dir, "whisper")
        if os.path.exists(ffmpeg):
            os.environ["FFMPEG_PATH"] = ffmpeg
        if os.path.exists(yt_dlp):
            os.environ["YTDLP_PATH"] = yt_dlp

    # Template/static override
    template_dir = os.path.join(bundle_dir, "templates")
    if os.path.exists(template_dir):
        os.environ["TEMPLATE_DIR"] = template_dir
