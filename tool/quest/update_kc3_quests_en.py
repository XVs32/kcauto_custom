#!/usr/bin/env python3
"""Download latest KC3 `quests.json` and overwrite local copy.

Usage:
    python3 tool/quest/update_kc3_quests_en.py

Optional flags:
    -u, --url       Override the raw URL to download
    -o, --out       Override output path
    --no-backup     Don't keep a timestamped backup of the existing file
"""
import argparse
import json
import os
import shutil
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from datetime import datetime

DEFAULT_RAW_URL = "https://raw.githubusercontent.com/KC3Kai/kc3-translations/master/data/en/quests.json"

def download(url):
    req = Request(url, headers={"User-Agent": "kcauto-update-script/1.0"})
    with urlopen(req) as resp:
        status = getattr(resp, "status", None)
        if status is not None and status != 200:
            raise HTTPError(url, status, getattr(resp, "reason", ""), resp.headers, None)
        return resp.read()

def main():
    parser = argparse.ArgumentParser(description="Download latest KC3 quests.json and overwrite local copy.")
    parser.add_argument("--url", "-u", default=DEFAULT_RAW_URL, help="Raw URL to download (default: KC3Kai raw quests.json)")
    parser.add_argument("--out", "-o", default=None, help="Output path (default: data/quests/kc3_quests_en.json relative to repo root)")
    parser.add_argument("--no-backup", action="store_true", help="Don't keep a timestamped backup of the existing file")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.normpath(os.path.join(script_dir, "..", ".."))
    default_out = os.path.join(repo_root, "data", "quests", "kc3_quests_en.json")
    out_path = args.out or default_out

    try:
        raw = download(args.url)
    except Exception as exc:
        print(f"Error downloading {args.url}: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        json.loads(raw.decode("utf-8"))
    except Exception as exc:
        print(f"Downloaded content is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(3)

    if os.path.exists(out_path) and not args.no_backup:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup_path = out_path + f".bak.{timestamp}"
        try:
            shutil.copy2(out_path, backup_path)
            print(f"Created backup: {backup_path}")
        except Exception as exc:
            print(f"Warning: could not create backup: {exc}", file=sys.stderr)

    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as fh:
            fh.write(raw)
    except Exception as exc:
        print(f"Failed writing to {out_path}: {exc}", file=sys.stderr)
        sys.exit(4)

    print(f"Updated {out_path} from {args.url}")

if __name__ == "__main__":
    main()
