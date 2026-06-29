"""Configuration for Drama Reels pipeline — Windows & Linux compatible."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Windows: use AppData paths if set by config_win.py, else use local paths
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", os.path.join(BASE_DIR, "downloads"))
CLIPS_DIR = os.environ.get("CLIPS_DIR", os.path.join(BASE_DIR, "clips"))
SUBTITLES_DIR = os.environ.get("SUBTITLES_DIR", os.path.join(BASE_DIR, "subtitles"))
JOBS_DIR = os.environ.get("JOBS_DIR", os.path.join(BASE_DIR, "jobs"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database.db"))
LOGS_DIR = os.environ.get("LOGS_DIR", os.path.join(BASE_DIR, "logs"))

# Video processing defaults
DEFAULT_CLIP_DURATION = 45  # seconds
DEFAULT_OVERLAP = 5  # seconds overlap between clips
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
VIDEO_QUALITY = 23  # CRF value
PRESET = "ultrafast"

# Whisper
WHISPER_MODEL = "base"  # tiny, base, small, medium, large
WHISPER_LANGUAGE = "zh"  # Chinese source

# Facebook
FB_APP_ID = os.environ.get("FB_APP_ID", "")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET", "")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")

# Server — 127.0.0.1 for Windows (local only), 0.0.0.0 for VPS
HOST = os.environ.get("HOST", "127.0.0.1" if os.name == "nt" else "0.0.0.0")
PORT = int(os.environ.get("PORT", "7860"))

# ffmpeg path override (Windows bundle)
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "")
