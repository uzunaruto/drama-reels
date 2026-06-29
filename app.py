"""Flask web application for Drama Reels pipeline — FULL FEATURED."""
import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

from config import *
from database import (
    init_db, create_job, update_job, get_job, get_all_jobs, delete_job,
    get_clips_by_job, create_clip, update_clip, get_clip, get_all_clips,
    get_stats, get_setting, set_setting,
    add_fb_page, get_fb_pages, get_fb_page, update_fb_page, remove_fb_page,
    add_to_queue, get_queue, get_pending_queue, update_queue_item,
    delete_queue_item, move_to_history,
    add_calendar_entry, get_calendar_entries, update_calendar_entry,
    record_analytics, get_analytics_summary
)
from processor import process_video
from uploader import FacebookUploader
from content_gen import generate_full_post, detect_genre

template_dir = os.environ.get("TEMPLATE_DIR", os.path.join(BASE_DIR, "templates"))
app = Flask(__name__, template_folder=template_dir)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

active_jobs = {}
scheduler_running = False


def get_fb_uploader(page_id=None):
    """Get Facebook uploader for a specific page or default."""
    if page_id:
        page = get_fb_page(page_id)
        if page and page.get("access_token"):
            return FacebookUploader(
                access_token=page["access_token"],
                page_id=page_id
            )
    # Fallback to global settings
    return FacebookUploader(
        access_token=get_setting("fb_access_token", FB_ACCESS_TOKEN),
        page_id=get_setting("fb_page_id", FB_PAGE_ID)
    )


def process_job_async(job_id, url, clip_duration, fb_page_id, language,
                       whisper_model, auto_translate, watermark_text):
    """Process a video job in background thread."""
    job_dir = os.path.join(JOBS_DIR, str(job_id))
    os.makedirs(job_dir, exist_ok=True)
    
    def progress_cb(pct, msg):
        update_job(job_id, progress=pct, message=msg)
    
    try:
        update_job(job_id, status="processing", progress=0, message="Starting...")
        
        result = process_video(
            url=url,
            job_dir=job_dir,
            clip_duration=clip_duration,
            language=language,
            whisper_model=whisper_model,
            auto_translate=auto_translate,
            watermark_text=watermark_text,
            progress_callback=progress_cb
        )
        
        clips = result["clips"]
        metadata = result.get("metadata", {})
        
        # Update job title from metadata
        if metadata.get("title"):
            update_job(job_id, title=metadata["title"])
        
        # Save clips to database
        for clip in clips:
            create_clip(
                job_id=job_id,
                filename=clip["filename"],
                filepath=clip["filepath"],
                duration=clip["duration"],
                thumbnail_path=clip.get("thumbnail_path", ""),
                title=clip.get("title", ""),
                caption=clip.get("caption", ""),
                hashtags=clip.get("hashtags", []),
                genre=clip.get("genre", "general")
            )
        
        update_job(
            job_id,
            status="completed",
            progress=100,
            message=f"Generated {len(clips)} clips",
            clip_count=len(clips),
            clips_generated=len(clips)
        )
        
        # Auto-add to queue if page specified
        if fb_page_id and clips:
            from scheduler import auto_schedule_clips
            scheduled = auto_schedule_clips(
                clips=[
                    {
                        "id": c.get("index", i),
                        "job_id": job_id,
                        "filename": c["filename"],
                        "filepath": c["filepath"],
                        "title": c.get("title", ""),
                        "description": c.get("description", ""),
                        "hashtags": c.get("hashtags", []),
                        "thumbnail_path": c.get("thumbnail_path", "")
                    }
                    for i, c in enumerate(clips)
                ],
                page_id=fb_page_id,
                posts_per_day=3
            )
            update_job(job_id, message=f"Done! {len(clips)} clips, {len(scheduled)} scheduled for posting")
        
    except Exception as e:
        update_job(job_id, status="failed", message=f"Error: {str(e)[:200]}")
    finally:
        if job_id in active_jobs:
            del active_jobs[job_id]


