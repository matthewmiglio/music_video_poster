# music_video_poster

Automated pipeline that builds a library of short vertical clips from music videos and posts one to YouTube on a nightly schedule.

The flow, end to end:

1. Pick popular artists not already in the library.
2. Find their official music videos and resolve real YouTube URLs.
3. Download the full videos.
4. Cut a 30 second vertical (9:16) clip timed around the song's drop.
5. Post one unposted clip per night with a randomized caption.

## Layout

```
scripts/            pipeline steps (all plain Python + ffmpeg + yt-dlp)
  resolve_urls.py       song queries  -> real YouTube URLs (via yt-dlp search)
  download_youtube_video.py  URL      -> full_videos/{artist}/{slug}.mp4
  drop_finder.py        full video    -> detected drop + suggested clip start
  crop.py               full video    -> clips/{slug}__30__{artist}.mp4
  run_batch.py          found_urls.tsv -> download + crop every official row
  post_nightly.py       pick one unposted clip, caption it, upload, log it
.claude/skills/     Claude Code skills wrapping the steps above
full_videos/        downloaded source videos (gitignored; see its CLAUDE.md)
clips/              generated clips + the posted.json ledger (gitignored)
logs/               one log file per nightly post (gitignored)
youtube_uploader/   browser-automation uploader (Playwright, no Data API)
```

Generated media, resolved-URL scratch files, and the logged-in browser profiles are not tracked. See `.gitignore`.

## Setup

```
pip install -r youtube_uploader/requirements.txt
playwright install chromium
```

Also requires `ffmpeg`, `ffprobe`, and `yt-dlp` on PATH.

Log in once so the uploader has a session:

```
python youtube_uploader/login.py --profile <your-account-email>
```

Tell the poster which account to use with the `MVP_PROFILE` environment variable, or put the address in an untracked `scripts/.account` file. With neither set, the uploader auto-detects the single logged-in profile.

## Usage

Grow the library (search, resolve, download, crop):

```
python scripts/resolve_urls.py queries.tsv found_urls.tsv
python scripts/run_batch.py found_urls.tsv
```

`queries.tsv` is tab separated: `artist-slug<TAB>song-slug<TAB>search query`.

Post one clip now:

```
python scripts/post_nightly.py
```

It picks a random clip that is not in `clips/posted.json`, captions it, uploads it as a public Short, writes a log to `logs/`, and records it so the same clip is never posted twice.

## Clip timing

`drop_finder.py` decodes the audio with ffmpeg and derives three signals with numpy: overall loudness (RMS), bass energy in the 20 to 200 Hz band, and spectral flux (onset strength). The drop is the point with the largest sustained energy rise. The clip is cut from 5 seconds before the drop through 25 seconds after. If detection fails, `crop.py` falls back to a point near the middle of the video.

## Nightly schedule

On Windows, `post_nightly.py` is run by a scheduled task (`music_video_poster_nightly`) at a random time each night. Register your own with Task Scheduler pointing at the script.

## Note on content

Re-uploading copyrighted music videos can trigger Content ID claims, copyright strikes, and account termination. Use a throwaway account and keep the posting cadence low.
