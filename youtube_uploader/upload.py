"""Upload a video to YouTube by driving Studio in the persistent profile.

    python upload.py --video "path\\to\\video.mp4" --title "Title" --description "Desc"
    python upload.py ... --profile alt        # which channel profile to upload as
    python upload.py ... --headed             # show the browser window (default is headless)

Requires a logged-in profile (see login.py). Publishes the video as Public,
audience = "not made for kids".
"""
import argparse
import re
import shutil
import sys
import time
from pathlib import Path

from _common import default_profile, open_context

HERE = Path(__file__).resolve().parent
DEBUG_DIR = HERE / "_debug"  # one <timestamp>_<profile>/ dir of step HTML per run
DEBUG_KEEP_RUNS = 5          # ~40 MB a run; each new run deletes all but the newest 5

# Selectors verified against _example_html/04-09.html (YouTube Studio, 2026-08).
SEL_SELECT_FILES = "#select-files-button"
SEL_TITLE = "#title-textarea #textbox"
SEL_DESC = "#description-textarea #textbox"
SEL_NOT_FOR_KIDS = 'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]'
SEL_NEXT = "#next-button"
SEL_PUBLIC = 'tp-yt-paper-radio-button[name="PUBLIC"]'
SEL_DONE = "#done-button"
# One-time "Remember that anyone can see public videos" notice. It opens over the
# visibility step the first time a channel publishes, and covers the Publish button.
SEL_GOT_IT = "ytcp-aadc-notice-dialog #got-it-button"
SEL_SHARE_URL = "#share-url"
# "We're still checking your content ... Publish anyway / Go back". Opens over Publish
# while YouTube's copyright/policy checks run; a new or flagged channel gets it every
# time. We click "Publish anyway": waiting out the checks can take longer than a nightly
# slot. ponytail: if a channel ever gets a strike from this, switch back to "Go back" + retry.
CHECKS_DIALOG_TEXT = "still checking your content"


# Any one of these visible = upload accepted. "Processing delayed up to a few hours"
# is a success too: the video is queued, it just isn't live this instant.
SUCCESS_TEXTS = ("Processing delayed", "Video processing", "Video published",
                 "Upload complete", "processing will begin")


def _read_share_url(page) -> str:
    el = page.query_selector(SEL_SHARE_URL)
    if el and (el.inner_text() or "").strip():
        return el.inner_text().strip()
    try:  # fallback: the video link is printed on the page regardless of element id
        m = re.search(r"https?://(?:youtu\.be/|youtube\.com/shorts/)\S+", page.inner_text("body"))
        return m.group(0) if m else ""
    except Exception:
        return ""


def _published(page) -> bool:
    """The details dialog is gone (or says published), i.e. Publish actually took."""
    try:
        body = page.inner_text("body")
    except Exception:
        return False
    return "Saved as private" not in body and "Saving..." not in body


def _checks_dialog_open(page) -> bool:
    try:
        loc = page.get_by_text(CHECKS_DIALOG_TEXT, exact=False)
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:
        return False


def _wait_success(page, snap, timeout_ms: int = 180000) -> str:
    """Wait for the video to be published. Studio silently ignores the Publish click while it
    is still 'Saving...' (the dialog stays open, 'Saved as private'), so keep re-clicking
    Publish until the dialog goes away. Re-clicking is idempotent: same video. If the
    'still checking your content' dialog appears, click Publish anyway."""
    end = time.time() + timeout_ms / 1000
    seen_checks = False
    while time.time() < end:
        if _checks_dialog_open(page):
            if not seen_checks:
                seen_checks = True
                snap(page, "checks_dialog")
                print("  YouTube is still checking the video; clicking Publish anyway", flush=True)
            try:
                page.get_by_role("button", name="Publish anyway").first.click(timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(3000)
            continue
        url = _read_share_url(page)
        if url and _published(page):
            return url
        if _published(page):
            for s in SUCCESS_TEXTS:
                loc = page.get_by_text(s, exact=False)
                if loc.count() and loc.first.is_visible():
                    return _read_share_url(page)
        else:
            try:
                btn = page.locator(SEL_DONE)
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=5000)
            except Exception:
                pass
        page.wait_for_timeout(3000)
    raise RuntimeError("no success signal (share link / processing dialog) appeared")


def _fill_contenteditable(page, selector: str, text: str) -> None:
    box = page.locator(selector)
    box.wait_for(state="visible", timeout=60000)
    box.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    if text:
        box.type(text, delay=5)


def latest_debug_run() -> Path | None:
    runs = sorted(p for p in DEBUG_DIR.glob("*") if p.is_dir()) if DEBUG_DIR.is_dir() else []
    return runs[-1] if runs else None


