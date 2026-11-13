---
name: search_for_artist_videos
description: Find an artist's tracks and determine which have official (shot/directed) music videos, with real YouTube URLs where possible, then report a per-release count. Use when the user runs /search_for_artist_videos {artist}, or asks which of an artist's songs have official music videos.
---

# search_for_artist_videos

Usage: `/search_for_artist_videos {artist}`

Goal: for each of the artist's releases, find the tracks that have an **official shot/directed music video** (not official audio / lyric / visualizer) **that we can actually download** — meaning a real, playable YouTube (or other yt-dlp-supported) URL. This feeds the downloader, so **a video only counts if it has a downloadable URL.**

**Governing rule: no URL = not counted.** A video that Wikipedia says exists but for which you can't find a real `watch?v=` link is useless to the pipeline. List those separately as "exists, no downloadable URL found" — never in the main count. Wikipedia director credits alone do NOT qualify a video.

Pressure-tested against 12 artists (Kanye, Future, Eminem, Travis Scott, Lil Uzi, Young Thug, ScHoolboy Q, Bktherula, Icytwat, Destroy Lonely, Bryson Tiller, Ty Dolla $ign). The rules below come from where it broke.

## First: pick the artist tier

- **Mainstream (has a Wikipedia videography article):** Wikipedia-first path works well. Kanye/Future/Eminem/Travis/Uzi/Thug/ScHoolboy Q/Bryson/Ty all qualify.
- **Underground (thin or no Wikipedia):** the Wikipedia spine collapses — jump to the underground path. Icytwat (no Wikipedia at all) and Bktherula (no discography page, no tracklists) proved this.

If unsure, try the mainstream path's step 1; if the discography/videography pages don't exist, switch.

## Tooling note
`ctx_fetch_and_index` is broken on this machine (`spawn bun ENOENT`). Use **WebFetch / web-fetch agents** for pages and **WebSearch** for everything else. Spawn one web-fetch agent per batch of pages to keep context small.

## Mainstream path

1. **Discography.** Don't guess the URL. `{Artist}_discography` is often a *disambiguation dead-page* (e.g. `Future_discography`). Search Wikipedia for the real pages — usually `{Artist}_albums_discography` plus a separate **`{Artist}_videography`**. List releases grouped as **studio albums / mixtapes / EPs / compilations / soundtrack+loose singles** — keep these buckets, don't collapse to "studio albums only" (see Gotcha 1).

2. **Videography article is the best source when it exists.** Its "as lead/main performer" table lists every video **with a director credit**, which is how you tell a shot video from an audio upload (Wikipedia never labels a video "official"). Read it verbatim — these tables sit deep in huge pages (100k+ chars) and markdown extraction duplicates/misaligns rows, so re-read to trust director/year pairings. If no videography article, fall back to each album article's "Music videos" prose + targeted director searches.

3. **Tracklists.** Fetch each release's own Wikipedia article for the numbered tracklist. Album URLs need exact disambiguation: `_(album)` or `_(Artist_album)`, with the artist's *real* casing (`Schoolboy_Q_album`, not `ScHoolboy`). Search rather than brute-force suffixes.

4. **Match videos to tracks — by tracklist membership, not release year.** A 2016 video can belong to a 2015 album (Travis "90210"). Fold **deluxe/Side-B/reissue** tracks into their base album. **Count songs-with-a-video, not raw uploads** — one song can have 2-3 video versions (Kanye "Jesus Walks" ×3).

5. **Get real downloadable URLs — this is the whole job, not a finishing touch.** Wikipedia gives titles+directors but almost never `watch?v=` links, so Wikipedia on its own produces zero downloadable results. The YouTube channel is the source of truth. Drive a real browser (Puppeteer / claude-in-chrome) to `youtube.com/@{artist}/videos` (it 404s plain fetchers), read the actual video titles, and capture real `watch?v=` URLs. Also check the artist's **VEVO / topic channels** and official uploads — the official video may live there. Prefer the official upload; a fan reupload is a fallback only. Match each captured URL back to a tracklist. The tables also go stale ~2021, so recent albums look empty on Wikipedia when they aren't — the browser pass is the only way to catch them. Ask the user before launching the browser.

## Underground path (no usable Wikipedia)

1. **MusicBrainz API** for the canonical release list — it returns JSON and is **not blocked**: `https://musicbrainz.org/ws/2/release-group?artist=<mbid>&fmt=json` (resolve the MBID via the artist search endpoint first).
2. **Genius / Discogs / Bandcamp all 403 plain fetchers** — reach them with Puppeteer (renders JS, gets past the block) for tracklists and release info.
3. **Videos:** Puppeteer the artist's real YouTube channel + IMVDb. Expect a floor count; director credits live in scattered one-off blogs, not a central table.
4. Disambiguate the name hard — underground names collide (Icytwat ≠ metal band "Icycore"). Query the exact project names, not just the artist.

## Output format

Only list videos with a real downloadable URL. One row per downloadable video:

```
| Release (type) | song | director | downloadable watch?v= URL |
```
Then: total count of **downloadable** videos (a floor — never claim exhaustive unless the YouTube channel was browsed), and two separate lists below the table: (a) videos that exist but have **no downloadable URL found** (not counted), and (b) unverified eras named as **GAP**s (a real 0 like Kanye's *Ye* differs from an unverified 0 — say which).

The downloadable URLs are the deliverable — they can be handed straight to `/download-youtube-video`.

## Gotchas
1. **Mixtape blindness is the #1 distortion.** For Future/Young Thug/Lil Uzi, the most iconic videos are on mixtapes/compilations, not studio albums. Restricting to studio albums throws away most of the catalog — always report mixtapes as their own bucket.
2. **Album-attribution trap.** Soundtrack, greatest-hits, and standalone singles are not album tracks: Eminem "Lose Yourself"/"Venom", Kanye "Mercy"/"Otis", Travis JackBoys cuts. Filter every candidate against a real tracklist.
3. **Lead-vs-featured contamination.** Artists like Ty Dolla $ign appear on hundreds of features; a raw video search balloons past 100 with other artists' videos. Drop anything not on his own tracklist. Query stylized spellings too (`Ty Dolla $ign`).
4. **Song title vs album name** — "Gemini Love" (a Lucki track) ≠ "GEMINI!" (an album). Don't conflate.
5. **Skits / visualizers / album trailers aren't song videos.** Footnote, don't silently count (Lucki "HUSH SKIT", Uzi "Baby Pluto" trailer, Opium-scene visualizers).
6. **readdork.com is NOT a general source** — it's a UK indie/pop mag with zero coverage of most rap/R&B artists. It only worked for Lucki by chance. Don't rely on it; use the Wikipedia videography article + YouTube channel instead.
