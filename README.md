# 🎬 Drama Reels Pipeline

Auto download → transcribe → translate → clip → subtitle → watermark → schedule → upload to Facebook.

## ✨ Features

- 📥 **Bulk URL Processing** — proses banyak video sekaligus
- 🀄 **Auto-Translate** — subtitle Chinese → Indonesian
- 💧 **Watermark** — text overlay di semua clip
- 🖼️ **Auto-Thumbnail** — generate thumbnail per clip
- #️⃣ **Auto-Hashtag & Caption** — sesuai genre drama
- 📤 **Publish Queue** — manage upload ke Facebook
- ⏰ **Auto-Scheduler** — post di jam optimal Indonesia
- 📄 **Multi-Page** — manage beberapa Facebook Page
- 📅 **Content Calendar** — visual jadwal posting
- 📊 **Analytics** — track views, likes, engagement
- ✏️ **Clip Editor** — edit title, caption, hashtag
- 🔗 **Merge Clips** — gabung beberapa clip

## 🖥️ Windows Installation

### Option 1: Installer (Recommended)
1. Download `DramaReels-Setup-2.0.0.exe` dari [Releases](../../releases)
2. Double-click → ikuti wizard
3. Desktop shortcut otomatis dibuat
4. Jalankan, browser terbuka ke `http://localhost:7860`

### Option 2: Build Sendiri
```batch
git clone https://github.com/uzunaruto/drama-reels.git
cd drama-reels
build-windows.bat
```

Hasil: `dist\DramaReels.exe` (portable) atau `installer-output\DramaReels-Setup-2.0.0.exe`

### Requirements
- Windows 10/11 (64-bit)
- Python 3.10+ (untuk build dari source)

## 🐧 Linux/VPS
```bash
pip install flask faster-whisper imageio-ffmpeg requests yt-dlp
python app.py
```

## 📱 Cara Pakai

1. Buka `http://localhost:7860`
2. **New Job** → paste URL drama → klik Process
3. Tunggu proses (5-15 menit per video)
4. Clip otomatis masuk Queue
5. Atur jadwal posting di Calendar
6. Monitor di Dashboard

## 🔑 Setup Facebook

1. Buka [developers.facebook.com](https://developers.facebook.com)
2. Create App → Business
3. Settings → Basic → copy App ID & App Secret
4. App Review → request: `pages_manage_posts`, `pages_manage_videos`, `pages_show_list`
5. Di app Settings → Advanced → Connected Pages → tambahkan Page lo
6. Generate Access Token via OAuth di tab Pages

## 📁 Data Location (Windows)

Semua data disimpan di: `%APPDATA%\DramaReels\`
- `downloads/` — video asli
- `clips/` — clip yang sudah diproses
- `subtitles/` — file subtitle
- `jobs/` — data processing
- `drama_reels.db` — database

## License

MIT
