"""Video processing engine: download, transcribe, translate, clip, subtitle, watermark, thumbnail."""
import os
import re
import json
import subprocess
import time
import math
from pathlib import Path

# Find ffmpeg binary
def get_ffmpeg():
    """Get ffmpeg binary path."""
    from config import FFMPEG_PATH
    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        return FFMPEG_PATH
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    for p in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
              "ffmpeg.exe", "tools/ffmpeg.exe"]:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG = get_ffmpeg()


def download_video(url, output_dir):
    """Download video using yt-dlp. Returns (filepath, title, duration, metadata)."""
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--print-json",
        "--no-warnings",
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise Exception(f"yt-dlp error: {result.stderr[-500:]}")
    
    info = json.loads(result.stdout.strip().split("\n")[-1])
    filepath = info.get("requested_downloads", [{}])[0].get("filepath") or info.get("_filename", "")
    
    metadata = {
        "title": info.get("title", "Unknown"),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", ""),
        "description": info.get("description", "")[:500],
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "upload_date": info.get("upload_date", ""),
        "thumbnail": info.get("thumbnail", ""),
        "tags": info.get("tags", []),
        "categories": info.get("categories", []),
    }
    
    return filepath, metadata


def transcribe_audio(filepath, language="zh", model_size="base"):
    """Transcribe audio using faster-whisper. Returns list of segments."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return []
    
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments_gen, info = model.transcribe(filepath, language=language, beam_size=5)
    
    segments = []
    for seg in segments_gen:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip()
        })
    
    return segments


def generate_clip(source_path, output_path, start_time, duration,
                  width=1080, height=1920, crf=23, preset="ultrafast"):
    """Generate a single vertical clip from source video."""
    
    filters = []
    filters.append(f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0")
    filters.append(f"scale={width}:{height}:flags=lanczos")
    
    filter_str = ",".join(filters)
    
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", source_path,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"ffmpeg error: {result.stderr[-300:]}")
    
    return output_path


def generate_ass_subtitle(segments, output_path, font_size=28, primary_color="&H00FFFFFF",
                           outline_color="&H00000000", outline_width=2, font_name="Arial"):
    """Generate ASS subtitle file from whisper segments."""
    
    header = f"""[Script Info]
Title: Drama Reels Subtitle
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{outline_width},1,2,20,20,100,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    
    events = []
    for seg in segments:
        start = _format_ass_time(seg["start"])
        end = _format_ass_time(seg["end"])
        text = seg["text"].replace("\n", "\\N")
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(events))
    
    return output_path