def scheduler_worker():
    """Background worker that processes the publish queue."""
    global scheduler_running
    scheduler_running = True
    
    while scheduler_running:
        try:
            pending = get_pending_queue()
            
            for item in pending:
                try:
                    page_id = item.get("page_id", "")
                    if not page_id:
                        continue
                    
                    # Check rate limit (max 10 posts per page per day)
                    page = get_fb_page(page_id)
                    if page:
                        today = datetime.now().strftime("%Y-%m-%d")
                        last_post = page.get("last_post_at", "")
                        if last_post and last_post.startswith(today):
                            if page.get("posts_today", 0) >= 10:
                                continue
                    
                    # Upload
                    uploader = get_fb_uploader(page_id)
                    
                    if not os.path.exists(item["filepath"]):
                        update_queue_item(item["id"], status="failed", error="File not found")
                        continue
                    
                    result = uploader.upload_reel(
                        video_path=item["filepath"],
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        page_id=page_id
                    )
                    
                    move_to_history(
                        item["id"],
                        status="published",
                        fb_video_id=result.get("video_id")
                    )
                    
                    # Update clip status
                    if item.get("clip_id"):
                        update_clip(item["clip_id"], fb_status="uploaded",
                                   fb_video_id=result.get("video_id", ""),
                                   fb_page_id=page_id)
                    
                    # Update page stats
                    if page:
                        update_fb_page(page_id,
                                      posts_today=page.get("posts_today", 0) + 1,
                                      last_post_at=datetime.now().isoformat())
                    
                    # Rate limit between posts
                    time.sleep(30)
                    
                except Exception as e:
                    move_to_history(item["id"], status="failed", error=str(e)[:200])
                    print(f"Queue publish error: {e}")
                    continue
            
        except Exception as e:
            print(f"Scheduler error: {e}")
        
        time.sleep(60)  # Check every minute


# ============ ROUTES ============

@app.route("/")
def index():
    jobs = get_all_jobs(20)
    stats = get_stats()
    pages = get_fb_pages()
    return render_template("index.html", jobs=jobs, stats=stats, pages=pages)


# ============ JOBS API ============

@app.route("/api/jobs", methods=["GET"])
def api_list_jobs():
    jobs = get_all_jobs(50)
    return jsonify({"jobs": jobs})


@app.route("/api/jobs", methods=["POST"])
def api_create_job():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    # Check for bulk URLs (comma or newline separated)
    urls = [u.strip() for u in url.replace("\n", ",").split(",") if u.strip()]
    
    job_ids = []
    for u in urls:
        job_id = create_job(
            url=u,
            clip_duration=int(data.get("clip_duration", DEFAULT_CLIP_DURATION)),
            fb_page_id=data.get("fb_page_id", ""),
            language=data.get("language", "zh"),
            whisper_model=data.get("whisper_model", WHISPER_MODEL),
            auto_translate=data.get("auto_translate", False),
            watermark_text=data.get("watermark_text", "")
        )
        
        if data.get("title"):
            update_job(job_id, title=data["title"])
        
        thread = threading.Thread(
            target=process_job_async,
            args=(job_id, u, int(data.get("clip_duration", DEFAULT_CLIP_DURATION)),
                  data.get("fb_page_id", ""), data.get("language", "zh"),
                  data.get("whisper_model", WHISPER_MODEL),
                  data.get("auto_translate", False),
                  data.get("watermark_text", "")),
            daemon=True
        )
        thread.start()
        active_jobs[job_id] = thread
        job_ids.append(job_id)
    
    return jsonify({"job_ids": job_ids, "count": len(job_ids), "status": "created"})


