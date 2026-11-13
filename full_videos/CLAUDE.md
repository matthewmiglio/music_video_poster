# full_videos/ structure

Downloaded full music videos live here, one folder per artist.

```
full_videos/
  {artist}/
    urls.json              # maps source URL -> local video file path
    {video-slug}.mp4       # the downloaded video
```

- `{artist}` and `{video-slug}` are lowercase, hyphenated (e.g. `lucki/`, `goodfellas.mp4`).
- One `urls.json` per artist folder. Keys are the source URLs, values are the file path relative to this `full_videos/` dir.

Example `full_videos/lucki/urls.json`:
```json
{
  "https://www.youtube.com/watch?v=6uuL43i-JQY": "lucki/goodfellas.mp4"
}
```
