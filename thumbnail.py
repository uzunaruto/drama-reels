"""Thumbnail generator for video clips."""
import os
import subprocess
import json
from config import FFMPEG


def generate_thumbnail(video_path, output_path, timestamp=None, width=1080, height=1920):
    """Generate a thumbnail from video at given timestamp."""
    
    if timestamp is None:
        # Get video duration and use 30%
        duration = get_duration(video_path)
        timestamp = duration * 0.3 if duration > 0 else 5
    
    cmd = [
        FFMPEG, "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale={width}:{height}:flags=lanczos",
        "-q:v", "2",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise Exception(f"Thumbnail generation failed: {result.stderr[-200:]}")
    
    return output_path


def add_watermark(video_path, output_path, watermark_path=None, text=None,
                  position="bottom-right", opacity=0.7, font_size=24):
    """Add watermark (image or text) to video."""
    
    filters = []
    
    # Crop to 9:16 first
    filters.append("crop=ih*9/16:ih:(iw-ih*9/16)/2:0")
    filters.append("scale=1080:1920:flags=lanczos")
    
    if watermark_path and os.path.exists(watermark_path):
        # Image watermark
        pos_map = {
            "top-left": "10:10",
            "top-right": "main_w-overlay_w-10:10",
            "bottom-left": "10:main_h-overlay_h-10",
            "bottom-right": "main_w-overlay_w-10:main_h-overlay_h-10",
            "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
        }
        pos = pos_map.get(position, pos_map["bottom-right"])
        
        # Overlay watermark
        cmd = [
            FFMPEG, "-y",
            "-i", video_path,
            "-i", watermark_path,
            "-filter_complex",
            f"[0:v]{','.join(filters)}[v];[1:v]format=rgba,colorchannelmixer=aa={opacity}[w];[v][w]overlay={pos}[out]",
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-loglevel", "error",
            output_path
        ]
    elif text:
        # Text watermark
        safe_text = text.replace("'", "'\\''").replace(":", "\\:")
        pos_map = {
            "top-left": "x=10:y=10",
            "top-right": "x=w-tw-10:y=10",
            "bottom-left": "x=10:y=h-th-10",
            "bottom-right": "x=w-tw-10:y=h-th-10",
            "center": "x=(w-tw)/2:y=(h-th)/2"
        }
        pos = pos_map.get(position, pos_map["bottom-right"])
        
        filters.append(
            f"drawtext=text='{safe_text}':"
            f"fontsize={font_size}:fontcolor=white@{opacity}:"
            f"borderw=1:bordercolor=black@0.5:"
            f"{pos}"
        )
        
        cmd = [
            FFMPEG, "-y",
            "-i", video_path,
            "-vf", ",".join(filters),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-loglevel", "error",
            output_path
        ]
    else:
        raise Exception("Either watermark_path or text must be provided")
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"Watermark failed: {result.stderr[-200:]}")
    
    return output_path


def add_intro_outro(clip_path, output_path, intro_path=None, outro_path=None):
    """Add intro/outro clips to main clip."""
    if not intro_path and not outro_path:
        import shutil
        shutil.copy2(clip_path, output_path)
        return output_path
    
    # Create concat file
    concat_file = output_path + ".concat.txt"
    files = []
    
    if intro_path and os.path.exists(intro_path):
        files.append(intro_path)
    files.append(clip_path)
    if outro_path and os.path.exists(outro_path):
        files.append(outro_path)
    
    with open(concat_file, "w") as f:
        for fp in files:
            f.write(f"file '{fp}'\n")
    
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
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    os.remove(concat_file)
    
    if result.returncode != 0:
        raise Exception(f"Concat failed: {result.stderr[-200:]}")
    
    return output_path


def add_background_music(video_path, music_path, output_path, volume=0.1):
    """Add background music to video (low volume)."""
    if not os.path.exists(music_path):
        raise Exception(f"Music file not found: {music_path}")
    
    cmd = [
        FFMPEG, "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[0:a]volume=1.0[main];[1:a]volume={volume}[bg];[main][bg]amix=inputs=2:duration=first[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-loglevel", "error",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise Exception(f"Background music failed: {result.stderr[-200:]}")
    
    return output_path


def get_duration(filepath):
    """Get video duration in seconds."""
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
        return 0
