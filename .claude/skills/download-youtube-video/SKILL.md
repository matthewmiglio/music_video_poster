---
name: download-youtube-video
description: Download a YouTube music video into full_videos/{artist}/{slug}.mp4 and record it in that artist's urls.json. Use when the user runs /download-youtube-video, or asks to download/save a YouTube video to this repo.
---

# download-youtube-video

Usage: `/download-youtube-video {artist} {url} {song-name-slug}`

Run the download script, passing the three args through verbatim:

```
python scripts/download_youtube_video.py "{artist}" "{url}" "{song-name-slug}"
```

The script:
- Downloads to `full_videos/{artist}/{song-name-slug}.mp4` (best video+audio, merged to mp4).
- Creates the artist folder if needed.
- Adds/updates `full_videos/{artist}/urls.json`, mapping the source URL to the relative file path.

Notes:
- `{artist}` and `{song-name-slug}` are slugified (lowercased, non-alphanumerics -> `-`).
- Requires `yt-dlp` on PATH.
- On this machine invoke Python as `python`, not `python3`.
