from __future__ import annotations

from datetime import datetime
from html import escape

from common.models import FetchResult, Item

SOURCE_ORDER = [
    "Hacker News",
    "Reddit",
    "Product Hunt",
    "YouTube Trending",
    "Steam New Releases",
]

SOURCE_ICONS = {
    "Hacker News": "[HN]",
    "Reddit": "[R]",
    "Product Hunt": "[PH]",
    "YouTube Trending": "[YT]",
    "Steam New Releases": "[ST]",
}


def _sort_key(src: str) -> int:
    for i, prefix in enumerate(SOURCE_ORDER):
        if src == prefix or src.startswith(prefix + "-"):
            return i
    return 99


def _fmt_num(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def group_by_source(results: list[FetchResult]) -> dict[str, list[Item]]:
    grouped: dict[str, list[Item]] = {}
    for r in results:
        if not r.ok:
            continue
        for it in r.items:
            grouped.setdefault(it.source, []).append(it)
    return dict(sorted(grouped.items(), key=lambda kv: _sort_key(kv[0])))


def render_markdown(results: list[FetchResult], date_str: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# Community Signal Digest — {today}",
        "",
        f"> Generated at: {date_str}  ·  Sources: {len(results)}",
        "",
        "## Source Status",
        "",
    ]
    for r in results:
        lines.append(f"- {r.summary()}")
    lines.append("")
    lines.append("---")
    lines.append("")

    grouped = group_by_source(results)
    if not grouped:
        lines.append("All sources failed. Check network access or configuration.")
        return "\n".join(lines) + "\n"

    for src, items in grouped.items():
        lines.append(f"## {src} ({len(items)} items)")
        lines.append("")
        for i, it in enumerate(items, 1):
            score_part = f" · points={_fmt_num(it.score)}" if it.score is not None else ""
            cmt_part = f" · comments={_fmt_num(it.comments)}" if it.comments is not None else ""
            lines.append(f"{i}. **{it.title}**{score_part}{cmt_part}")
            lines.append(f"   - {it.url}")
        lines.append("")

    return "\n".join(lines) + "\n"


HTML_CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Noto Sans CJK SC", sans-serif;
    max-width: 920px;
    margin: 0 auto;
    padding: 24px 28px 80px;
    color: #1f2328;
    line-height: 1.55;
    background: #fff;
}
h1 {
    font-size: 22px;
    border-bottom: 2px solid #1f2328;
    padding-bottom: 8px;
    margin: 0 0 6px;
}
.meta { color: #6c757d; font-size: 13px; margin-bottom: 16px; }
h2 {
    font-size: 16px;
    margin: 28px 0 12px;
    padding: 6px 10px;
    background: #f0f3f6;
    border-left: 4px solid #247;
}
.status-list { font-size: 13px; color: #444; }
.status-list .ok { color: #1a7f37; }
.status-list .fail { color: #cf222e; }
.source-section { margin-bottom: 8px; }
.item {
    padding: 8px 10px;
    border-bottom: 1px solid #eaecef;
    font-size: 14px;
}
.item:last-child { border-bottom: none; }
.item-title { font-weight: 600; color: #1f2328; }
.item-meta {
    font-size: 12px;
    color: #6c757d;
    margin-left: 8px;
    white-space: nowrap;
}
.item-url {
    display: block;
    font-size: 12px;
    color: #247;
    margin-top: 2px;
    word-break: break-all;
    text-decoration: none;
}
.item-url:hover { text-decoration: underline; }
.badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
    background: #eaecef;
    color: #444;
}
hr { border: none; border-top: 1px solid #d0d7de; margin: 18px 0; }
.footer {
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #eaecef;
    color: #6c757d;
    font-size: 12px;
    text-align: center;
}
"""


def _render_status_pill(ok: bool, text: str) -> str:
    cls = "ok" if ok else "fail"
    return f'<span class="{cls}">{escape(text)}</span>'


def render_html(results: list[FetchResult], date_str: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Community Signal Digest — {today}</title>",
        f"<style>{HTML_CSS}</style>",
        "</head><body>",
        "<h1>Community Signal Digest</h1>",
        f'<div class="meta">Date: {today}  ·  Generated at {escape(date_str)}  ·  Sources: {len(results)}</div>',
        '<div class="status-list"><strong>Source status:</strong> ',
    ]
    pills = []
    for r in results:
        text = f"{r.source}: {'OK' if r.ok else 'FAIL'} ({len(r.items) if r.ok else r.error})"
        pills.append(_render_status_pill(r.ok, text))
    parts.append(" · ".join(pills))
    parts.append("</div>")
    parts.append("<hr>")

    grouped = group_by_source(results)
    if not grouped:
        parts.append('<p style="color:#cf222e">All sources failed. Check network access or configuration.</p>')
    else:
        for src, items in grouped.items():
            badge = SOURCE_ICONS.get(src, "")
            parts.append(
                f'<h2>{escape(src)} <span class="badge">{escape(badge)}</span>'
                f'<span class="badge">{len(items)} items</span></h2>'
            )
            parts.append('<div class="source-section">')
            for i, it in enumerate(items, 1):
                meta_bits = []
                if it.score is not None:
                    meta_bits.append(f"⬆ {_fmt_num(it.score)}")
                if it.comments is not None:
                    meta_bits.append(f"💬 {_fmt_num(it.comments)}")
                meta_html = (
                    f'<span class="item-meta">{" · ".join(meta_bits)}</span>'
                    if meta_bits
                    else ""
                )
                url_html = (
                    f'<a class="item-url" href="{escape(it.url)}" target="_blank" rel="noopener">{escape(it.url)}</a>'
                    if it.url
                    else ""
                )
                parts.append(
                    f'<div class="item">'
                    f'<div><span class="badge">{i}</span>'
                    f'<span class="item-title">{escape(it.title)}</span>'
                    f"{meta_html}</div>"
                    f"{url_html}"
                    f"</div>"
                )
            parts.append("</div>")

    parts.append(
        f'<div class="footer">Generated by community signal aggregator · {escape(date_str)}</div>'
    )
    parts.append("</body></html>")
    return "\n".join(parts)
