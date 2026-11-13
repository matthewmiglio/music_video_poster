---
name: ingestion
description: End-to-end pipeline — pick popular rappers not already in the repo, find their official music videos, resolve real YouTube URLs, download, and process into clips. Use when the user runs /ingestion, or asks to ingest/grow the clip library.
---

# ingestion

Usage: `/ingestion [count]` — ingest `count` new artists (default 3).

Runs the full chain for artists **we don't already have**, reusing the existing skills/scripts. Don't reinvent any step — call the pieces below.

## Step 1 — pick NEW popular rappers

- "We have" = the folders in `full_videos/`. List them: `ls full_videos/` (each subfolder is an artist slug we've already ingested).
- Propose `count` popular rappers whose slug is **not** already a folder. Use well-known names with real video catalogs (so the pipeline has something to find). Skip anyone already present.
- Show the user the proposed list and get a quick confirm before spending the download time.

## Step 2 — find their videos

For each new artist, run the research in `/search_for_artist_videos` (see that skill):
- Mainstream artists: Wikipedia `{Artist}_videography` + album tracklists.
- Underground: MusicBrainz API + Puppeteer (Genius/Discogs/Bandcamp 403 plain fetchers).
- Spawn one agent per artist (parallel) to return the list of **official-video song titles** per album. Titles only here; URLs come next.

## Step 3 — resolve URLs

Turn titles into real YouTube URLs with the resolver (no AI, just YouTube search — returns the top real hit + channel for verification):

1. Write a TSV `artist<TAB>slug<TAB>query` where query is `{Artist} {Song} official music video`.
2. `python scripts/resolve_urls.py <queries.tsv> found_urls.tsv`
3. Keep only rows on **official channels** (artist / VEVO / label). Drop reupload channels and NOTFOUND rows — eyeball the `channel` column. **Governing rule from `/search_for_artist_videos`: no real URL = not ingested.**

## Step 4 + 5 — download and process

Run the batch driver (download → crop → clip, idempotent, skips anything already done):

```
python scripts/run_batch.py
```

It reads `found_urls.tsv`, skips the blocked/reupload channels, downloads each full video to `full_videos/{artist}/` (recording `urls.json`), and crops a random 30s 9:16 clip to `clips/{slug}__30__{artist}.mp4`.

Run it in the **background** — it's ~many large downloads. Report when done or if failures pile up.

## Notes
- The blocklist of reupload channels lives in `run_batch.py` (`BLOCK`). Add to it when a bad channel slips through.
- `ctx_fetch_and_index` is broken on this machine (`spawn bun ENOENT`) — use WebFetch/web-fetch agents for research.
- Idempotent throughout: re-running skips artists/clips already present, so a crashed run just resumes.
