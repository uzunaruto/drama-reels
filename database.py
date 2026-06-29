"""SQLite database for job tracking — extended with scheduler, multi-page, content calendar."""
import sqlite3
import os
import json
from datetime import datetime
from config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            message TEXT DEFAULT '',
            clip_duration INTEGER DEFAULT 45,
            clip_count INTEGER DEFAULT 0,
            clips_generated INTEGER DEFAULT 0,
            fb_page_id TEXT DEFAULT '',
            fb_uploaded INTEGER DEFAULT 0,
            language TEXT DEFAULT 'zh',
            whisper_model TEXT DEFAULT 'base',
            auto_translate INTEGER DEFAULT 0,
            watermark_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            thumbnail_path TEXT DEFAULT '',
            duration REAL DEFAULT 0,
            subtitle_path TEXT DEFAULT '',
            subtitle_translated_path TEXT DEFAULT '',
            title TEXT DEFAULT '',
            caption TEXT DEFAULT '',
            hashtags TEXT DEFAULT '[]',
            genre TEXT DEFAULT 'general',
            fb_video_id TEXT DEFAULT '',
            fb_status TEXT DEFAULT 'pending',
            fb_page_id TEXT DEFAULT '',
            watermark_applied INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS fb_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id TEXT NOT NULL UNIQUE,
            page_name TEXT DEFAULT '',
            access_token TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            posts_today INTEGER DEFAULT 0,
            last_post_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS publish_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER,
            job_id INTEGER,
            filename TEXT DEFAULT '',
            filepath TEXT DEFAULT '',
            thumbnail_path TEXT DEFAULT '',
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            page_id TEXT DEFAULT '',
            scheduled_time TEXT,
            status TEXT DEFAULT 'queued',
            published_at TEXT,
            fb_video_id TEXT,
            error TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS content_calendar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            page_id TEXT DEFAULT '',
            clip_id INTEGER,
            status TEXT DEFAULT 'planned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER,
            fb_video_id TEXT,
            page_id TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            engagement_rate REAL DEFAULT 0,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ============ JOBS ============

def create_job(url, clip_duration=45, fb_page_id="", language="zh",
               whisper_model="base", auto_translate=False, watermark_text=""):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO jobs (url, clip_duration, fb_page_id, language, 
           whisper_model, auto_translate, watermark_text) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (url, clip_duration, fb_page_id, language, whisper_model,
         int(auto_translate), watermark_text)
    )
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    sets.append("updated_at = CURRENT_TIMESTAMP")
    values.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_job(job_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_jobs(limit=50):
    conn = get_db()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_job(job_id):
    conn = get_db()
    conn.execute("DELETE FROM clips WHERE job_id = ?", (job_id,))
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


# ============ CLIPS ============

def create_clip(job_id, filename, filepath, duration=0, thumbnail_path="",
                title="", caption="", hashtags="[]", genre="general"):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO clips (job_id, filename, filepath, duration, thumbnail_path,
           title, caption, hashtags, genre) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (job_id, filename, filepath, duration, thumbnail_path,
         title, caption, json.dumps(hashtags) if isinstance(hashtags, list) else hashtags, genre)
    )
    clip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return clip_id


