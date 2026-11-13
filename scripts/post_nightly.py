#!/usr/bin/env python
"""Post one random clip to YouTube with a '{artist} is so fye' caption.

Picks a random clip from clips/ that hasn't been posted yet, derives the artist
from the filename ({slug}__{dur}__{artist}.mp4), and uploads via the copied
youtube_uploader module under the chosen account profile.

Usage: python post_nightly.py [--profile EMAIL]
"""
import argparse
import json
import random
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLIPS = REPO / "clips"
UPLOADER = REPO / "youtube_uploader" / "upload.py"
LEDGER = REPO / "clips" / "posted.json"
LOGS = REPO / "logs"
# Account profile (an email). Kept out of source: set MVP_PROFILE, or drop the
# address in an untracked scripts/.account file. If neither is set, the uploader
# auto-detects the single logged-in profile under youtube_uploader/profiles/.
def _default_profile():
    import os
    env = os.environ.get("MVP_PROFILE")
    if env:
        return env
    acct = Path(__file__).resolve().parent / ".account"
    return acct.read_text(encoding="utf-8").strip() if acct.exists() else None


DEFAULT_PROFILE = _default_profile()
URL_RE = re.compile(r"https?://(?:youtu\.be/|(?:www\.)?youtube\.com/)\S+")


def load_ledger():
    """posted.json: {clip_name: {...meta}}. Migrates old list form (names only)."""
    if not LEDGER.exists():
        return {}
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    if isinstance(data, list):  # old format: just a list of posted filenames
        return {name: {} for name in data}
    return data


def artist_of(clip):
    # {slug}__{dur}__{artist}.mp4
    return clip.stem.split("__")[-1]


def pretty(artist_slug):
    return artist_slug.replace("-", " ").title()


# Caption templates: {a} = artist, {e} = 1-3 random emojis.
TEMPLATES = [
    "{a} is so fye {e}", "{a} don't miss {e}", "nobody doing it like {a} {e}",
    "{a} always goated {e}", "{a} snapped on this one {e}", "{a} too hard {e}",
    "{a} carrying fr {e}", "run it back {a} {e}", "{a} the realest {e}",
    "who checking {a} {e}", "{a} go crazy {e}", "{a} on demon time {e}",
    "{a} wake up pick a struggle {e}", "aura +1000 {a} {e}", "{a} spazzed {e}",
    "{a} ate this no crumbs {e}", "{a} different breed {e}", "{a} cold as hell {e}",
    "forever {a} {e}", "{a} up next {e}", "{a} got the whole hood {e}",
    "{a} in a league of his own {e}", "sheesh {a} {e}", "{a} never lacking {e}",
]
# fire, 100, imp, cold-face, drool, skull, pray, crown, lion, sparkles,
# ice, star, wave, salute, goat, muscle, eyes, exploding-head
EMOJIS = ["\U0001F525", "\U0001F4AF", "\U0001F608", "\U0001F976", "\U0001F924",
          "\U0001F480", "\U0001F64F", "\U0001F451", "\U0001F981", "\U00002728",
          "\U0001F9CA", "\U0001F320", "\U0001F30A", "\U0001FAE1", "\U0001F410",
          "\U0001F4AA", "\U0001F440", "\U0001F92F"]


def make_caption(artist):
    emojis = "".join(random.sample(EMOJIS, random.randint(1, 3)))
    return random.choice(TEMPLATES).format(a=pretty(artist), e=emojis)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=DEFAULT_PROFILE)
    args = ap.parse_args()

    LOGS.mkdir(exist_ok=True)
    started = datetime.now()
    log = LOGS / f"nightly_{started:%Y-%m-%d_%H%M%S}.log"

    posted = load_ledger()
    clips = [c for c in CLIPS.glob("*.mp4") if c.name not in posted]
    if not clips:
        msg = "no unposted clips left"
        print(msg)
        log.write_text(msg + "\n", encoding="utf-8")
        return

    clip = random.choice(clips)
    caption = make_caption(artist_of(clip))
    print(f"posting {clip.name} as: {caption!r} (profile {args.profile})")

    cmd = [sys.executable, str(UPLOADER), "--video", str(clip),
           "--title", caption, "--description", caption]
    if args.profile:  # omit -> uploader auto-detects the single logged-in profile
        cmd += ["--profile", args.profile]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    m = URL_RE.search(out)
    url = m.group(0) if m else None

    meta = {
        "clip": clip.name,
        "artist": pretty(artist_of(clip)),
        "caption": caption,
        "profile": args.profile,
        "url": url,
        "posted_at": started.isoformat(timespec="seconds"),
        "exit_code": r.returncode,
        "ok": r.returncode == 0,
    }
    # One log file per run: metadata header + full uploader output.
    log.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n\n--- uploader output ---\n" + out,
                   encoding="utf-8")

    if r.returncode == 0:
        posted[clip.name] = meta  # dedup key; nothing reposts the same clip
        LEDGER.write_text(json.dumps(posted, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"posted + recorded -> {url or '(no url parsed)'}  | log: {log}")
    else:
        print(f"upload failed (exit {r.returncode}); not recording | log: {log}")
        sys.exit(1)


if __name__ == "__main__":
    main()
