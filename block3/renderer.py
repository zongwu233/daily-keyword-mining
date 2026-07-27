from __future__ import annotations

from datetime import datetime
from html import escape

from common.models import FetchResult


def _fmt_num(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


def render_markdown(result: FetchResult, iso_str: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# New Domain Research Report — {today}",
        "",
        f"> Generated at: {iso_str}  ·  {result.summary()}",
        "",
        "## New Domain Candidates",
        "",
    ]
    if not result.ok:
        lines.append(f"Source failed: {result.error}")
        return "\n".join(lines) + "\n"
    for i, it in enumerate(result.items, 1):
        desc = it.extra.get("description") or ""
        lines.append(f"{i}. **{it.title}** · signal={_fmt_num(it.score)}")
        if desc:
            lines.append(f"   - {desc}")
        lines.append(f"   - {it.url}")
    return "\n".join(lines) + "\n"


HTML_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; max-width: 920px; margin: 0 auto; padding: 24px 28px 80px; color: #1f2328; line-height: 1.55; }
h1 { font-size: 22px; border-bottom: 2px solid #1f2328; padding-bottom: 8px; margin: 0 0 6px; }
.meta { color: #6c757d; font-size: 13px; margin-bottom: 16px; }
h2 { font-size: 16px; margin: 28px 0 12px; padding: 6px 10px; background: #f0f3f6; border-left: 4px solid #1a7f37; }
.item { padding: 8px 10px; border-bottom: 1px solid #eaecef; font-size: 14px; }
.item-title { font-weight: 600; color: #1f2328; }
.item-meta { font-size: 12px; color: #6c757d; margin-left: 8px; white-space: nowrap; }
.item-desc { font-size: 12px; color: #555; margin-top: 2px; }
.item-url { display: block; font-size: 12px; color: #1a7f37; margin-top: 2px; word-break: break-all; text-decoration: none; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin-right: 6px; background: #eaecef; color: #444; }
"""


def render_html(result: FetchResult, iso_str: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>New Domain Research Report — {today}</title>",
        f"<style>{HTML_CSS}</style>",
        "</head><body>",
        "<h1>New Domain Research Report</h1>",
        f'<div class="meta">Date: {today} · Generated at {escape(iso_str)} · {escape(result.summary())}</div>',
        '<h2>New Domains (WhoisDS NRD) <span class="badge">NRD</span></h2>',
    ]
    if not result.ok:
        parts.append(f'<p style="color:#cf222e">Source failed: {escape(result.error or "unknown")}</p>')
    else:
        for i, it in enumerate(result.items, 1):
            desc = it.extra.get("description") or ""
            desc_html = f'<div class="item-desc">{escape(desc[:200])}</div>' if desc else ""
            parts.append(
                f'<div class="item"><div><span class="badge">{i}</span>'
                f'<span class="item-title">{escape(it.title)}</span>'
                f'<span class="item-meta">signal {_fmt_num(it.score)}</span></div>'
                f'{desc_html}'
                f'<a class="item-url" href="{escape(it.url)}" target="_blank" rel="noopener">{escape(it.url)}</a>'
                f'</div>'
            )
    parts.append("</body></html>")
    return "\n".join(parts)
