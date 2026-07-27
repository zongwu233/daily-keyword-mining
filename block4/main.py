from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.models import FetchResult
from block4.renderer import render_html, render_markdown
from block4.sources import (
    fetch_hackernews,
    fetch_producthunt,
    fetch_reddit,
    fetch_steam,
    fetch_youtube,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "block4" / "config.json"
DEFAULT_OUT = ROOT / "digests"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"config not found: {path}\n"
            f"copy block4/config.example.json to {path} and fill in tokens"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def run_all(cfg: dict[str, Any]) -> list[FetchResult]:
    top = cfg.get("top_n", {})
    results: list[FetchResult] = []

    results.append(fetch_hackernews(top_n=top.get("hackernews", 20)))

    reddit_cfg = cfg.get("reddit", {})
    results.append(
        fetch_reddit(
            subreddits=reddit_cfg.get(
                "subreddits", ["all", "InternetIsBeautiful", "SomebodyMakeThis"]
            ),
            top_n_per_sub=reddit_cfg.get("top_n_per_sub", 20),
        )
    )

    ph_cfg = cfg.get("producthunt", {})
    results.append(
        fetch_producthunt(
            token=ph_cfg.get("token", ""),
            top_n=top.get("producthunt", 10),
        )
    )

    yt_cfg = cfg.get("youtube", {})
    results.append(
        fetch_youtube(
            api_key=yt_cfg.get("api_key", ""),
            region_code=yt_cfg.get("region_code", "US"),
            top_n=top.get("youtube", 15),
        )
    )

    results.append(fetch_steam(top_n=top.get("steam", 15)))
    return results


def write_outputs(
    results: list[FetchResult], out_dir: Path, ts: datetime
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = ts.strftime("%Y-%m-%d")
    iso_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    md_path = out_dir / f"digest-{date_str}.md"
    html_path = out_dir / f"digest-{date_str}.html"

    md_path.write_text(render_markdown(results, iso_str), encoding="utf-8")
    html_path.write_text(render_html(results, iso_str), encoding="utf-8")
    return md_path, html_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Block 4 community aggregator")
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
