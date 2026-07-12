# x-media-sentinel

A lightweight Python watcher that monitors an X (Twitter) account and automatically downloads any new photos or videos as they're posted — no manual checking, no re-downloading duplicates.

Built on top of [`gallery-dl`](https://github.com/mikf/gallery-dl) for the actual extraction, with a polling loop, live timestamped logging, and a timeout guard on top so a stuck or rate-limited run doesn't hang the whole process.

## Features

- **Continuous monitoring** — polls an account on a configurable interval and grabs anything new.
- **No duplicate downloads** — uses `gallery-dl`'s download archive to skip files it already has.
- **Live logging** — every gallery-dl line streams to the console in real time with a timestamp, instead of buffering silently until a run finishes.
- **Timeout protection** — if a run hangs (commonly due to X rate-limiting), it's killed automatically and retried on the next cycle rather than freezing indefinitely.
- **Cross-platform** — runs gallery-dl as a Python module (`python -m gallery_dl`) rather than a bare shell command, avoiding Windows PATH issues.

## Requirements

- Python 3.10+
- [`gallery-dl`](https://pypi.org/project/gallery-dl/)
- A cookies file exported from a logged-in X session (see below)

```bash
pip install gallery-dl
```

## Getting your cookies

X requires an authenticated session to access most media. Export your login cookies once:

1. Log into [x.com](https://x.com) in your browser.
2. Install a cookie-export extension such as **"Get cookies.txt LOCALLY"**.
3. While on x.com, export cookies for the current site and save the file as `cookies.txt` in this project's root folder.

Treat `cookies.txt` like a password — anyone with it can access your logged-in session. Don't commit it or share it, and it's already excluded via `.gitignore`.

## Usage

```bash
python mediaScraper.py https://x.com/someaccount \
    --out ./downloads \
    --cookies cookies.txt \
    --interval 300
```

### Arguments

| Flag | Default | Description |
|---|---|---|
| `account_url` | — | The X profile URL to monitor (required) |
| `--out` | `./downloads` | Directory to save downloaded media |
| `--cookies` | *(none)* | Path to your exported `cookies.txt` |
| `--interval` | `300` | Seconds between checks |
| `--timeout` | `120` | Max seconds to wait for one gallery-dl run before killing it |
| `--once` | *(off)* | Run a single check instead of looping forever |

### Example output

```
[2026-07-12 14:32:01] Checking for new media...
[2026-07-12 14:32:03] downloads/twitter/someaccount/1707456688301744356_1.jpg
[2026-07-12 14:32:03] [+] 1 new item(s) downloaded.
[2026-07-12 14:32:03] Sleeping for 300s...
```

## Notes on rate limiting

X throttles repeated profile scans from the same session. Restarting the script frequently, or setting `--interval` too low, can trigger rate limits or cause a single check to hang. If a run gets stuck, the built-in timeout will kill it and the script will simply retry on the next cycle.

## Disclaimer

This tool is intended for personal archiving of accounts you own or have explicit permission to monitor. Automated scraping of X is against their Terms of Service — use responsibly and at your own risk.

## License

MIT
