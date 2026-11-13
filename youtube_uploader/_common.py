"""Shared browser helpers for the Playwright-based YouTube uploader.

One persistent Chromium profile per channel lives under profiles/<profile>/.
Log in once (login.py) and the cookies persist there across runs.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright

HERE = Path(__file__).resolve().parent
PROFILES_DIR = HERE / "profiles"

# A real-ish desktop UA; the default headless UA is an obvious bot flag.
# ponytail: hard-coded UA, bump it if Studio starts complaining about browser version.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def profile_path(profile: str) -> Path:
    p = PROFILES_DIR / profile
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_profile() -> str:
    """The profile to use when none was named on the command line.

    Named profiles are e-mail addresses (see claude.md), so there is no sensible
    literal to fall back on. With exactly one logged in, that is obviously the
    one meant; with several, refuse rather than guess which channel to publish as.
    """
    found = sorted(d.name for d in PROFILES_DIR.glob("*") if d.is_dir() and not d.name.startswith("_"))
    if len(found) == 1:
        return found[0]
    if not found:
        raise SystemExit("No profile is logged in. Run: python login.py --profile <email>")
    raise SystemExit("Several profiles exist; name one with --profile: " + ", ".join(found))


def open_context(profile: str, headless: bool) -> tuple[Playwright, BrowserContext]:
    """Launch (or reopen) the persistent context for a channel profile.

    Caller owns cleanup: context.close() then pw.stop().
    """
    pw = sync_playwright().start()
    kwargs = dict(
        user_data_dir=str(profile_path(profile)),
        headless=headless,
        slow_mo=int(os.environ.get("YT_SLOWMO", "0")),  # ms between ops; keystrokes stay fast
        viewport={"width": 1280, "height": 900},
        user_agent=_UA,
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        ctx = pw.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception:
        # Real Chrome not installed -> use Playwright's bundled Chromium.
        ctx = pw.chromium.launch_persistent_context(**kwargs)
    return pw, ctx
