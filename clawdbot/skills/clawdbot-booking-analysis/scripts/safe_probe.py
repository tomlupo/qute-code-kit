#!/usr/bin/env python3
"""
Safe booking site probe.

- Fetch HTML and bundle list
- Extract /api endpoints from bundles (best-effort)
- Optional safe POST to availability endpoint (no confirm)

Usage:
  python scripts/safe_probe.py --url https://example.com
  python scripts/safe_probe.py --url https://mojstolik.pl --availability --payload payload.json
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urljoin

import requests


API_PATTERN = re.compile(r"/api/[a-zA-Z0-9_\-./?{}=]+")
SCRIPT_PATTERN = re.compile(r"<script[^>]+src=\"([^\"]+)\"")


def fetch(url, headers=None):
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def list_scripts(html, base_url):
    scripts = []
    for m in SCRIPT_PATTERN.finditer(html):
        src = m.group(1)
        scripts.append(urljoin(base_url, src))
    return scripts


def extract_endpoints(js_text):
    return sorted(set(API_PATTERN.findall(js_text)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base site URL, e.g. https://mojstolik.pl")
    parser.add_argument("--availability", action="store_true", help="Run a safe availability POST if payload provided")
    parser.add_argument("--payload", help="JSON file with POST body for availability check")
    parser.add_argument("--post-url", help="Override POST URL for availability check")
    parser.add_argument("--locale", default="pl", help="Device-Locale header value")
    args = parser.parse_args()

    base_url = args.url.rstrip("/") + "/"
    headers = {"User-Agent": "clawdbot-safe-probe/1.0", "Device-Locale": args.locale}

    html = fetch(base_url, headers=headers)
    scripts = list_scripts(html, base_url)

    endpoints = set()
    for src in scripts[:10]:
        try:
            js_text = fetch(src, headers=headers)
        except Exception:
            continue
        for ep in extract_endpoints(js_text):
            endpoints.add(ep)

    print("# Scripts")
    for s in scripts:
        print(s)

    print("\n# Endpoints (best-effort)")
    for ep in sorted(endpoints):
        print(ep)

    if args.availability:
        if not args.payload:
            print("\n[skip] --availability requires --payload")
            return 0
        with open(args.payload, "r", encoding="utf-8") as f:
            body = json.load(f)
        post_url = args.post_url or urljoin(base_url, "api/restaurant/searchSingleRestaurant")
        resp = requests.post(
            post_url,
            json=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Device-Locale": args.locale,
            },
            timeout=20,
        )
        print("\n# Availability response")
        print("status", resp.status_code)
        print(resp.text[:2000])

    return 0


if __name__ == "__main__":
    sys.exit(main())
