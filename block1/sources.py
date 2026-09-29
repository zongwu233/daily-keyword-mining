from __future__ import annotations
import os
import re
import time
from datetime import datetime, timedelta, timezone

import requests
import feedparser

from common.models import FetchResult, Item


UA = "Mozilla/5.0 (compatible; niche-research-block1/1.0)"
TIMEOUT = 15

WIKI_PREFIXES_TO_SKIP = (
    "Main_Page",
    "Special:",
    "Wikipedia:",
    "Portal:",
    "Help:",
    "File:",
    "Talk:",
    "Template:",
    "Category:",
)

REPO_RE = re.compile(
    r'<h2[^>]*lh-condensed[^>]*>\s*<a[^>]*href="(/[^/]+/[^/"]+)"',
    re.S,
)
STARS_RE = re.compile(r"([\d,]+)\s+stars\s+(today|this week|this month)", re.S)
DESC_RE = re.compile(
    r'<p class="[^"]*col-9[^"]*"[^>]*>\s*([^<]+?)\s*</p>', re.S
)
LANG_RE = re.compile(
    r'itemprop="programmingLanguage">\s*([^<]+?)\s*<', re.S
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_google_trends_rss(
    geo: str = "US",
    top_n: int = 20,
    retries: int = 3,
    backoff: int = 5,
) -> FetchResult:
    source_label = f"Google Trends ({geo})"
    print(f"  [GT-rss] fetching daily trending geo={geo}...", flush=True, end=" ")
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = _get(url)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            f = feedparser.parse(r.text)
            items: list[Item] = []
            for i, e in enumerate(list(f.entries)[:top_n], 1):
                title = str(e.get("title", "")).strip()
                if not title:
                    continue
                traffic = str(e.get("ht_approx_traffic", "") or "").strip()
                news_title = str(e.get("ht_news_item_title", "") or "").strip()
                news_url = str(e.get("ht_news_item_url", "") or "").strip()
                news_snippet = str(e.get("ht_news_item_snippet", "") or "").strip()
                desc_bits = []
                if traffic:
                    desc_bits.append(f"traffic={traffic}")
                if news_title:
                    desc_bits.append(f"news: {news_title}")
                if news_snippet and news_snippet != news_title:
                    desc_bits.append(news_snippet[:120])
                description = " · ".join(desc_bits)
                items.append(
                    Item(
                        source=source_label,
                        title=title,
                        url=f"https://trends.google.com/trends/explore?q={title.replace(' ', '+')}&geo={geo}",
                        score=None,
                        comments=None,
                        extra={
                            "rank": i,
                            "approx_traffic": traffic or None,
                            "pub_date": str(e.get("published", "")),
                            "news_title": news_title or None,
                            "news_url": news_url or None,
                            "news_snippet": news_snippet or None,
                            "description": description or None,
                        },
                    )
                )
            print(f"OK ({len(items)} items){f' after {attempt+1} tries' if attempt > 0 else ''}", flush=True)
            return FetchResult(source_label, True, items, fetched_at=_ts())
        except Exception as e:
            last_err = e
            if attempt < retries:
                wait = backoff * (attempt + 1)
                print(f"retry in {wait}s ", flush=True, end="")
                time.sleep(wait)
                print(f"... ", flush=True, end="")
    print(f"FAIL", flush=True)
    return FetchResult(source_label, False, error=repr(last_err), fetched_at=_ts())


def _get(url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {}) | {"User-Agent": UA}
    return requests.get(url, headers=headers, timeout=TIMEOUT, **kw)


def fetch_wikipedia_top(top_n: int = 30, days_back: int = 1) -> FetchResult:
    print(f"  [Wiki] fetching top {top_n} articles (days_back={days_back})...", flush=True, end=" ")
    try:
        d = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{d}"
        r = _get(url)
        r.raise_for_status()
        data = r.json()
        items: list[Item] = []
        for a in data["items"][0]["articles"]:
            title_raw = a["article"]
            if title_raw.startswith(WIKI_PREFIXES_TO_SKIP):
                continue
            items.append(
                Item(
                    source="Wikipedia Top",
                    title=title_raw.replace("_", " "),
                    url=f"https://en.wikipedia.org/wiki/{title_raw}",
                    score=int(a.get("views", 0)),
                    comments=None,
                    extra={
                        "rank": a.get("rank"),
                        "date": d,
                    },
                )
            )
            if len(items) >= top_n:
                break
        print(f"OK ({len(items)} items)", flush=True)
        return FetchResult("Wikipedia Top", True, items, fetched_at=_ts())
    except Exception as e:
        print(f"FAIL", flush=True)
        return FetchResult("Wikipedia Top", False, error=repr(e), fetched_at=_ts())


def fetch_github_trending(
    since: str = "daily",
    language: str = "",
    top_n: int = 25,
) -> FetchResult:
    lang_label = f"/{language}" if language else ""
    lang_display = f" [{language}]" if language else ""
    source_label = f"GitHub Trending ({since}){lang_display}"
    print(
        f"  [GitHub] trending since={since} language={language or '(all)'}...",
        flush=True,
        end=" ",
    )
    try:
        url = f"https://github.com/trending{lang_label}?since={since}"
        r = _get(url)
        r.raise_for_status()
        boxes = re.findall(r"<article[^>]*>(.*?)</article>", r.text, re.S)
        items: list[Item] = []
        for box in boxes[:top_n]:
            m = REPO_RE.search(box)
            if not m:
                continue
            slug = m.group(1).strip("/")
            sm = STARS_RE.search(box)
            stars_today = (
                int(sm.group(1).replace(",", "")) if sm else None
            )
            stars_period = sm.group(2) if sm else None
            dm = DESC_RE.search(box)
            desc = dm.group(1).strip() if dm else ""
            lm = LANG_RE.search(box)
            lang_name = lm.group(1).strip() if lm else None
            name = slug.split("/")[-1] if slug else ""
            items.append(
                Item(
                    source=source_label,
                    title=name,
                    url=f"https://github.com/{slug}",
                    score=stars_today,
                    comments=None,
                    extra={
                        "full_slug": slug,
                        "description": desc[:200],
                        "language": lang_name,
                        "stars_period": stars_period,
                    },
                )
            )
        print(f"OK ({len(items)} items)", flush=True)
        return FetchResult(
            source_label, True, items, fetched_at=_ts()
        )
    except Exception as e:
        print(f"FAIL", flush=True)
        return FetchResult(
            source_label, False, error=repr(e), fetched_at=_ts()
        )


JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_TIMEOUT = 30
JEV_QUESTION = {
    "type": "choice",
    "instructions": "Classify the candidate object in the state for durable keyword research. Choose 'research' only when it plausibly signals ongoing problem, product, service, tool, or informational niche demand beyond the current news cycle. Choose 'transient' for short-lived attention that is not itself a durable niche opportunity. Choose 'uncertain' when context is insufficient or the term could be either; do not infer a business opportunity from a person or event name alone.",
    "criteria": {
        "research": "A plausibly durable topic, product/service category, recurring problem, or informational need suitable for manual keyword opportunity research.",
        "transient": "Primarily a short-lived spike: celebrity/person gossip or news; film/TV/music/game release or fandom; sports match/tournament/athlete result; breaking news, political event/election, crime or disaster; holiday/anniversary/seasonal event; recurring annual shopping or tax/payday trend; weather alert; lottery/draw result; viral meme/challenge; one-off product launch or press event.",
        "uncertain": "Not enough evidence to distinguish durable demand from a transient spike, or the term is ambiguous."
    }
}


def screen_google_trends(items: list[Item], geo: str, api_key: str) -> tuple[list[Item], list[Item], str | None]:
    """Return research candidates, rejected/uncertain terms, and a failure message."""
    if not items:
        return [], [], None
    if not api_key:
        return items, [], "TYPESAFE_API_KEY is not configured; showing unscreened trends"

    kept: list[Item] = []
    excluded: list[Item] = []
    try:
        for index, item in enumerate(items):
            state = {
                "region": geo,
                "candidate": {
                    "term": item.title,
                    "news_title": item.extra.get("news_title"),
                    "news_snippet": item.extra.get("news_snippet"),
                },
            }
            response = requests.post(
                JEV_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "state": state,
                    "model": "jev-latest",
                    "questions": {"screen": JEV_QUESTION},
                },
                timeout=JEV_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            answers = payload.get("answers", {}) if isinstance(payload, dict) else {}
            answer = answers.get("screen", {}) if isinstance(answers, dict) else {}
            decision = answer.get("choice") if isinstance(answer, dict) else None
            if decision not in {"research", "transient", "uncertain"}:
                raise ValueError("JEV response is missing a valid classification")
            item.extra["jev_decision"] = decision
            item.extra["jev_confidence"] = answer.get("confidence")
            if decision == "research":
                kept.append(item)
            else:
                excluded.append(item)
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        return items, [], f"JEV screening failed; showing unscreened trends: {exc}"
    return kept, excluded, None


def fetch_and_screen_google_trends(geo: str, top_n: int, api_key: str) -> tuple[FetchResult, FetchResult | None, str | None]:
    raw = fetch_google_trends_rss(geo=geo, top_n=top_n)
    if not raw.ok:
        return raw, None, None
    kept, excluded, error = screen_google_trends(raw.items, geo, api_key)
    if error:
        raw.source = f"Google Trends ({geo}) — screening unavailable"
        return raw, None, error
    research = FetchResult(f"Google Trends ({geo}) — research candidates", True, kept, fetched_at=raw.fetched_at)
    filtered = FetchResult(f"Google Trends ({geo}) — filtered out", True, excluded, fetched_at=raw.fetched_at) if excluded else None
    return research, filtered, None