def _snapshotter(profile: str):
    """Make _debug/<timestamp>_<profile>/ for this run, prune old runs, and return a
    snap(page, name) writer. Runs are kept so a failed night can be read the next day."""
    DEBUG_DIR.mkdir(exist_ok=True)
    for f in DEBUG_DIR.glob("*.html"):  # the old flat layout
        f.unlink(missing_ok=True)
    run_dir = DEBUG_DIR / f"{time.strftime('%Y%m%d_%H%M%S')}_{profile}"
    run_dir.mkdir()
    for old in sorted(p for p in DEBUG_DIR.glob("*") if p.is_dir())[:-DEBUG_KEEP_RUNS]:
        shutil.rmtree(old, ignore_errors=True)
    print(f"  step snapshots: {run_dir}", flush=True)
    n = [0]

    def snap(page, name: str) -> None:
        n[0] += 1
        try:
            (run_dir / f"{n[0]:02d}_{name}.html").write_text(page.content(), encoding="utf-8")
        except Exception as e:
            print(f"  (snapshot {name} failed: {e})")

    return snap


def run_upload(video: Path, title: str, description: str, profile: str, headless: bool) -> int:
    snap = _snapshotter(profile)
    pw, ctx = open_context(profile, headless=headless)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.set_default_timeout(60000)
    try:
        # Steps 1-3: go straight to the upload dialog (equivalent to Create > Upload video).
        page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded")
        # A dead session bounces here to the Google login page, and every later step then
        # fails as a plain selector timeout. Name it now so the batch driver can tell an
        # expired login from an ordinary flake and email about it.
        if "accounts.google.com" in page.url or "ServiceLogin" in page.url:
            raise RuntimeError("AUTH_EXPIRED: upload page redirected to Google login (session dead)")
        snap(page, "upload_page")

        # Step 4: hand the file to the picker triggered by "Select files".
        with page.expect_file_chooser(timeout=60000) as fc:
            page.click(SEL_SELECT_FILES)
        fc.value.set_files(str(video))

        # Step 5/6: details page. Title box appears once the upload starts.
        _fill_contenteditable(page, SEL_TITLE, title)
        _fill_contenteditable(page, SEL_DESC, description)
        page.locator(SEL_NOT_FOR_KIDS).click()
        snap(page, "details_filled")

        # Steps 6-8: click Next until the visibility step (Public radio) shows up.
        # ponytail: step count varies (monetization step is conditional) -> loop, don't hardcode 3.
        for i in range(6):
            if page.locator(SEL_PUBLIC).is_visible():
                break
            snap(page, f"step_{i+1}")
            page.click(SEL_NEXT)
            page.wait_for_timeout(1200)
        else:
            snap(page, "no_visibility_step")
            raise RuntimeError("never reached the visibility step (Public radio not found)")

        # Step 9: make it Public and save.
        page.locator(SEL_PUBLIC).click()
        snap(page, "visibility_public")
        # ponytail: fixed 3s wait for a notice that only shows once per channel; if Studio
        # ever opens it later than that, raise the wait rather than adding a poll loop.
        got_it = page.locator(SEL_GOT_IT)
        try:
            got_it.wait_for(state="visible", timeout=3000)
            got_it.click()
        except Exception:
            pass  # not shown: the usual case once a channel has published before
        page.click(SEL_DONE)

        # Step 10: success = share link OR a processing/published dialog appears.
        share = _wait_success(page, snap)
        snap(page, "success")
        print(f"OK: published (may still be processing). {share}".rstrip())
        return 0
    except Exception as e:
        snap(page, "error")
        # Google's "Verify it's you" challenge lands as an overlay mid-upload and every
        # click then times out behind it. Only a human can clear it, so report it as
        # AUTH_EXPIRED: that is the marker ad_batch.py emails about.
        try:
            challenged = "Verify it" in page.inner_text("body")
        except Exception:
            challenged = False
        if challenged:
            print("ERROR during upload: AUTH_EXPIRED: Google is asking to verify it's you. "
                  "Sign in again with login.py and complete the check.")
        else:
            print(f"ERROR during upload: {e}")
        return 1
    finally:
        ctx.close()
        pw.stop()


def main() -> int:
    ap = argparse.ArgumentParser(description="Upload a video to YouTube via Studio.")
    ap.add_argument("--video", required=True, help="path to the video file")
    ap.add_argument("--title", required=True, help="video title")
    ap.add_argument("--description", default="", help="video description")
    ap.add_argument("--profile", default=None, help="channel profile name, e.g. an e-mail (default: the only one logged in)")
    ap.add_argument("--headed", action="store_true", help="show the browser window (default is headless)")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.is_file():
        print(f"ERROR: video not found: {video}")
        return 2

    return run_upload(video, args.title, args.description,
                      args.profile or default_profile(), not args.headed)


if __name__ == "__main__":
    sys.exit(main())