@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def api_get_job(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    clips = get_clips_by_job(job_id)
    return jsonify({"job": job, "clips": clips})


@app.route("/api/jobs/<int:job_id>", methods=["DELETE"])
def api_delete_job(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    job_dir = os.path.join(JOBS_DIR, str(job_id))
    if os.path.exists(job_dir):
        import shutil
        shutil.rmtree(job_dir, ignore_errors=True)
    
    delete_job(job_id)
    return jsonify({"success": True})


# ============ CLIPS API ============

@app.route("/api/clips", methods=["GET"])
def api_list_clips():
    clips = get_all_clips(100)
    return jsonify({"clips": clips})


@app.route("/api/clips/<int:clip_id>", methods=["GET"])
def api_get_clip(clip_id):
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip not found"}), 404
    return jsonify(clip)


@app.route("/api/clips/<int:clip_id>", methods=["PATCH"])
def api_update_clip(clip_id):
    data = request.json or {}
    allowed = ["title", "caption", "hashtags", "description"]
    updates = {k: v for k, v in data.items() if k in allowed}
    if updates:
        if "hashtags" in updates and isinstance(updates["hashtags"], list):
            updates["hashtags"] = json.dumps(updates["hashtags"])
        update_clip(clip_id, **updates)
    return jsonify({"success": True})


@app.route("/api/clips/<int:clip_id>/upload", methods=["POST"])
def api_upload_clip(clip_id):
    data = request.json or {}
    page_id = data.get("page_id", "")
    
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip not found"}), 404
    
    try:
        uploader = get_fb_uploader(page_id)
        title = data.get("title", clip.get("title", f"Drama China Part {clip_id}"))
        description = data.get("description", clip.get("description",
            f"{title}\n\n#DramaChina #CDrama #SubtitleIndonesia"))
        
        result = uploader.upload_reel(
            video_path=clip["filepath"],
            title=title,
            description=description,
            page_id=page_id
        )
        
        update_clip(clip_id, fb_video_id=result.get("video_id", ""),
                    fb_status="uploaded", fb_page_id=page_id)
        
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clips/<int:clip_id>/queue", methods=["POST"])
def api_queue_clip(clip_id):
    """Add clip to publish queue."""
    data = request.json or {}
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip not found"}), 404
    
    queue_id = add_to_queue(
        clip_id=clip_id,
        job_id=clip.get("job_id", 0),
        filename=clip["filename"],
        filepath=clip["filepath"],
        thumbnail_path=clip.get("thumbnail_path", ""),
        title=data.get("title", clip.get("title", "")),
        description=data.get("description", clip.get("description", "")),
        page_id=data.get("page_id", clip.get("fb_page_id", "")),
        scheduled_time=data.get("scheduled_time")
    )
    
    return jsonify({"queue_id": queue_id, "status": "queued"})


@app.route("/api/clips/<int:clip_id>/download")
def api_download_clip(clip_id):
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip not found"}), 404
    if not os.path.exists(clip["filepath"]):
        return jsonify({"error": "File not found"}), 404
    return send_file(clip["filepath"], as_attachment=True, download_name=clip["filename"])


@app.route("/api/clips/<int:clip_id>/thumbnail")
def api_get_thumbnail(clip_id):
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip not found"}), 404
    thumb = clip.get("thumbnail_path", "")
    if thumb and os.path.exists(thumb):
        return send_file(thumb, mimetype="image/jpeg")
    return jsonify({"error": "No thumbnail"}), 404


@app.route("/api/clips/<int:clip_id>/merge", methods=["POST"])
def api_merge_clip(clip_id):
    """Merge clip with another clip."""
    data = request.json or {}
    other_id = data.get("merge_with")
    if not other_id:
        return jsonify({"error": "merge_with required"}), 400
    
    clip1 = get_clip(clip_id)
    clip2 = get_clip(int(other_id))
    if not clip1 or not clip2:
        return jsonify({"error": "Clip not found"}), 404
    
    from processor import merge_clips
    output_path = os.path.join(os.path.dirname(clip1["filepath"]),
                                f"merged_{clip_id}_{other_id}.mp4")
    
    try:
        merge_clips([clip1["filepath"], clip2["filepath"]], output_path)
        return send_file(output_path, as_attachment=True,
                        download_name=f"merged_{clip_id}_{other_id}.mp4")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ QUEUE API ============

@app.route("/api/queue", methods=["GET"])
def api_get_queue():
    status = request.args.get("status")
    items = get_queue(status)
    return jsonify({"queue": items})


@app.route("/api/queue", methods=["POST"])
def api_add_to_queue():
    data = request.json or {}
    queue_id = add_to_queue(
        clip_id=data.get("clip_id", 0),
        job_id=data.get("job_id", 0),
        filename=data.get("filename", ""),
        filepath=data.get("filepath", ""),
        thumbnail_path=data.get("thumbnail_path", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        page_id=data.get("page_id", ""),
        scheduled_time=data.get("scheduled_time")
    )
    return jsonify({"queue_id": queue_id})


@app.route("/api/queue/<int:queue_id>", methods=["DELETE"])
def api_delete_queue(queue_id):
    delete_queue_item(queue_id)
    return jsonify({"success": True})


@app.route("/api/queue/<int:queue_id>/publish", methods=["POST"])
def api_publish_now(queue_id):
    """Force publish a queued item immediately."""
    items = get_queue()
    item = next((i for i in items if i["id"] == queue_id), None)
    if not item:
        return jsonify({"error": "Queue item not found"}), 404
    
    try:
        uploader = get_fb_uploader(item.get("page_id"))
        result = uploader.upload_reel(
            video_path=item["filepath"],
            title=item.get("title", ""),
            description=item.get("description", ""),
            page_id=item.get("page_id")
        )
        
        move_to_history(queue_id, status="published", fb_video_id=result.get("video_id"))
        return jsonify({"success": True, "result": result})
    except Exception as e:
        move_to_history(queue_id, status="failed", error=str(e))
        return jsonify({"error": str(e)}), 500


# ============ PAGES API ============

@app.route("/api/pages", methods=["GET"])
def api_list_pages():
    pages = get_fb_pages()
    return jsonify({"pages": pages})


@app.route("/api/pages", methods=["POST"])
def api_add_page():
    data = request.json or {}
    page_id = data.get("page_id", "").strip()
    if not page_id:
        return jsonify({"error": "Page ID required"}), 400
    
    add_fb_page(
        page_id=page_id,
        page_name=data.get("page_name", ""),
        access_token=data.get("access_token", "")
    )
    return jsonify({"success": True})


@app.route("/api/pages/<page_id>", methods=["DELETE"])
def api_remove_page(page_id):
    remove_fb_page(page_id)
    return jsonify({"success": True})


@app.route("/api/pages/<page_id>", methods=["PATCH"])
def api_update_page(page_id):
    data = request.json or {}
    updates = {}
    for k in ["page_name", "access_token", "is_active"]:
        if k in data:
            updates[k] = data[k]
    if updates:
        update_fb_page(page_id, **updates)
    return jsonify({"success": True})


# ============ CALENDAR API ============

@app.route("/api/calendar", methods=["GET"])
def api_get_calendar():
    start = request.args.get("start")
    end = request.args.get("end")
    entries = get_calendar_entries(start, end)
    return jsonify({"entries": entries})


@app.route("/api/calendar", methods=["POST"])
def api_add_calendar():
    data = request.json or {}
    entry_id = add_calendar_entry(
        date=data.get("date", datetime.now().strftime("%Y-%m-%d")),
        time_slot=data.get("time_slot", "12:00"),
        title=data.get("title", ""),
        description=data.get("description", ""),
        page_id=data.get("page_id", ""),
        clip_id=data.get("clip_id")
    )
    return jsonify({"entry_id": entry_id})


@app.route("/api/calendar/<int:entry_id>", methods=["PATCH"])
def api_update_calendar(entry_id):
    data = request.json or {}
    updates = {k: v for k, v in data.items() if k in ["title", "description", "status", "page_id"]}
    if updates:
        update_calendar_entry(entry_id, **updates)
    return jsonify({"success": True})


# ============ ANALYTICS API ============

@app.route("/api/analytics", methods=["GET"])
def api_get_analytics():
    summary = get_analytics_summary()
    return jsonify(summary)


@app.route("/api/analytics", methods=["POST"])
def api_record_analytics():
    data = request.json or {}
    record_analytics(
        clip_id=data.get("clip_id"),
        fb_video_id=data.get("fb_video_id", ""),
        page_id=data.get("page_id", ""),
        views=data.get("views", 0),
        likes=data.get("likes", 0),
        comments=data.get("comments", 0),
        shares=data.get("shares", 0),
        reach=data.get("reach", 0)
    )
    return jsonify({"success": True})


# ============ SETTINGS API ============

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    settings = {
        "fb_app_id": get_setting("fb_app_id", FB_APP_ID),
        "fb_page_id": get_setting("fb_page_id", FB_PAGE_ID),
        "fb_access_token": get_setting("fb_access_token", FB_ACCESS_TOKEN),
        "clip_duration": get_setting("clip_duration", str(DEFAULT_CLIP_DURATION)),
        "whisper_model": get_setting("whisper_model", WHISPER_MODEL),
        "language": get_setting("language", "zh"),
        "auto_translate": get_setting("auto_translate", "false"),
        "watermark_text": get_setting("watermark_text", ""),
        "posts_per_day": get_setting("posts_per_day", "3"),
        "auto_schedule": get_setting("auto_schedule", "true"),
    }
    return jsonify(settings)


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.json or {}
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({"success": True})


# ============ STATS API ============

@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())


# ============ FACEBOOK AUTH ============

@app.route("/api/fb/auth-url", methods=["GET"])
def api_fb_auth_url():
    app_id = request.args.get("app_id", get_setting("fb_app_id", FB_APP_ID))
    uploader = FacebookUploader()
    url = uploader.get_auth_url(app_id=app_id)
    return jsonify({"auth_url": url})


@app.route("/api/fb/exchange", methods=["POST"])
def api_fb_exchange():
    data = request.json or {}
    code = data.get("code", "")
    if not code:
        return jsonify({"error": "Code required"}), 400
    
    try:
        uploader = FacebookUploader()
        result = uploader.exchange_code(
            code,
            app_id=data.get("app_id", get_setting("fb_app_id")),
            app_secret=data.get("app_secret", get_setting("fb_app_secret"))
        )
        
        if result.get("access_token"):
            page_token = uploader.get_page_token(result["access_token"])
            result["page_token"] = page_token
            
            # Auto-add pages
            if page_token and isinstance(page_token, dict) and page_token.get("all_pages"):
                for p in page_token["all_pages"]:
                    add_fb_page(
                        page_id=p["id"],
                        page_name=p.get("name", ""),
                        access_token=p.get("access_token", "")
                    )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fb/pages-list", methods=["GET"])
def api_fb_pages_list():
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "Token required"}), 400
    
    try:
        import requests as req
        resp = req.get(
            f"https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": token, "fields": "id,name,category,fan_count"}
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ PREVIEW ============

