from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.db.session import init_db, get_session_factory

from app.core.config import get_settings
from app.models.learning import LearningContent, extract_youtube_id

settings = get_settings()

try:
    import yt_dlp
except ImportError:
    print("Error: 'yt-dlp' is not installed.")
    print("Please run: pip install yt-dlp")
    sys.exit(1)

# Topics / Videos configured in the prompt
INDIVIDUAL_VIDEOS = [
    {"url": "https://www.youtube.com/watch?v=EcqtztE4QrY", "fallback_category": "Menstrual Health"},
    {"url": "https://www.youtube.com/watch?v=43W1MRgQ9X8", "fallback_category": "Periods"},
]

ADDITIONAL_VIDEOS = [
    {"url": "https://youtu.be/uzR70T4fnFY?si=X89C7CHAB0ubWNfv"},
    {"url": "https://youtu.be/e_A0zZlP_Fs?si=m2ydarV1eoaoha1B"},
    {"url": "https://youtu.be/rYtAYWCiBoU?si=jOlGlYmMzb1SUwPn"},
    {"url": "https://youtu.be/d1cm0voCLwo?si=NgTeTNnyhE5lWEzo"},
    {"url": "https://youtu.be/ZVTWGhDU27E?si=4bjBeFC7WOHKDdn2"},
    {"url": "https://youtu.be/bXwmjPrg0wk?si=j9TYvDP10fgNU2ZD"},
    {"url": "https://youtu.be/p3wuQQJqQps?si=7WB2KiAyR87swyFa"},
    {"url": "https://youtu.be/Ry2aN0w78qw?si=i8D1UnjijKUJWu9-"},
]

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL0K84nc6F_9vOxnCulm-xCHEWT9FdCbsZ"

# Simple heuristic mapping to map youtube titles/descriptions to Sakhi categories
CATEGORY_MAPPING = {
    "period": "Periods",
    "menstrual": "Menstrual Health",
    "pcos": "PCOS",
    "pregnancy": "Pregnancy",
    "nutrition": "Nutrition",
    "diet": "Nutrition",
    "fitness": "Fitness",
    "exercise": "Fitness",
    "mental": "Mental Health",
    "reproductive": "Reproductive Health",
    "wellness": "Wellness",
    "hygiene": "Personal Hygiene",
}

def determine_category(title: str, description: str, fallback: str = "Women's Health") -> str:
    combined = f"{title} {description}".lower()
    for keyword, category in CATEGORY_MAPPING.items():
        if keyword in combined:
            return category
    return fallback

def generate_tags(title: str, description: str, category: str) -> list[str]:
    combined = f"{title} {description}".lower()
    tags = [category]
    for keyword, cat in CATEGORY_MAPPING.items():
        if keyword in combined and cat not in tags:
            tags.append(cat)
    # Add a few contextual tags
    if "hygiene" in combined: tags.append("Hygiene")
    if "health" in combined: tags.append("Women's Health")
    if "care" in combined: tags.append("Care")
    
    # Return unique top 5-6 tags
    return list(dict.fromkeys(tags))[:6]

def get_thumbnail(video_id: str) -> str:
    # Use maxresdefault, fallback to hqdefault
    return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

