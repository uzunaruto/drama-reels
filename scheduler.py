"""Scheduler for auto-posting at optimal times."""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from config import JOBS_DIR

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "schedules.json")
PUBLISH_QUEUE_FILE = os.path.join(os.path.dirname(__file__), "publish_queue.json")

# Optimal posting times for Indonesian audience (WIB = UTC+7)
OPTIMAL_TIMES_WIB = [
    {"hour": 11, "minute": 0, "label": "Siang (11:00)"},
    {"hour": 13, "minute": 0, "label": "Makan Siang (13:00)"},
    {"hour": 18, "minute": 0, "label": "Sore (18:00)"},
    {"hour": 20, "minute": 0, "label": "Malam (20:00)"},
    {"hour": 21, "minute": 30, "label": "Prime Time (21:30)"},
]


def load_schedules():
    """Load scheduled posts."""
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return {"schedules": [], "auto_schedule": False, "posts_per_day": 3}


def save_schedules(data):
    """Save scheduled posts."""
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_publish_queue():
    """Load publish queue."""
    if os.path.exists(PUBLISH_QUEUE_FILE):
        with open(PUBLISH_QUEUE_FILE, "r") as f:
            return json.load(f)
    return {"queue": [], "history": []}


def save_publish_queue(data):
    """Save publish queue."""
    with open(PUBLISH_QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_to_queue(clip_id, job_id, filename, filepath, title="", description="",
                 page_id="", scheduled_time=None, hashtags=None):
    """Add a clip to the publish queue."""
    data = load_publish_queue()
    
    entry = {
        "id": len(data["queue"]) + len(data["history"]) + 1,
        "clip_id": clip_id,
        "job_id": job_id,
        "filename": filename,
        "filepath": filepath,
        "title": title,
        "description": description,
        "page_id": page_id,
        "hashtags": hashtags or [],
        "scheduled_time": scheduled_time,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "published_at": None,
        "fb_video_id": None,
        "error": None
    }
    
    data["queue"].append(entry)
    save_publish_queue(data)
    return entry


def auto_schedule_clips(clips, page_id, posts_per_day=3):
    """Auto-schedule clips for optimal posting times."""
    data = load_schedules()
    queue_data = load_publish_queue()
    
    # Calculate next available posting times
    now = datetime.now()
    wib_now = now + timedelta(hours=7)  # UTC to WIB
    
    scheduled = []
    clip_index = 0
    
    # Schedule for next 7 days
    for day_offset in range(7):
        if clip_index >= len(clips):
            break
        
        target_date = wib_now + timedelta(days=day_offset)
        
        # Pick optimal times for this day
        times_today = OPTIMAL_TIMES_WIB[:posts_per_day]
        
        for slot in times_today:
            if clip_index >= len(clips):
                break
            
            scheduled_time = target_date.replace(
                hour=slot["hour"],
                minute=slot["minute"],
                second=0
            )
            
            # Convert back to UTC
            utc_time = scheduled_time - timedelta(hours=7)
            
            # Only schedule future times
            if utc_time > now:
                clip = clips[clip_index]
                
                entry = add_to_queue(
                    clip_id=clip.get("id", 0),
                    job_id=clip.get("job_id", 0),
                    filename=clip.get("filename", ""),
                    filepath=clip.get("filepath", ""),
                    title=clip.get("title", f"Part {clip_index + 1}"),
                    description=clip.get("description", ""),
                    page_id=page_id,
                    scheduled_time=utc_time.isoformat(),
                    hashtags=clip.get("hashtags", [])
                )
                
                scheduled.append(entry)
                clip_index += 1
    
    return scheduled


def get_pending_posts():
    """Get posts that are ready to be published."""
    data = load_publish_queue()
    now = datetime.now().isoformat()
    
    pending = [
        p for p in data["queue"]
        if p["status"] == "queued" and (not p["scheduled_time"] or p["scheduled_time"] <= now)
    ]
    
    return pending


def mark_published(entry_id, fb_video_id=None, error=None):
    """Mark a queue entry as published."""
    data = load_publish_queue()
    
    for i, entry in enumerate(data["queue"]):
        if entry["id"] == entry_id:
            entry["status"] = "published" if not error else "failed"
            entry["published_at"] = datetime.now().isoformat()
            entry["fb_video_id"] = fb_video_id
            entry["error"] = error
            
            # Move to history
            data["history"].append(entry)
            data["queue"].pop(i)
            break
    
    save_publish_queue(data)


def get_schedule_stats():
    """Get scheduling statistics."""
    data = load_publish_queue()
    
    queued = len([e for e in data["queue"] if e["status"] == "queued"])
    published = len([e for e in data["history"] if e["status"] == "published"])
    failed = len([e for e in data["history"] if e["status"] == "failed"])
    
    return {
        "queued": queued,
        "published": published,
        "failed": failed,
        "total": queued + published + failed
    }
