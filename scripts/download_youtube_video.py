#!/usr/bin/env python
"""Download a YouTube video into full_videos/{artist}/{slug}.mp4 and record it in urls.json.

Usage: python download_youtube_video.py <artist> <url> <song-name-slug>
Requires yt-dlp on PATH.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FULL_VIDEOS = REPO / "full_videos"


def slugify(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: download_youtube_video.py <artist> <url> <song-name-slug>")
    artist, url, slug = slugify(sys.argv[1]), sys.argv[2], slugify(sys.argv[3])

    artist_dir = FULL_VIDEOS / artist
    artist_dir.mkdir(parents=True, exist_ok=True)
    out_file = artist_dir / f"{slug}.mp4"

    subprocess.run(
        ["yt-dlp", "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4",
         "-o", str(out_file), url],
        check=True,
    )

    urls_path = artist_dir / "urls.json"
    urls = json.loads(urls_path.read_text()) if urls_path.exists() else {}
    urls[url] = f"{artist}/{slug}.mp4"
    urls_path.write_text(json.dumps(urls, indent=2))
    print(f"saved {out_file}")


if __name__ == "__main__":
    main()