def update_clip(clip_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    values.append(clip_id)
    conn.execute(f"UPDATE clips SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def get_clips_by_job(job_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM clips WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_clip(clip_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_clips(limit=100):
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, j.title as job_title, j.url as job_url 
        FROM clips c 
        LEFT JOIN jobs j ON c.job_id = j.id 
        ORDER BY c.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============ FB PAGES ============

def add_fb_page(page_id, page_name="", access_token=""):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO fb_pages (page_id, page_name, access_token, is_active)
           VALUES (?, ?, ?, 1)""",
        (page_id, page_name, access_token)
    )
    conn.commit()
    conn.close()


def get_fb_pages():
    conn = get_db()
    rows = conn.execute("SELECT * FROM fb_pages WHERE is_active = 1 ORDER BY page_name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_fb_page(page_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM fb_pages WHERE page_id = ?", (page_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_fb_page(page_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    values.append(page_id)
    conn.execute(f"UPDATE fb_pages SET {', '.join(sets)} WHERE page_id = ?", values)
    conn.commit()
    conn.close()


def remove_fb_page(page_id):
    conn = get_db()
    conn.execute("UPDATE fb_pages SET is_active = 0 WHERE page_id = ?", (page_id,))
    conn.commit()
    conn.close()


# ============ PUBLISH QUEUE ============

def add_to_queue(clip_id, job_id, filename, filepath, title="",
                 description="", page_id="", scheduled_time=None,
                 thumbnail_path=""):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO publish_queue 
           (clip_id, job_id, filename, filepath, thumbnail_path, title, description, page_id, scheduled_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (clip_id, job_id, filename, filepath, thumbnail_path, title, description, page_id, scheduled_time)
    )
    queue_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return queue_id


def get_queue(status=None):
    conn = get_db()
    if status:
        rows = conn.execute(
            "SELECT * FROM publish_queue WHERE status = ? ORDER BY scheduled_time",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM publish_queue ORDER BY scheduled_time"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_queue():
    """Get items ready to publish (scheduled time passed or immediate)."""
    conn = get_db()
    now = datetime.now().isoformat()
    rows = conn.execute(
        """SELECT * FROM publish_queue 
           WHERE status = 'queued' 
           AND (scheduled_time IS NULL OR scheduled_time <= ?)
           ORDER BY scheduled_time""",
        (now,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_queue_item(queue_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    values.append(queue_id)
    conn.execute(f"UPDATE publish_queue SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_queue_item(queue_id):
    conn = get_db()
    conn.execute("DELETE FROM publish_queue WHERE id = ?", (queue_id,))
    conn.commit()
    conn.close()


def move_to_history(queue_id, status="published", fb_video_id=None, error=None):
    """Move queue item to history (update status)."""
    conn = get_db()
    conn.execute(
        """UPDATE publish_queue SET status = ?, published_at = CURRENT_TIMESTAMP,
           fb_video_id = ?, error = ? WHERE id = ?""",
        (status, fb_video_id, error, queue_id)
    )
    conn.commit()
    conn.close()


# ============ CONTENT CALENDAR ============

def add_calendar_entry(date, time_slot, title="", description="",
                       page_id="", clip_id=None):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO content_calendar (date, time_slot, title, description, page_id, clip_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (date, time_slot, title, description, page_id, clip_id)
    )
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def get_calendar_entries(start_date=None, end_date=None):
    conn = get_db()
    if start_date and end_date:
        rows = conn.execute(
            "SELECT * FROM content_calendar WHERE date BETWEEN ? AND ? ORDER BY date, time_slot",
            (start_date, end_date)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content_calendar ORDER BY date DESC, time_slot"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_calendar_entry(entry_id, **kwargs):
    conn = get_db()
    sets = []
    values = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        values.append(v)
    values.append(entry_id)
    conn.execute(f"UPDATE content_calendar SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


# ============ ANALYTICS ============

def record_analytics(clip_id, fb_video_id, page_id, views=0, likes=0,
                     comments=0, shares=0, reach=0):
    engagement = (likes + comments + shares) / max(views, 1) * 100
    conn = get_db()
    conn.execute(
        """INSERT INTO analytics (clip_id, fb_video_id, page_id, views, likes, 
           comments, shares, reach, engagement_rate)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (clip_id, fb_video_id, page_id, views, likes, comments, shares, reach, engagement)
    )
    conn.commit()
    conn.close()


def get_analytics_summary():
    conn = get_db()
    row = conn.execute("""
        SELECT 
            COUNT(*) as total_records,
            SUM(views) as total_views,
            SUM(likes) as total_likes,
            SUM(comments) as total_comments,
            SUM(shares) as total_shares,
            SUM(reach) as total_reach,
            AVG(engagement_rate) as avg_engagement
        FROM analytics
    """).fetchone()
    conn.close()
    return dict(row) if row else {}


# ============ STATS ============

def get_stats():
    conn = get_db()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'").fetchone()[0]
    total_clips = conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
    uploaded = conn.execute("SELECT COUNT(*) FROM clips WHERE fb_status = 'uploaded'").fetchone()[0]
    queue_pending = conn.execute("SELECT COUNT(*) FROM publish_queue WHERE status = 'queued'").fetchone()[0]
    pages = conn.execute("SELECT COUNT(*) FROM fb_pages WHERE is_active = 1").fetchone()[0]
    conn.close()
    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed,
        "total_clips": total_clips,
        "uploaded_clips": uploaded,
        "queue_pending": queue_pending,
        "fb_pages": pages
    }


def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()
