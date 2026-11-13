#!/usr/bin/env python
"""Resolve song titles to real YouTube URLs via yt-dlp search (no fabrication).

Input: TSV on stdin or a file, columns: artist<TAB>slug<TAB>query
Output: TSV: artist<TAB>slug<TAB>url<TAB>resolved_title<TAB>channel  (printed + written to out path)

Usage: python resolve_urls.py <queries.tsv> <out.tsv>
"""
import subprocess
import sys


def resolve(query):
    """Return (url, title, channel) for the top YouTube hit, or None."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--no-warnings", "--skip-download", "--no-playlist",
             "--print", "%(id)s\t%(title)s\t%(channel)s",
             f"ytsearch1:{query}"],
            capture_output=True, text=True, timeout=60,
        )
        line = out.stdout.strip().splitlines()
        if not line:
            return None
        vid, title, channel = (line[0].split("\t") + ["", ""])[:3]
        return f"https://www.youtube.com/watch?v={vid}", title, channel
    except Exception as e:
        return ("ERROR", str(e), "")


def main():
    rows = [l.rstrip("\n").split("\t") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        for artist, slug, query in rows:
            r = resolve(query)
            url, title, channel = r if r else ("NOTFOUND", "", "")
            f.write(f"{artist}\t{slug}\t{url}\t{title}\t{channel}\n")
            f.flush()
            print(f"{artist}\t{slug}\t{url}\t{title[:50]}\t{channel[:30]}")


if __name__ == "__main__":
    main()
