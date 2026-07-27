from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from block1.renderer import render_html, render_markdown
from block1.sources import (
    fetch_github_trending,
    fetch_google_trends_rss,
    fetch_wikipedia_top,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "block1" / "config.json"
DEFAULT_OUT = ROOT / "trends"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"config not found: {path}\n"
            f"copy block1/config.example.json to {path}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def run_all(cfg: dict[str, Any]) -> list:
    top = cfg.get("top_n", {})
    results = []

    wiki_cfg = cfg.get("wikipedia", {})
    results.append(
        fetch_wikipedia_top(
            top_n=top.get("wikipedia", 30),
            days_back=wiki_cfg.get("days_back", 1),
        )
    )

    gh_cfg = cfg.get("github", {})
    for entry in gh_cfg.get("queries", [{"since": "daily", "language": ""}]):
        results.append(
            fetch_github_trending(
                since=entry.get("since", "daily"),
                language=entry.get("language", ""),
                top_n=top.get("github", 25),
            )
        )

    gt_cfg = cfg.get("google_trends_rss", {})
    if gt_cfg.get("enabled", True):
        geos = gt_cfg.get("geos", ["US"])
        for idx, geo in enumerate(geos):
            if idx > 0:
                import time as _time
                _time.sleep(3)
            results.append(fetch_google_trends_rss(geo=geo, top_n=top.get("google_trends", 20)))

    return results


def write_outputs(results, out_dir: Path, ts: datetime) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = ts.strftime("%Y-%m-%d")
    iso_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    md_path = out_dir / f"trends-{date_str}.md"
    html_path = out_dir / f"trends-{date_str}.html"

    md_path.write_text(render_markdown(results, iso_str), encoding="utf-8")
    html_path.write_text(render_html(results, iso_str), encoding="utf-8")
    return md_path, html_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Block 1 trend aggregator")
    p.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"config json path (default: {DEFAULT_CONFIG})",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    args = p.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    ts = datetime.now(timezone.utc)
    print(f"[INFO] start at {ts.isoformat()}")
    results = run_all(cfg)

    print("[INFO] fetch summary:")
    total_ok = 0
    total_items = 0
    for r in results:
        print(f"  {r.summary()}")
        if r.ok:
            total_ok += 1
            total_items += len(r.items)

    md_path, html_path = write_outputs(results, args.out, ts)
    print(f"[INFO] {total_ok}/{len(results)} sources ok, {total_items} items total")
    print(f"[INFO] md   → {md_path}")
    print(f"[INFO] html → {html_path}")
    return 0 if total_ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
