---
name: process_video
description: Crop a full video to vertical 9:16 (TikTok / YouTube Shorts) and trim a random 30s clip into the clips/ folder. Use when the user runs /process_video, or asks to turn a full video into a short clip.
---

# process_video

Usage: `/process_video {input_video} {vid-name} {artist} [output_dir]`

Runs the crop+trim script:

```
python scripts/crop.py "{input_video}" "{output_dir}" "{vid-name}" "{artist}"
```

Default `{output_dir}` to `clips/` when the user doesn't give one.

The script:
- Center-crops to 9:16 at highest native resolution (no upscale, capped at 1080x1920).
- Grabs a random 30s window (or the whole video if shorter than 30s).
- Writes `clips/{vid-name-slug}__{duration}__{artist-slug}.mp4`.

Notes:
- Requires `ffmpeg` + `ffprobe` on PATH.
- On this machine invoke Python as `python`, not `python3`.
- Typically chained after `/download-youtube-video`: download the full video, then process it into a clip.
