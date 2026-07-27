from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, cast

import feedparser
import requests

from common.models import FetchResult, Item

UA = "Mozilla/5.0 (compatible; niche-research-block4/1.0)"
TIMEOUT = 15


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {}) | {"User-Agent": UA}
    return requests.get(url, headers=headers, timeout=TIMEOUT, **kw)


def fetch_hackernews(top_n: int = 20) -> FetchResult:
    base = "https://hacker-news.firebaseio.com/v0"
    try:
        print(f"  [HN] fetching top {top_n} story ids...", flush=True)
        ids = _get(f"{base}/topstories.json").json()[:top_n]
        items: list[Item] = []
        for i, aid in enumerate(ids, 1):
            d = _get(f"{base}/item/{aid}.json").json()
            if not d:
                continue
            url = d.get("url") or f"https://news.ycombinator.com/item?id={aid}"
            items.append(
                Item(
                    source="Hacker News",
                    title=d.get("title", ""),
                    url=url,
                    score=d.get("score"),
                    comments=d.get("descendants"),
                    extra={
                        "by": d.get("by"),
                        "hn_url": f"https://news.ycombinator.com/item?id={aid}",
                    },
                )
            )
            if i % 5 == 0:
                print(f"  [HN] {i}/{len(ids)}", flush=True)
            time.sleep(0.05)
        print(f"  [HN] done: {len(items)} items", flush=True)
        return FetchResult("Hacker News", True, items, fetched_at=_ts())
    except Exception as e:
        return FetchResult("Hacker News", False, error=repr(e), fetched_at=_ts())


def _reddit_fetch(url: str, retries: int = 2, backoff: int = 20) -> Any:
    last_status = None
    for attempt in range(retries + 1):
        feed = feedparser.parse(url, agent=UA)
        status = getattr(feed, "status", 200)
        last_status = status
        if status == 200 and feed.entries:
            return feed
        if status in (429, 503) and attempt < retries:
            print(f"  [Reddit] HTTP {status}, retry in {backoff}s (attempt {attempt+1}/{retries})", flush=True)
            time.sleep(backoff)
            backoff *= 2
            continue
        return feed
    return None


def fetch_reddit(subreddits: list[str], top_n_per_sub: int = 20) -> FetchResult:
    items: list[Item] = []
    errors: list[str] = []
    print(f"  [Reddit] {len(subreddits)} subreddit(s) to fetch", flush=True)
    for idx, sub in enumerate(subreddits):
        if idx > 0:
            time.sleep(5)
        print(f"  [Reddit] r/{sub} ...", flush=True, end=" ")
        try:
            url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit={top_n_per_sub}"
            feed = _reddit_fetch(url)
            if feed is None:
                raise RuntimeError("rate limited after retries")
            if feed.bozo and not feed.entries:
                raise RuntimeError(f"feed parse error: {feed.bozo_exception}")
            status = getattr(feed, "status", 200)
            if status == 429:
                raise RuntimeError("rate limited (429)")
            seen_in_sub: set[str] = set()
            for raw in list(feed.entries)[:top_n_per_sub]:
                e: dict[str, Any] = cast(dict[str, Any], raw)
                link = str(e.get("link") or e.get("id") or "")
                if not link or link in seen_in_sub:
                    continue
                seen_in_sub.add(link)
                score = None
                for k in ("score", "ups"):
                    if k in e:
                        score = int(e[k])
                        break
                comments = int(e["comments"]) if "comments" in e else None
                items.append(
                    Item(
                        source=f"Reddit-r/{sub}",
                        title=str(e.get("title", "")),
                        url=link,
                        score=score,
                        comments=comments,
                        extra={"author": str(e.get("author", ""))},
                    )
                )
            print(f"OK ({len(seen_in_sub)} items)", flush=True)
        except Exception as exc:
            print(f"FAIL ({exc!r})", flush=True)
            errors.append(f"r/{sub}: {exc!r}")
    if not items and errors:
        return FetchResult(
            "Reddit",
            False,
            error="; ".join(errors),
            fetched_at=_ts(),
        )
    return FetchResult("Reddit", True, items, fetched_at=_ts())


PH_GRAPHQL = "https://api.producthunt.com/v2/api/graphql"