@app.route("/api/preview/<int:job_id>")
def api_preview_video(job_id):
    clip_id = request.args.get("clip_id")
    if clip_id:
        clip = get_clip(int(clip_id))
        if clip and os.path.exists(clip["filepath"]):
            return send_file(clip["filepath"], mimetype="video/mp4")
    return jsonify({"error": "Not found"}), 404


# ============ TRANSLATE API ============

@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.json or {}
    text = data.get("text", "")
    source = data.get("source", "zh")
    target = data.get("target", "id")
    
    try:
        from translator import translate_text
        result = translate_text(text, source, target)
        return jsonify({"translated": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ CONTENT GENERATION ============

@app.route("/api/generate-content", methods=["POST"])
def api_generate_content():
    data = request.json or {}
    try:
        post = generate_full_post(
            title_source=data.get("title", ""),
            genre=data.get("genre"),
            part_number=data.get("part_number", 1),
            total_parts=data.get("total_parts", 1),
            custom_caption=data.get("custom_caption", ""),
            custom_hashtags=data.get("custom_hashtags")
        )
        return jsonify(post)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ INIT ============

def ensure_dirs():
    for d in [DOWNLOADS_DIR, CLIPS_DIR, SUBTITLES_DIR, JOBS_DIR]:
        os.makedirs(d, exist_ok=True)


if __name__ == "__main__":
    ensure_dirs()
    init_db()
    
    # Start scheduler worker
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()
    
    print(f"🎬 Drama Reels Pipeline — FULL EDITION")
    print(f"   http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
