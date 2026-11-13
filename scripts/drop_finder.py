#!/usr/bin/env python
"""Find the 'drop' in a track and suggest a 30s clip window around it.

Uses ffmpeg to decode mono audio, then numpy for three framewise signals:
  - RMS (overall loudness)
  - bass energy (20-200 Hz FFT band -- the kick/808 that defines a drop)
  - spectral flux (onset strength -- sudden broadband change)

The drop is the moment with the biggest sustained ENERGY RISE: quiet-ish build
just before, loud sustained section just after. The suggested clip is
{5s before the drop} + {25s after} = 30s.

Usage:
  python drop_finder.py <video>            # print drop + suggested start
  python drop_finder.py <video> --json     # machine-readable
  python drop_finder.py --selfcheck

Requires ffmpeg on PATH + numpy. No librosa (it hangs on this machine).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 11025          # decode rate; plenty for a 20-200 Hz bass band
NFFT = 2048         # ~5.4 Hz/bin -> clean low-end resolution
HOP = SR // 4       # 0.25 s per frame
CLIP = 30
PRE = 5             # seconds of the clip that sit BEFORE the drop
# rise detector windows (seconds): compare "after" loudness to "before"
BEFORE_W = 4.0
AFTER_W = 6.0


def _decode(path):
    """ffmpeg -> mono float32 samples in [-1, 1]."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
         "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def _features(x):
    """Per-frame (hop=0.25s) normalized energy score; returns (times, score)."""
    win = np.hanning(NFFT).astype(np.float32)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    bass = (freqs >= 20) & (freqs <= 200)

    starts = range(0, max(1, len(x) - NFFT), HOP)
    rms, bass_e, flux = [], [], []
    prev = None
    for s in starts:
        frame = x[s:s + NFFT] * win
        rms.append(float(np.sqrt(np.mean(frame * frame)) + 1e-9))
        mag = np.abs(np.fft.rfft(frame))
        bass_e.append(float(mag[bass].sum()))
        flux.append(0.0 if prev is None else float(np.maximum(mag - prev, 0).sum()))
        prev = mag

    def norm(a):
        a = np.asarray(a, dtype=np.float64)
        rng = a.max() - a.min()
        return (a - a.min()) / rng if rng > 1e-12 else np.zeros_like(a)

    # bass-weighted: a drop is mostly "the 808 hits", loudness/onset confirm it
    score = 0.5 * norm(bass_e) + 0.3 * norm(rms) + 0.2 * norm(flux)
    score = _smooth(score, 4)  # ~1 s moving average
    times = np.array([s / SR for s in starts])
    return times, score


def _smooth(a, k):
    if k <= 1 or len(a) < k:
        return a
    kernel = np.ones(k) / k
    return np.convolve(a, kernel, mode="same")


def find_drop(path, total=None):
    """Return the drop time (seconds). Falls back to the loudest moment if no
    clear rise exists."""
    x = _decode(path)
    if total is None:
        total = len(x) / SR
    times, score = _features(x)
    fps = 1.0 / (HOP / SR)  # frames per second
    bw, aw = int(BEFORE_W * fps), int(AFTER_W * fps)

    # Candidate drops must leave room for {PRE before} + {CLIP-PRE after}.
    lo_t, hi_t = PRE, max(PRE, total - (CLIP - PRE))
    best_t, best_rise = None, -1e9
    for i, t in enumerate(times):
        if t < lo_t or t > hi_t:
            continue
        before = score[max(0, i - bw):i]
        after = score[i:i + aw]
        if len(before) == 0 or len(after) == 0:
            continue
        rise = after.mean() - before.mean()
        if rise > best_rise:
            best_rise, best_t = rise, float(t)

    if best_t is None:                      # clip barely fits -> loudest point
        in_range = [(t, score[i]) for i, t in enumerate(times) if lo_t <= t <= hi_t]
        best_t = max(in_range, key=lambda p: p[1])[0] if in_range else lo_t
    return best_t


def suggested_start(path, total=None):
    """Clip start = drop - PRE, clamped so a 30s clip stays inside the video."""
    x = None
    if total is None:
        x = _decode(path)
        total = len(x) / SR
    drop = find_drop(path, total=total)
    return round(min(max(0.0, drop - PRE), max(0.0, total - CLIP)), 3)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not args:
        sys.exit("usage: drop_finder.py <video> [--json]")
    path = args[0]
    x = _decode(path)
    total = len(x) / SR
    drop = find_drop(path, total=total)
    start = round(min(max(0.0, drop - PRE), max(0.0, total - CLIP)), 3)
    if as_json:
        print(json.dumps({"drop": round(drop, 3), "start": start, "total": round(total, 3)}))
    else:
        print(f"{Path(path).name}: drop~{drop:.1f}s -> clip start {start:.1f}s "
              f"(5s pre / 25s post, total {total:.0f}s)")


def _selfcheck():
    # Synthetic score: flat-low build, then a sustained high plateau = the drop.
    # Verify the rise detector lands on the plateau edge, not the noisy peak.
    fps = 1.0 / (HOP / SR)
    total = 90.0
    times = np.arange(0, total, 1 / fps)
    score = np.full_like(times, 0.2)
    drop_at = 40.0
    score[times >= drop_at] = 0.8
    rng = np.random.default_rng(0)
    score = score + rng.normal(0, 0.02, size=score.shape)

    # inline copy of the rise scan against our synthetic arrays
    bw, aw = int(BEFORE_W * fps), int(AFTER_W * fps)
    lo_t, hi_t = PRE, total - (CLIP - PRE)
    best_t, best_rise = None, -1e9
    for i, t in enumerate(times):
        if t < lo_t or t > hi_t:
            continue
        before, after = score[max(0, i - bw):i], score[i:i + aw]
        if len(before) and len(after):
            rise = after.mean() - before.mean()
            if rise > best_rise:
                best_rise, best_t = rise, t
    assert abs(best_t - drop_at) <= 1.5, f"drop found at {best_t}, expected ~{drop_at}"
    start = min(max(0.0, best_t - PRE), total - CLIP)
    assert abs(start - (drop_at - PRE)) <= 1.5, start
    print(f"ok (drop {best_t:.1f}s, start {start:.1f}s)")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main()
