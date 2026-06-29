"""
Drama Reels — Windows Desktop Application
Auto-opens browser, runs Flask server in background.
"""
import os
import sys
import webbrowser
import threading
import time
import ctypes
import signal
import socket

# Determine base directory (for PyInstaller bundle vs dev)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else BASE_DIR
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

# Data directory: %APPDATA%/DramaReels (persists across updates)
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
DATA_DIR = os.path.join(APPDATA, "DramaReels")
os.makedirs(DATA_DIR, exist_ok=True)

# Override config paths for Windows
os.environ["DRAMA_REELS_DATA"] = DATA_DIR
os.environ["DRAMA_REELS_BASE"] = BASE_DIR
os.environ["DRAMA_REELS_BUNDLE"] = BUNDLE_DIR

# Set ffmpeg/yt-dlp paths from bundle
TOOLS_DIR = os.path.join(BUNDLE_DIR, "tools")
if os.path.exists(TOOLS_DIR):
    os.environ["PATH"] = TOOLS_DIR + os.pathsep + os.environ.get("PATH", "")

# Set host/port
HOST = "127.0.0.1"
PORT = 7860


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_server(port, timeout=30):
    """Wait until Flask server is ready."""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.3)
    return False


def open_browser(port):
    """Open browser after server is ready."""
    if wait_for_server(port):
        webbrowser.open(f"http://localhost:{port}")


def main():
    print("=" * 50)
    print("  🎬 Drama Reels Pipeline")
    print("  Auto Download • Clip • Translate • Upload")
    print("=" * 50)
    print(f"  Data: {DATA_DIR}")
    print(f"  URL:  http://localhost:{PORT}")
    print("=" * 50)

    if is_port_in_use(PORT):
        print(f"\n⚠️  Port {PORT} sudah dipakai. Membuka browser...")
        webbrowser.open(f"http://localhost:{PORT}")
        input("\nTekan Enter untuk keluar...")
        return

    # Import and configure the app
    sys.path.insert(0, BUNDLE_DIR)
    sys.path.insert(0, BASE_DIR)

    # Override config module for Windows paths
    import config_win
    config_win.setup(DATA_DIR, BUNDLE_DIR)

    from app import app, ensure_dirs
    from database import init_db

    ensure_dirs()
    init_db()

    # Open browser in background
    browser_thread = threading.Thread(target=open_browser, args=(PORT,), daemon=True)
    browser_thread.start()

    print(f"\n✅ Server running at http://localhost:{PORT}")
    print("   Browser akan terbuka otomatis...")
    print("   Tutup window ini untuk stop server.\n")

    # Run Flask
    try:
        app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")


if __name__ == "__main__":
    main()