def fetch_producthunt(token: str, top_n: int = 10) -> FetchResult:
    if not token:
        return FetchResult(
            "Product Hunt",
            False,
            error="no token (set producthunt.token in config)",
            fetched_at=_ts(),
        )
    print(f"  [PH] fetching top {top_n} posts...", flush=True, end=" ")
    query = """
    query {
      posts(first: %d, order: VOTES) {
        edges {
          node {
            name
            tagline
            url
            website
            votesCount
            commentsCount
            topics(first: 3) { edges { node { name } } }
          }
        }
      }
    }
    """ % top_n
    try:
        r = requests.post(
            PH_GRAPHQL,
            json={"query": query},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": UA,
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(str(data["errors"]))
        items: list[Item] = []
        for edge in data["data"]["posts"]["edges"]:
            n = edge["node"]
            url = n.get("website") or n.get("url") or ""
            topics = [t["node"]["name"] for t in n.get("topics", {}).get("edges", [])]
            items.append(
                Item(
                    source="Product Hunt",
                    title=f"{n['name']} — {n.get('tagline', '')}",
                    url=url,
                    score=n.get("votesCount"),
                    comments=n.get("commentsCount"),
                    extra={"topics": topics, "ph_url": n.get("url")},
                )
            )
        print(f"OK ({len(items)} items)", flush=True)
        return FetchResult("Product Hunt", True, items, fetched_at=_ts())
    except Exception as e:
        print(f"FAIL", flush=True)
        return FetchResult("Product Hunt", False, error=repr(e), fetched_at=_ts())


YT_TRENDING = "https://www.googleapis.com/youtube/v3/videos"


def fetch_youtube(api_key: str, region_code: str = "US", top_n: int = 15) -> FetchResult:
    if not api_key:
        return FetchResult(
            "YouTube",
            False,
            error="no api_key (set youtube.api_key in config)",
            fetched_at=_ts(),
        )
    print(f"  [YT] fetching trending ({region_code}) top {top_n}...", flush=True, end=" ")
    try:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": top_n,
            "key": api_key,
        }
        r = _get(YT_TRENDING, params=params)
        r.raise_for_status()
        data = r.json()
        items: list[Item] = []
        for v in data.get("items", []):
            sid = v["id"]
            snip = v.get("snippet", {})
            stat = v.get("statistics", {})
            view_count = int(stat.get("viewCount", 0)) if "viewCount" in stat else None
            items.append(
                Item(
                    source="YouTube Trending",
                    title=snip.get("title", ""),
                    url=f"https://www.youtube.com/watch?v={sid}",
                    score=view_count,
                    comments=int(stat["commentCount"]) if "commentCount" in stat else None,
                    extra={
                        "channel": snip.get("channelTitle"),
                        "category_id": snip.get("categoryId"),
                    },
                )
            )
        print(f"OK ({len(items)} items)", flush=True)
        return FetchResult("YouTube Trending", True, items, fetched_at=_ts())
    except Exception as e:
        print(f"FAIL", flush=True)
        return FetchResult("YouTube Trending", False, error=repr(e), fetched_at=_ts())


STEAM_FEATURED = "https://store.steampowered.com/api/featuredcategories"


def fetch_steam(top_n: int = 15) -> FetchResult:
    print(f"  [Steam] fetching new releases top {top_n}...", flush=True, end=" ")
    try:
        r = _get(STEAM_FEATURED, params={"l": "english", "cc": "US"})
        r.raise_for_status()
        data = r.json()
        items: list[Item] = []
        new_releases = data.get("new_releases", {})
        for g in new_releases.get("items", [])[:top_n]:
            appid = g.get("id")
            items.append(
                Item(
                    source="Steam New Releases",
                    title=g.get("name", ""),
                    url=f"https://store.steampowered.com/app/{appid}" if appid else "",
                    score=None,
                    comments=None,
                    extra={
                        "price": g.get("final_price", 0) / 100 if g.get("final_price") else None,
                        "discount": g.get("discount_block"),
                    },
                )
            )
        print(f"OK ({len(items)} items)", flush=True)
        return FetchResult("Steam New Releases", True, items, fetched_at=_ts())
    except Exception as e:
        print(f"FAIL", flush=True)
        return FetchResult("Steam New Releases", False, error=repr(e), fetched_at=_ts())
