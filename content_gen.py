"""Auto-generate hashtags, captions, and titles for drama clips."""
import random

# Chinese drama hashtag sets
HASHTAG_SETS = {
    "drama_china": [
        "#DramaChina", "#CDrama", "#DramaChinaSubIndo", "#Drakorindo",
        "#ChineseDrama", "#DramaChinaRomance", "#DramaChinaAction",
        "#DramaChinaHistorical", "#DramaChinaModern", "#DramaChinaComedy"
    ],
    "general_entertainment": [
        "#FilmSeru", "#NontonOnline", "#SubtitleIndonesia", "#FilmAsia",
        "#DramaAsia", "#ReelsIndonesia", "#FYP", "#Viral",
        "#ReelsViral", "#ExplorePage"
    ],
    "romance": [
        "#DramaRomantis", "#LoveStory", "#RomanceCDrama", "#Cinta",
        "#DramaChinaRomantis", "#LoveDrama", "#SweetDrama",
        "#DramaKorea", "#AsianRomance"
    ],
    "action": [
        "#DramaAction", "#ActionDrama", "#MartialArts", "#Wuxia",
        "#DramaChinaAction", "#FightScene", "#EpicDrama"
    ],
    "historical": [
        "#DramaChinaHistorical", "#CostumeDrama", "#HistoricalDrama",
        "#DramaChinaKlasik", "#DynastyDrama", "#AncientChina"
    ],
    "comedy": [
        "#DramaKomedi", "#ComedyDrama", "#LucuBanget", "#FunnyDrama",
        "#DramaChinaLucu", "#Comedy"
    ],
    "fantasy": [
        "#DramaFantasy", "#FantasyDrama", "#Xianxia", "#Wuxia",
        "#DramaChinaFantasy", "#MagicDrama", "#SupernaturalDrama"
    ]
}

# Caption templates
CAPTION_TEMPLATES = {
    "cliffhanger": [
        "Kamu bakal GAK NYANGKA endingnya! 😱",
        "Tunggu part selanjutnya... ini baru awal! 🔥",
        "Kalau kamu, bakal gimana? Comment di bawah! 💬",
        "Plot twist yang bikin nangis! 😭",
        "Gak ada yang nyangka bakal kayak gini... 😳"
    ],
    "emotional": [
        "Scene ini bikin nangis parah 😭💔",
        "Siapa yang ikut nonton sambil nangis? 😢",
        "Cinta sejati itu memang menyakitkan... 💔",
        "Ini scene paling sedih sepanjang drama! 😭",
        "Kalau kamu di posisi dia, kamu bakal gimana? 💭"
    ],
    "romantic": [
        "Chemistry mereka gak ada lawan! 💕",
        "Scene romantis terbaik sepanjang sejarah drama! ❤️",
        "Couple goals banget sih! 🥰",
        "Ini yang bikin kita semua baper! 😍",
        "Cinta yang gak bisa dipisahkan... 💑"
    ],
    "action": [
        "Scene action terbaik! 🔥⚔️",
        "Gak ada yang bisa ngalahin adegan ini! 💪",
        "Epic banget fight scene-nya! 🥋",
        "Ini baru namanya drama action! 🔥",
        "Wuxia terbaik yang pernah ada! ⚔️"
    ],
    "funny": [
        "Ngakak parah! 🤣",
        "Scene paling lucu sepanjang drama! 😂",
        "Gak kuat nahan ketawa! 🤣🤣",
        "Komedi terbaik! 😆",
        "Lucu banget sampe nangis! 😂😂"
    ],
    "general": [
        "Wajib nonton! 🎬",
        "Drama China terbaik yang wajib kamu tonton! 👑",
        "Part selanjutnya bakal lebih seru! 🔥",
        "Jangan lupa like, comment, dan share! 🙏",
        "Subscribe biar gak ketinggalan episode terbaru! 🔔"
    ]
}


def detect_genre(title="", description=""):
    """Detect drama genre from title and description."""
    text = (title + " " + description).lower()
    
    genre_keywords = {
        "romance": ["love", "romance", "romantic", "cinta", "romantis", "heart", "beloved"],
        "action": ["action", "fight", "martial", "warrior", "war", "battle", "sword"],
        "historical": ["dynasty", "emperor", "palace", "ancient", "historical", "imperial", "concubine"],
        "comedy": ["comedy", "funny", "laugh", "humor", "lucu", "romantic comedy"],
        "fantasy": ["fantasy", "immortal", "xianxia", "wuxia", "magic", "fairy", "demon", "cultivation"]
    }
    
    scores = {}
    for genre, keywords in genre_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[genre] = score
    
    if not scores:
        return "general"
    
    return max(scores, key=scores.get)


def generate_hashtags(genre="general", title="", count=15):
    """Generate relevant hashtags."""
    hashtags = []
    
    # Always include core drama hashtags
    hashtags.extend(random.sample(HASHTAG_SETS["drama_china"], min(5, len(HASHTAG_SETS["drama_china"]))))
    hashtags.extend(random.sample(HASHTAG_SETS["general_entertainment"], min(4, len(HASHTAG_SETS["general_entertainment"]))))
    
    # Add genre-specific hashtags
    if genre in HASHTAG_SETS:
        hashtags.extend(random.sample(HASHTAG_SETS[genre], min(4, len(HASHTAG_SETS[genre]))))
    
    # Deduplicate and limit
    seen = set()
    unique = []
    for h in hashtags:
        h_lower = h.lower()
        if h_lower not in seen:
            seen.add(h_lower)
            unique.append(h)
    
    return unique[:count]


def generate_caption(genre="general", part_number=1, title=""):
    """Generate a caption for the clip."""
    templates = CAPTION_TEMPLATES.get(genre, CAPTION_TEMPLATES["general"])
    template = random.choice(templates)
    
    # Add part number context
    if part_number > 1:
        prefix = f"Part {part_number} — "
    else:
        prefix = ""
    
    # Build full caption
    caption = f"{prefix}{template}"
    
    return caption


def generate_title(title_source, part_number, total_parts):
    """Generate a video title for the clip."""
    # Clean source title
    clean_title = title_source.strip()
    if len(clean_title) > 60:
        clean_title = clean_title[:57] + "..."
    
    if total_parts > 1:
        return f"{clean_title} — Part {part_number}/{total_parts}"
    return clean_title


def generate_full_post(title_source="", genre=None, part_number=1, total_parts=1,
                       custom_caption="", custom_hashtags=None):
    """Generate a complete Facebook post with title, caption, and hashtags."""
    
    # Detect genre if not specified
    if genre is None:
        genre = detect_genre(title_source)
    
    # Generate components
    title = generate_title(title_source, part_number, total_parts)
    caption = custom_caption or generate_caption(genre, part_number, title_source)
    hashtags = custom_hashtags or generate_hashtags(genre, title_source)
    
    # Build full description
    hashtag_str = " ".join(hashtags)
    description = f"{caption}\n\n{hashtag_str}"
    
    return {
        "title": title,
        "caption": caption,
        "hashtags": hashtags,
        "description": description,
        "genre": genre
    }