def _format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def burn_subtitles(clip_path, ass_path, output_path):
    """Burn ASS subtitles into video clip."""
    safe_ass = ass_path.replace(":", "\\:").replace("'", "\\'")
    
    cmd = [
        FFMPEG, "-y",
        "-i", clip_path,
        "-vf", f"subtitles={safe_ass}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        import shutil
        shutil.copy2(clip_path, output_path)
    
    return output_path


def get_video_duration(filepath):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except:
        pass
    
    cmd2 = [FFMPEG, "-i", filepath]
    result = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if match:
        h, m, s = match.groups()
        return int(h) * 3600 + int(m) * 60 + float(s)
    return 0


def calculate_clip_points(total_duration, clip_duration=45, overlap=5):
    if total_duration <= clip_duration:
        return [0]
    
    points = []
    step = clip_duration - overlap
    t = 0
    while t < total_duration:
        points.append(t)
        t += step
        if total_duration - t < clip_duration * 0.3:
            break
    
    return points


def generate_thumbnail(video_path, output_path, timestamp=None):
    """Generate a thumbnail image from video."""
    if timestamp is None:
        duration = get_video_duration(video_path)
        timestamp = duration * 0.3 if duration > 0 else 5
    
    cmd = [
        FFMPEG, "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920:flags=lanczos",
        "-q:v", "2",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None
    return output_path


def add_watermark_to_clip(video_path, output_path, watermark_text, 
                           position="bottom-right", opacity=0.6, font_size=22):
    """Add text watermark to video clip."""
    
    pos_map = {
        "top-left": "x=10:y=10",
        "top-right": "x=w-tw-10:y=10",
        "bottom-left": "x=10:y=h-th-10",
        "bottom-right": "x=w-tw-10:y=h-th-10",
        "center": "x=(w-tw)/2:y=(h-th)/2"
    }
    pos = pos_map.get(position, pos_map["bottom-right"])
    safe_text = watermark_text.replace("'", "'\\''").replace(":", "\\:")
    
    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-vf", (
            f"drawtext=text='{safe_text}':"
            f"fontsize={font_size}:fontcolor=white@{opacity}:"
            f"borderw=1:bordercolor=black@0.3:"
            f"{pos}"
        ),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        import shutil
        shutil.copy2(video_path, output_path)
    return output_path


def merge_clips(clip_paths, output_path):
    """Merge multiple clips into one video."""
    if len(clip_paths) == 1:
        import shutil
        shutil.copy2(clip_paths[0], output_path)
        return output_path
    
    # Create concat file
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for cp in clip_paths:
            f.write(f"file '{cp}'\n")
    
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    os.remove(concat_file)
    
    if result.returncode != 0:
        raise Exception(f"Merge failed: {result.stderr[-200:]}")
    
    return output_path


def trim_clip(input_path, output_path, start, end):
    """Trim a clip to specific start/end times."""
    duration = end - start
    
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", input_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"Trim failed: {result.stderr[-200:]}")
    
    return output_path


def process_video(url, job_dir, clip_duration=45, language="zh",
                   whisper_model="base", auto_translate=False,
                   watermark_text="", progress_callback=None):
    """
    Full pipeline: download → transcribe → translate → clip → subtitle → watermark → thumbnail.
    Returns dict with clips and metadata.
    """
    downloads_dir = os.path.join(job_dir, "downloads")
    clips_dir = os.path.join(job_dir, "clips")
    subs_dir = os.path.join(job_dir, "subtitles")
    thumbs_dir = os.path.join(job_dir, "thumbnails")
    
    for d in [downloads_dir, clips_dir, subs_dir, thumbs_dir]:
        os.makedirs(d, exist_ok=True)
    
    # Step 1: Download
    if progress_callback:
        progress_callback(5, "Downloading video...")
    
    video_path, metadata = download_video(url, downloads_dir)
    duration = metadata["duration"]
    if not duration or duration <= 0:
        duration = get_video_duration(video_path)
    metadata["duration"] = duration
    
    if progress_callback:
        progress_callback(20, f"Downloaded: {metadata['title']} ({duration:.0f}s)")
    
    # Step 2: Transcribe
    if progress_callback:
        progress_callback(30, "Transcribing audio...")
    
    segments = transcribe_audio(video_path, language=language, model_size=whisper_model)
    
    if progress_callback:
        progress_callback(45, f"Transcribed {len(segments)} segments")
    
    # Step 3: Translate
    translated_segments = None
    if auto_translate and segments:
        if progress_callback:
            progress_callback(50, "Translating subtitles to Indonesian...")
        
        try:
            from translator import translate_segments
            translated_segments = translate_segments(segments, source_lang=language, target_lang="id")
            
            # Save translated ASS
            if translated_segments:
                trans_ass_path = os.path.join(subs_dir, "full_translated.ass")
                generate_ass_subtitle(translated_segments, trans_ass_path)
        except Exception as e:
            print(f"Translation error: {e}")
            translated_segments = segments  # Fallback
    
    if progress_callback:
        progress_callback(55, "Generating clips...")
    
    # Step 4: Generate clips
    clip_points = calculate_clip_points(duration, clip_duration)
    clips = []
    
    # Import content generator
    try:
        from content_gen import generate_full_post, detect_genre
        genre = detect_genre(metadata.get("title", ""), metadata.get("description", ""))
    except:
        genre = "general"
    
    for i, start in enumerate(clip_points):
        if progress_callback:
            pct = 55 + int(35 * (i + 1) / len(clip_points))
            progress_callback(pct, f"Processing clip {i+1}/{len(clip_points)}...")
        
        actual_duration = min(clip_duration, duration - start)
        
        # Find subtitle segments for this clip
        clip_segments = [
            s for s in segments
            if s["start"] >= start - 1 and s["start"] < start + actual_duration
        ]
        
        # Get translated segments for this clip
        clip_translated = None
        if translated_segments:
            clip_translated = [
                s for s in translated_segments
                if s["start"] >= start - 1 and s["start"] < start + actual_duration
            ]
        
        clip_filename = f"clip_{i+1:03d}_{int(start):04d}s.mp4"
        clip_path = os.path.join(clips_dir, clip_filename)
        
        # Generate content metadata
        try:
            post_data = generate_full_post(
                title_source=metadata.get("title", ""),
                genre=genre,
                part_number=i + 1,
                total_parts=len(clip_points)
            )
        except:
            post_data = {
                "title": f"Part {i+1}",
                "caption": "",
                "hashtags": [],
                "description": f"#DramaChina #CDrama #SubtitleIndonesia",
                "genre": genre
            }
        
        try:
            # Generate the clip
            generate_clip(video_path, clip_path, start, actual_duration)
            
            # Generate and burn subtitles (prefer translated)
            subs_to_use = clip_translated if clip_translated else clip_segments
            if subs_to_use:
                ass_filename = f"clip_{i+1:03d}.ass"
                ass_path = os.path.join(subs_dir, ass_filename)
                
                adjusted_segments = []
                for seg in subs_to_use:
                    adjusted_segments.append({
                        "start": max(0, seg["start"] - start),
                        "end": min(actual_duration, seg["end"] - start),
                        "text": seg["text"]
                    })
                
                generate_ass_subtitle(adjusted_segments, ass_path)
                
                sub_clip_path = os.path.join(clips_dir, f"clip_{i+1:03d}_sub.mp4")
                burn_subtitles(clip_path, ass_path, sub_clip_path)
                
                if os.path.exists(sub_clip_path) and os.path.getsize(sub_clip_path) > 0:
                    os.replace(sub_clip_path, clip_path)
            
            # Apply watermark if specified
            if watermark_text:
                wm_path = os.path.join(clips_dir, f"clip_{i+1:03d}_wm.mp4")
                try:
                    add_watermark_to_clip(clip_path, wm_path, watermark_text)
                    if os.path.exists(wm_path) and os.path.getsize(wm_path) > 0:
                        os.replace(wm_path, clip_path)
                except Exception as e:
                    print(f"Watermark error: {e}")
            
            # Generate thumbnail
            thumb_path = os.path.join(thumbs_dir, f"thumb_{i+1:03d}.jpg")
            generate_thumbnail(clip_path, thumb_path)
            
            sub_text = " ".join([s["text"] for s in (clip_translated or clip_segments)[:3]])
            
            clips.append({
                "filename": clip_filename,
                "filepath": clip_path,
                "thumbnail_path": thumb_path if os.path.exists(thumb_path) else "",
                "start": start,
                "duration": actual_duration,
                "subtitle": sub_text[:100] if sub_text else "",
                "index": i + 1,
                "title": post_data["title"],
                "caption": post_data["caption"],
                "hashtags": post_data["hashtags"],
                "genre": post_data["genre"],
                "description": post_data["description"]
            })
            
        except Exception as e:
            print(f"Error generating clip {i+1}: {e}")
            continue
    
    if progress_callback:
        progress_callback(100, f"Done! Generated {len(clips)} clips")
    
    return {
        "clips": clips,
        "metadata": metadata,
        "total_clips": len(clips),
        "duration": duration
    }
