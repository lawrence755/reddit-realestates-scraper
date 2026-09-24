#!/usr/bin/env python3
"""Scrape Bay Area subreddit posts into a CSV using Reddit's JSON endpoints.

If REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET are set (a "script" app from
https://www.reddit.com/prefs/apps), requests go through the official OAuth API at
oauth.reddit.com. That is required from cloud/datacenter IPs, which Reddit blocks
for anonymous requests.

Usage:
    python3 scrape_reddit.py                          # defaults below
    python3 scrape_reddit.py --subs bayarea sanfrancisco --sort top --time month
    python3 scrape_reddit.py --query "rent OR housing OR mortgage" --limit 300
"""
import argparse
import base64
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DEFAULT_SUBS = [
    "bayarea",
    "BayAreaRealEstate",
    "sanfrancisco",
    "SanJose",
    "oakland",
    "berkeley",
    "PaloAlto",
    "southbaybayarea",
]
USER_AGENT = "bayarea-realestate-scraper/0.1 (research script)"
FIELDS = [
    "subreddit", "id", "title", "author", "created_utc", "score", "upvote_ratio",
    "num_comments", "flair", "is_self", "url", "permalink", "selftext",
]


_token = None


def oauth_token():
    """App-only OAuth token (client_credentials), or None if no credentials are set."""
    global _token
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return None
    if _token is None:
        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=b"grant_type=client_credentials",
            headers={"User-Agent": USER_AGENT},
        )
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode())
        with urllib.request.urlopen(req, timeout=30) as resp:
            _token = json.load(resp)["access_token"]
    return _token


def fetch_json(url, retries=4):
    headers = {"User-Agent": USER_AGENT}
    token = oauth_token()
    if token:
        url = url.replace("https://www.reddit.com", "https://oauth.reddit.com", 1)
        headers["Authorization"] = f"bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"Failed after {retries} attempts: {url}")


def listing_url(sub, sort, time_filter, query, after):
    params = {"limit": 100, "raw_json": 1}
    if after:
        params["after"] = after
    if query:
        path = f"/r/{sub}/search.json"
        params.update(q=query, restrict_sr=1, sort=sort if sort != "hot" else "relevance", t=time_filter)
    else:
        path = f"/r/{sub}/{sort}.json"
        if sort in ("top", "controversial"):
            params["t"] = time_filter
    return f"https://www.reddit.com{path}?{urllib.parse.urlencode(params)}"


def to_row(post):
    d = post["data"]
    return {
        "subreddit": d.get("subreddit", ""),
        "id": d.get("id", ""),
        "title": d.get("title", "").strip(),
        "author": d.get("author", ""),
        "created_utc": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
        "score": d.get("score", 0),
        "upvote_ratio": d.get("upvote_ratio", ""),
        "num_comments": d.get("num_comments", 0),
        "flair": d.get("link_flair_text") or "",
        "is_self": d.get("is_self", False),
        "url": d.get("url", ""),
        "permalink": "https://www.reddit.com" + d.get("permalink", ""),
        "selftext": (d.get("selftext") or "").strip()[:2000],
    }


def scrape_sub(sub, sort, time_filter, query, limit, delay):
    rows, after = [], None
    while len(rows) < limit:
        data = fetch_json(listing_url(sub, sort, time_filter, query, after))
        children = [c for c in data["data"]["children"] if c.get("kind") == "t3"]
        if not children:
            break
        rows.extend(to_row(c) for c in children)
        after = data["data"].get("after")
        print(f"  r/{sub}: {len(rows)} posts", file=sys.stderr)
        if not after:
            break
        time.sleep(delay)
    return rows[:limit]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subs", nargs="+", default=DEFAULT_SUBS, help="subreddits to scrape")
    ap.add_argument("--sort", default="new", choices=["new", "hot", "top", "rising", "controversial"])
    ap.add_argument("--time", default="month", choices=["hour", "day", "week", "month", "year", "all"])
    ap.add_argument("--query", help="search within each subreddit instead of listing")
    ap.add_argument("--limit", type=int, default=200, help="max posts per subreddit")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests")
    ap.add_argument("--out", default=f"data/bayarea_reddit_{datetime.now():%Y%m%d}.csv")
    args = ap.parse_args()

    seen, all_rows = set(), []
    for sub in args.subs:
        try:
            rows = scrape_sub(sub, args.sort, args.time, args.query, args.limit, args.delay)
        except Exception as e:
            print(f"  r/{sub}: skipped ({e})", file=sys.stderr)
            continue
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                all_rows.append(r)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} unique posts to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
