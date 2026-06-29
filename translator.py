"""Auto-translate subtitles using Google Translate (free)."""
import re
import json
import urllib.request
import urllib.parse
import time


def translate_text(text, source_lang="zh", target_lang="id"):
    """Translate text using Google Translate free API."""
    if not text or not text.strip():
        return text
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    
    full_url = url + "?" + urllib.parse.urlencode(params)
    
    req = urllib.request.Request(full_url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([item[0] for item in data[0] if item[0]])
            return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def translate_segments(segments, source_lang="zh", target_lang="id"):
    """Translate all subtitle segments."""
    translated = []
    
    # Batch translate for efficiency (combine short segments)
    batch_text = []
    batch_indices = []
    
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if text:
            batch_text.append(text)
            batch_indices.append(i)
        
        # Batch every 10 segments or at end
        if len(batch_text) >= 10 or i == len(segments) - 1:
            if batch_text:
                combined = " ||| ".join(batch_text)
                result = translate_text(combined, source_lang, target_lang)
                parts = result.split("|||")
                
                for j, part in enumerate(parts):
                    if j < len(batch_indices):
                        idx = batch_indices[j]
                        while len(translated) <= idx:
                            translated.append(segments[len(translated)].copy())
                        translated[idx]["text"] = part.strip()
                        translated[idx]["translated"] = True
                
                batch_text = []
                batch_indices = []
                time.sleep(0.3)  # Rate limit
    
    # Fill in any untranslated segments
    for i, seg in enumerate(segments):
        if i >= len(translated):
            translated.append(seg.copy())
        elif "translated" not in translated[i]:
            translated[i]["text"] = seg.get("text", "")
    
    return translated


def translate_ass_file(ass_path, output_path, source_lang="zh", target_lang="id"):
    """Translate an ASS subtitle file."""
    with open(ass_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Parse dialogue lines
    lines = content.split("\n")
    translated_lines = []
    
    dialogue_lines = []
    dialogue_indices = []
    
    for i, line in enumerate(lines):
        if line.startswith("Dialogue:"):
            parts = line.split(",", 9)
            if len(parts) >= 10:
                dialogue_lines.append(parts[9])
                dialogue_indices.append(i)
        translated_lines.append(line)
    
    # Batch translate dialogues
    if dialogue_lines:
        # Translate in batches of 15
        for batch_start in range(0, len(dialogue_lines), 15):
            batch = dialogue_lines[batch_start:batch_start + 15]
            combined = " ||| ".join(batch)
            translated = translate_text(combined, source_lang, target_lang)
            parts = translated.split("|||")
            
            for j, part in enumerate(parts):
                idx = batch_start + j
                if idx < len(dialogue_indices):
                    line_idx = dialogue_indices[idx]
                    old_parts = translated_lines[line_idx].split(",", 9)
                    old_parts[9] = part.strip()
                    translated_lines[line_idx] = ",".join(old_parts)
            
            time.sleep(0.3)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(translated_lines))
    
    return output_path