def main():
    print("=" * 80)
    print("Sakhi AI - YouTube Learning Content Import")
    print("=" * 80)
    
    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    
    ydl_opts = {
        'extract_flat': False,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'nocheckcertificate': True,
    }
    
    results = []
    stats = {
        "Total individual videos": len(INDIVIDUAL_VIDEOS),
        "Total additional videos": len(ADDITIONAL_VIDEOS),
        "Total playlist videos": 0,
        "Total unique videos": 0,
        "Total imported": 0,
        "Total skipped": 0,
        "Total duplicates": 0,
        "Total unavailable": 0,
        "Total failed": 0,
    }

    videos_to_process = []

    # 1. Individual Videos
    for vid in INDIVIDUAL_VIDEOS:
        videos_to_process.append({
            "url": vid["url"],
            "source": "Individual",
            "fallback_category": vid.get("fallback_category", "Women's Health")
        })

    # 2. Additional Videos
    for vid in ADDITIONAL_VIDEOS:
        videos_to_process.append({
            "url": vid["url"],
            "source": "Additional",
            "fallback_category": "Women's Health"
        })

    # 3. Playlist
    print("Fetching playlist metadata... (this may take a moment)")
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'quiet': True, 'nocheckcertificate': True}) as ydl:
        try:
            playlist_info = ydl.extract_info(PLAYLIST_URL, download=False)
            if playlist_info and 'entries' in playlist_info:
                entries = playlist_info['entries']
                stats["Total playlist videos"] = len(entries)
                for entry in entries:
                    if not entry:
                        continue
                    v_id = entry.get('id')
                    if v_id:
                        videos_to_process.append({
                            "url": f"https://www.youtube.com/watch?v={v_id}",
                            "source": "Playlist",
                            "fallback_category": "Women's Health"
                        })
        except Exception as e:
            print(f"Playlist fetch failed: {e}")
            stats["Total failed"] += 1

    unique_urls = {}
    for v in videos_to_process:
        vid_id = extract_youtube_id(v["url"])
        if vid_id and vid_id not in unique_urls:
            v["id"] = vid_id
            unique_urls[vid_id] = v
        else:
            stats["Total duplicates"] += 1

    stats["Total unique videos"] = len(unique_urls)

    print(f"\nFound {len(unique_urls)} unique videos to process. Starting import...\n")
    print(f"{'#':<4} | {'Source':<12} | {'Video ID':<12} | {'Official Title':<30} | {'Status':<15}")
    print("-" * 80)

    with SessionLocal() as db:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for idx, (vid_id, v_data) in enumerate(unique_urls.items(), 1):
                url = f"https://www.youtube.com/watch?v={vid_id}"
                
                # Check if it already exists in DB
                existing = db.query(LearningContent).filter(LearningContent.media_url.ilike(f"%{vid_id}%")).first()
                if existing:
                    print(f"{idx:<4} | {v_data['source']:<12} | {vid_id:<12} | {existing.title[:27]+'...':<30} | {'DUPLICATE (SKIPPED)'}")
                    stats["Total skipped"] += 1
                    stats["Total duplicates"] += 1
                    
                    results.append({
                        "id": vid_id,
                        "title": existing.title,
                        "category": existing.category,
                        "status": "DUPLICATE"
                    })
                    continue

                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    info = None
                
                if not info:
                    print(f"{idx:<4} | {v_data['source']:<12} | {vid_id:<12} | {'<UNAVAILABLE>':<30} | {'UNAVAILABLE'}")
                    stats["Total unavailable"] += 1
                    results.append({
                        "id": vid_id,
                        "title": "Unavailable",
                        "status": "BLOCKED_METADATA"
                    })
                    continue

                title = info.get("title", f"Video {vid_id}")
                description = info.get("description", "")
                author = info.get("uploader", "YouTube Creator")
                language = info.get("language", "en") or "en"
                duration = info.get("duration", 0)
                duration_mins = duration // 60 if duration else 0
                
                category = determine_category(title, description, fallback=v_data["fallback_category"])
                tags = generate_tags(title, description, category)
                
                # Use maxresdefault if possible
                thumbnail = f"https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg"
                
                new_content = LearningContent(
                    title=title,
                    description=description[:2000] if description else "",
                    content_type="VIDEO",
                    source_type="YOUTUBE",
                    media_url=url,
                    thumbnail_url=thumbnail,
                    category=category,
                    tags=tags,
                    language=language[:10],
                    author_id="system-import", # Use a generic author ID since no users table FK constraints
                    status="PUBLISHED",
                    duration_minutes=duration_mins
                )
                
                db.add(new_content)
                db.commit()
                
                print(f"{idx:<4} | {v_data['source']:<12} | {vid_id:<12} | {title[:27]+'...':<30} | {'IMPORTED'}")
                stats["Total imported"] += 1
                results.append({
                    "id": vid_id,
                    "title": title,
                    "category": category,
                    "tags": tags,
                    "language": language,
                    "channel": author,
                    "thumbnail": thumbnail,
                    "status": "IMPORTED"
                })

    print("\n" + "=" * 80)
    print("1. IMPORT SUMMARY")
    print("=" * 80)
    for k, v in stats.items():
        print(f"{k:<30}: {v}")
    
    print("\n" + "=" * 80)
    print("2. COMPLETE VIDEO LIST")
    print("=" * 80)
    for r in results:
        print(f"{r['id']:<12} | {r['status']:<15} | {r.get('category', ''):<20} | {r['title'][:40]}")

if __name__ == "__main__":
    main()
