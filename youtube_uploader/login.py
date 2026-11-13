"""Log in a YouTube channel into a persistent browser profile, or check it.

    python login.py                      # open youtube.com; you sign in by hand, then close/Enter
    python login.py --check              # report whether the saved profile is still signed in
    python login.py --profile <email>    # name a channel; needed for the first login

Profiles are named after the signed-in account. With exactly one logged in,
--profile can be left off.

The profile (cookies etc.) is stored under profiles/<profile>/ and reused by
upload.py, so you only ever log in once per channel.
"""
import argparse
import sys

from _common import default_profile, open_context, profile_path


def do_login(profile: str) -> int:
    pw, ctx = open_context(profile, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.youtube.com", wait_until="domcontentloaded")
    print(f"\nProfile: {profile_path(profile)}")
    print("A browser window opened. Sign in to the Google/YouTube account you want.")
    print("When you see yourself logged in, come back here and press Enter to save + close.")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    ctx.close()
    pw.stop()
    print("Saved. Run `python login.py --check` to verify.")
    return 0


def _signed_in(page) -> bool:
    # Avatar button exists only when signed in; the "Sign in" link only when not.
    if page.query_selector("button#avatar-btn"):
        return True
    if page.query_selector('a[aria-label="Sign in"], ytd-button-renderer a[href*="ServiceLogin"]'):
        return False
    # Fallback: ask the page's own signed-in flag.
    try:
        return bool(page.evaluate("() => !!(window.ytInitialData && document.querySelector('#avatar-btn'))"))
    except Exception:
        return False


def do_check(profile: str, headless: bool) -> int:
    pw, ctx = open_context(profile, headless=headless)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    ok = True
    reasons = []
    try:
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        if not _signed_in(page):
            ok = False
            reasons.append("not signed in (no account avatar found)")

        # Upload capability sanity: Studio must load without bouncing to the login page.
        page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        url = page.url
        if "accounts.google.com" in url or "ServiceLogin" in url:
            ok = False
            reasons.append("Studio redirected to Google login (session dead)")

        # Best-effort suspension / channel-name read.
        # ponytail: ban detection is heuristic; a real terminated channel shows a
        # notice in Studio. We scan visible text for the obvious phrases only.
        body = (page.inner_text("body")[:4000] if page.query_selector("body") else "").lower()
        for phrase in ("has been terminated", "account has been suspended",
                       "channel was removed", "violated"):
            if phrase in body:
                ok = False
                reasons.append(f"Studio page mentions: '{phrase}'")
                break

        handle = None
        for sel in ("ytcp-channel-name #entity-name", "#channel-name #entity-name",
                    "#entity-name"):
            el = page.query_selector(sel)
            if el:
                handle = (el.inner_text() or "").strip()
                if handle:
                    break
    finally:
        ctx.close()
        pw.stop()

    if ok:
        who = f" ({handle})" if handle else ""
        print(f"PASS: profile '{profile}' is signed in and can reach Studio{who}.")
        return 0
    print(f"FAIL: profile '{profile}':")
    for r in reasons:
        print(f"  - {r}")
    print("Run `python login.py --profile " + profile + "` to (re)authenticate.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Log in / verify a YouTube channel profile.")
    ap.add_argument("--check", action="store_true", help="validate the saved login instead of opening it")
    ap.add_argument("--profile", default=None, help="channel profile name, e.g. an e-mail (default: the only one logged in)")
    ap.add_argument("--headed", action="store_true", help="run --check with a visible window (default is headless)")
    args = ap.parse_args()

    # No literal fallback: profiles are named after the account (see claude.md).
    profile = args.profile or default_profile()
    if args.check:
        return do_check(profile, headless=not args.headed)
    return do_login(profile)


if __name__ == "__main__":
    sys.exit(main())
