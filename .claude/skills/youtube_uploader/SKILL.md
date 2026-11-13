---
name: youtube_uploader
description: Upload a clip to YouTube via the browser-automation uploader (no API/quota), or post a random clip nightly with a "{artist} is so fye" caption. Use when the user runs /youtube_uploader, or asks to upload/post a clip to YouTube.
---

# youtube_uploader

Browser-automation YouTube uploader copied from the ChessPecker monorepo. Drives YouTube Studio with Playwright (no Data API, no quota). Lives in `youtube_uploader/`.

## Account
Posts as whichever account's browser profile lives under `youtube_uploader/profiles/<email>/` (gitignored — cookies/credentials never leave the machine). The profile to use comes from `$MVP_PROFILE` or an untracked `scripts/.account` file; with neither set, the uploader auto-detects the single logged-in profile. Re-auth with `python youtube_uploader/login.py --profile <email>`; check with `python youtube_uploader/login.py --check`.

## Upload one clip
```
python youtube_uploader/upload.py --video "clips/<file>.mp4" --title "Title" --description "Desc"
```
Headless by default (`--headed` to watch). Publishes **Public**, not-for-kids. Exit 0 + `youtu.be` URL on success.

## Nightly auto-post
```
python scripts/post_nightly.py
```
Picks a random not-yet-posted clip from `clips/`, derives the artist from the filename, captions it `"{Artist} is so fye 🔥"`, uploads, and records it in `clips/posted.json` so it never double-posts. This is what the Windows scheduled task `music_video_poster_nightly` runs.

## Setup (once, if moving machines)
```
pip install -r youtube_uploader/requirements.txt
playwright install chromium
```

## Caveat
Re-uploading copyrighted music videos risks Content ID claims, copyright strikes, and account termination — the module's own notes say bans come from content + velocity, not the transport. One/night keeps a human cadence; the account is still at risk.
