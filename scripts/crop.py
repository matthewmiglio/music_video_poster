#!/usr/bin/env python
"""Crop a video to vertical 9:16 (TikTok / YouTube Shorts) at the highest native
resolution possible (no upscaling, capped at 1080x1920) and grab a random 30s clip.

Usage: python crop.py <input_video> <output_dir> <vid-name> <artist>
Output: <output_dir>/{vid-name-slug}__{duration}__{artist-slug}.mp4
Requires ffmpeg + ffprobe on PATH.
"""
import json
import random
import subprocess
import sys
from pathlib import Path

CLIP_SECONDS = 30


def slugify(s):
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def duration_seconds(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


INTRO_SKIP = 30  # skip opening where the video is long enough to afford it


def pick_start(total, clip=CLIP_SECONDS):
    """Start somewhere in the middle of the video, skipping the first 30s where
    possible. Picks randomly within the middle half of the valid start range."""
    latest = max(0, total - clip)            # last start where the clip still fits
    lo = INTRO_SKIP if latest >= INTRO_SKIP else 0
    span = latest - lo
    return round(random.uniform(lo + span * 0.25, lo + span * 0.75), 3)


def main():
    if len(sys.argv) != 5:
        sys.exit("usage: crop.py <input_video> <output_dir> <vid-name> <artist>")
    inp, out_dir, name, artist = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    out_dir.mkdir(parents=True, exist_ok=True)

    total = duration_seconds(inp)
    clip = min(CLIP_SECONDS, int(total))

    # Prefer timing the clip around the detected drop (5s pre / 25s post);
    # fall back to the middle-of-video heuristic if detection fails.
    start = None
    if clip == CLIP_SECONDS:
        try:
            import drop_finder
            start = drop_finder.suggested_start(inp, total=total)
            print(f"drop-timed start: {start}s")
        except Exception as e:
            print(f"drop detection failed ({e}); using middle heuristic")
    if start is None:
        start = pick_start(total, clip)

    out_file = out_dir / f"{slugify(name)}__{clip}__{slugify(artist)}.mp4"

    # Center-crop to 9:16, then downscale to fit 1080x1920 (no upscale).
    vf = ("crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
          "scale='min(iw,1080)':-2")

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-i", str(inp), "-t", str(clip),
         "-vf", vf, "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", str(out_file)],
        check=True,
    )
    print(f"saved {out_file} (start={start}s, {clip}s)")


def _selfcheck():
    # long video: skip intro, land in the middle half (40-60s of a 100s clip range)
    s = pick_start(100, 30)
    assert 40 <= s <= 60, s
    # short video can't skip 30s and still fit -> start from 0, stays in middle half
    assert pick_start(35, 30) <= 5
    assert pick_start(30, 30) == 0  # exactly clip-length -> only start is 0
    assert slugify("Super Urus!") == "super-urus"
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selfcheck":
        _selfcheck()
    else:
        main()
