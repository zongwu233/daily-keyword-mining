from __future__ import annotations

import re
import zipfile
from collections import defaultdict, deque
from datetime import datetime, timezone
from html import unescape
from io import BytesIO

import requests

from common.models import FetchResult, Item

UA = "Mozilla/5.0 (compatible; niche-research-block3/1.0)"
TIMEOUT = 15

WHOISDS_NRD_RE = re.compile(
    r'href=["\']([^"\']*/whois-database/newly-registered-domains/[^"\']+/nrd)["\']',
    re.I,
)
DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?!-)[a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+$"
)
COMMERCIAL_TERMS = (
    "ai",
    "agent",
    "app",
    "bot",
    "cloud",
    "data",
    "dev",
    "flow",
    "growth",
    "lead",
    "market",
    "seo",
    "shop",
    "studio",
    "tool",
    "video",
)
PREFERRED_TLDS = (".ai", ".app", ".dev", ".io", ".tools", ".com", ".co", ".xyz")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, **kw) -> requests.Response:
    headers = kw.pop("headers", {}) | {"User-Agent": UA}
    return requests.get(url, headers=headers, timeout=TIMEOUT, **kw)


def _extract_whoisds_downloads(html: str, max_days: int) -> list[str]:
    seen: set[str] = set()
    links: list[str] = []
    for raw_url in WHOISDS_NRD_RE.findall(html):
        url = unescape(raw_url)
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/"):
            url = f"https://www.whoisds.com{url}"
        if url not in seen:
            seen.add(url)
            links.append(url)
        if len(links) >= max_days:
            break
    return links


def _parse_domain_lines(raw: str) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        domain = line.strip().strip('"').strip("'").lower()
        if not domain or "://" in domain or " " in domain or "." not in domain:
            continue
        if not DOMAIN_RE.match(domain):
            continue
        if domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains


def _domains_from_zip(content: bytes) -> list[str]:
    domains: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            raw = zf.read(name).decode("utf-8", errors="ignore")
            domains.extend(_parse_domain_lines(raw))
    return domains


def _score_new_domain(domain: str) -> int:
    label = domain.split(".", 1)[0]
    score = 30
    if any(domain.endswith(tld) for tld in PREFERRED_TLDS):
        score += 20
    for term in COMMERCIAL_TERMS:
        if term in label:
            score += 12
    if 6 <= len(label) <= 14:
        score += 12
    if "-" not in label:
        score += 8
    digit_count = sum(ch.isdigit() for ch in label)
    score -= digit_count * 5
    if label.count("-") > 1:
        score -= 10
    return max(score, 0)


def _rank_domains(domains: list[str]) -> list[tuple[str, int]]:
    scored_by_score: dict[int, list[str]] = defaultdict(list)
    for domain in domains:
        scored_by_score[_score_new_domain(domain)].append(domain)

    ranked: list[tuple[str, int]] = []
    for score in sorted(scored_by_score, reverse=True):
        by_initial: dict[str, deque[str]] = defaultdict(deque)
        for domain in sorted(scored_by_score[score]):
            by_initial[domain[0]].append(domain)
        initials = sorted(by_initial)
        while initials:
            next_initials: list[str] = []
            for initial in initials:
                domain = by_initial[initial].popleft()
                ranked.append((domain, score))
                if by_initial[initial]:
                    next_initials.append(initial)
            initials = next_initials
    return ranked


def fetch_new_domains(
    top_n: int = 50,
    max_days: int = 1,
    sample_limit: int = 70000,
    min_score: int = 55,
) -> FetchResult:
    source_label = "New Domains (WhoisDS NRD)"
    print(
        f"  [NRD] fetching WhoisDS newly registered domains max_days={max_days}...",
        flush=True,
        end=" ",
    )
    try:
        page = _get("https://www.whoisds.com/newly-registered-domains")
        page.raise_for_status()
        links = _extract_whoisds_downloads(page.text, max_days=max_days)
        if not links:
            raise RuntimeError("no WhoisDS NRD download links found")

        domains: list[str] = []
        seen: set[str] = set()
        for link in links:
            archive = _get(link)
            archive.raise_for_status()
            for domain in _domains_from_zip(archive.content):
                if domain in seen:
                    continue
                seen.add(domain)
                domains.append(domain)
                if len(domains) >= sample_limit:
                    break
            if len(domains) >= sample_limit:
                break

        ranked = _rank_domains(domains)
        items = [
            Item(
                source=source_label,
                title=domain,
                url=f"https://{domain}",
                score=score,
                comments=None,
                extra={
                    "description": "newly registered domain candidate; score is name/TLD/commercial-intent heuristic",
                    "rank": idx,
                    "source_url": links[0],
                },
            )
            for idx, (domain, score) in enumerate(ranked, 1)
            if score >= min_score
        ][:top_n]
        print(f"OK ({len(items)} items from {len(domains)} sampled domains)", flush=True)
        return FetchResult(source_label, True, items, fetched_at=_ts())
    except Exception as e:
        print("FAIL", flush=True)
        return FetchResult(source_label, False, error=repr(e), fetched_at=_ts())
