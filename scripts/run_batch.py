#!/usr/bin/env python
"""Download + process every official-channel row in found_urls.tsv.

Reads found_urls.tsv (artist, slug, url, title, channel), skips non-official
channels and NOTFOUND rows, then for each: download full video, crop to a clip.
Idempotent: skips rows whose clip already exists.

Usage: python run_batch.py
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "found_urls.tsv"
CLIPS = REPO / "clips"

# Reupload / wrong-hit channels to skip (official-only run).
BLOCK = {"channelzerotv", "Tony Williams", "Video Archives", "[UNRLSD]",
         "BEEF TV", "RappersClip", "#VEVOCertified", "",
         "US Trill Music", "Angry Studios", "ZeldTheAlchemist",
         "Ye (Kanye West) Live Performances", "WORLDSTARHIPHOP",
         "LyricalOranged", "B A R T H O O D TV"}


def done(artist, slug):
    return any(CLIPS.glob(f"{slug}__*__{artist}.mp4"))


def main():
    rows = [l.rstrip("\n").split("\t") for l in open(TSV, encoding="utf-8") if l.strip()]
    todo = [r for r in rows if len(r) >= 5 and r[2].startswith("http")
            and r[4] not in BLOCK]
    print(f"{len(todo)} official-channel videos to process")

    for i, (artist, slug, url, title, channel) in enumerate(todo, 1):
        if done(artist, slug):
            print(f"[{i}/{len(todo)}] skip (clip exists): {artist}/{slug}")
            continue
        print(f"[{i}/{len(todo)}] {artist}/{slug}  [{channel}]")
        try:
            subprocess.run([sys.executable, str(REPO / "scripts/download_youtube_video.py"),
                            artist, url, slug], check=True)
            full = REPO / "full_videos" / artist / f"{slug}.mp4"
            subprocess.run([sys.executable, str(REPO / "scripts/crop.py"),
                            str(full), str(CLIPS), slug, artist], check=True)
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {artist}/{slug}: {e}")
    print("batch complete")


if __name__ == "__main__":
    main()
