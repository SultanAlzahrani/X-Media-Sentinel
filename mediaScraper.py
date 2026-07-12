#!/usr/bin/env python3
"""
mediaScraper.py

Watches an X (Twitter) account URL and downloads any NEW photos/videos
as they get posted, polling at a set interval.

Requires: gallery-dl  (pip install gallery-dl --break-system-packages)

X now requires an authenticated session for most media access, so you'll
need to give gallery-dl your login cookies once. Two ways to do that:

  1. Cookie file (recommended): export cookies from your browser
     (e.g. with the "Get cookies.txt LOCALLY" extension) while logged into
     x.com, save as cookies.txt, and pass its path with --cookies.

  2. username/password in gallery-dl's config file (~/.gallery-dl.conf) -
     less reliable due to X's login challenges.

Usage:
    py mediaScraper.py https://x.com/someaccount \
        --out ./downloads --cookies cookies.txt --interval 300

Notes on rate limiting:
    X aggressively throttles repeated profile scans from the same cookie
    session. Every restart forces gallery-dl to walk the whole timeline
    again (the archive file only prevents re-downloading, not re-scanning),
    so restarting frequently or using a short --interval can get you
    rate-limited or make a single check take a long time / hang. If that
    happens, this script will time out the stuck run (see --timeout) and
    just try again on the next cycle rather than freezing forever.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Call gallery-dl as "python -m gallery_dl" instead of the bare "gallery-dl"
# command. This avoids relying on gallery-dl's script being on PATH, which
# is the cause of "FileNotFoundError: [WinError 2]" on Windows when pip
# installs it to a Scripts folder that isn't on PATH.
GALLERY_DL_CMD = [sys.executable, "-m", "gallery_dl"]


def ts() -> str:
    """Current time as a short timestamp string for log lines."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_seen(seen_file: Path) -> set:
    if seen_file.exists():
        return set(json.loads(seen_file.read_text()))
    return set()


def save_seen(seen_file: Path, seen: set):
    seen_file.write_text(json.dumps(sorted(seen)))


def run_streamed(cmd, timeout: int):
    """
    Run a command, printing each line of output live (with a timestamp) as
    it arrives, instead of buffering everything until the process exits.
    If the process runs longer than `timeout` seconds, it gets killed so
    the script doesn't hang forever on a stuck/rate-limited request.
    Returns (returncode, all_output_lines). returncode is -1 on timeout.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines = []
    start = time.time()
    timed_out = False

    for line in proc.stdout:
        line = line.rstrip("\n")
        print(f"[{ts()}] {line}")
        lines.append(line)
        if time.time() - start > timeout:
            timed_out = True
            break

    if timed_out:
        proc.kill()
        proc.wait(timeout=5)
        print(f"[{ts()}] [warn] gallery-dl exceeded {timeout}s timeout - killed it "
              f"(likely rate-limited by X). Will retry next cycle.")
        return -1, lines

    proc.wait()
    return proc.returncode, lines


def download_new(account_url: str, out_dir: Path, cookies, timeout: int) -> int:
    """
    Runs gallery-dl once to both download and report progress. Returns the
    count of genuinely new files downloaded this cycle (lines that are an
    actual file path, not a "# already downloaded" skip line).
    """
    cmd = GALLERY_DL_CMD + ["-d", str(out_dir), account_url]
    if cookies:
        cmd += ["--cookies", cookies]

    archive_file = out_dir / ".gallery-dl-archive.sqlite3"
    cmd += ["--download-archive", str(archive_file)]

    returncode, lines = run_streamed(cmd, timeout)

    if returncode not in (0, -1):
        print(f"[{ts()}] [warn] gallery-dl exited with code {returncode}")

    # gallery-dl prefixes already-downloaded/skipped files with "# " and
    # prints a plain path for newly downloaded files.
    new_count = sum(
        1 for line in lines
        if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("[")
    )
    return new_count


def main():
    parser = argparse.ArgumentParser(description="Poll an X account and download new media.")
    parser.add_argument("account_url", help="e.g. https://x.com/someaccount")
    parser.add_argument("--out", default="./downloads", help="Output directory")
    parser.add_argument("--cookies", default=None, help="Path to cookies.txt exported from your browser")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300)")
    parser.add_argument("--timeout", type=int, default=120,
                         help="Max seconds to wait for one gallery-dl run before killing it (default: 120)")
    parser.add_argument("--once", action="store_true", help="Run a single check instead of looping forever")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    seen_file = out_dir / ".seen_ids.json"  # kept for backward-compat, not actively used now
    _ = load_seen(seen_file)

    print(f"Monitoring {args.account_url}")
    print(f"Saving media to: {out_dir.resolve()}")
    print(f"Polling every {args.interval}s, per-run timeout {args.timeout}s (Ctrl+C to stop)\n")

    try:
        while True:
            print(f"[{ts()}] Checking for new media...")
            try:
                new_count = download_new(args.account_url, out_dir, args.cookies, args.timeout)
            except Exception as e:
                print(f"[{ts()}] [error] cycle failed: {e}")
                new_count = 0

            if new_count:
                print(f"[{ts()}] [+] {new_count} new item(s) downloaded.")
            else:
                print(f"[{ts()}] [.] No new media.")

            if args.once:
                break
            print(f"[{ts()}] Sleeping for {args.interval}s...\n")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Stopped.")


if __name__ == "__main__":
    main()