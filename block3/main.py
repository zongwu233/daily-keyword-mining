from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from block3.renderer import render_html, render_markdown
from block3.sources import fetch_new_domains

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "block3" / "config.json"
DEFAULT_OUT = ROOT / "new_domains"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"config not found: {path}\n"
            f"copy block3/config.example.json to {path}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def run_all(cfg: dict[str, Any]):
    top = cfg.get("top_n", {})
    nrd_cfg = cfg.get("new_domains", {})
    return fetch_new_domains(
        top_n=top.get("new_domains", 50),
        max_days=nrd_cfg.get("max_days", 1),
        sample_limit=nrd_cfg.get("sample_limit", 70000),
        min_score=nrd_cfg.get("min_score", 55),
    )


def write_outputs(result, out_dir: Path, ts: datetime) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = ts.strftime("%Y-%m-%d")
    iso_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    md_path = out_dir / f"new-domains-{date_str}.md"
    html_path = out_dir / f"new-domains-{date_str}.html"

    md_path.write_text(render_markdown(result, iso_str), encoding="utf-8")
    html_path.write_text(render_html(result, iso_str), encoding="utf-8")
    return md_path, html_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Block 3 newly registered domains scanner")
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
    result = run_all(cfg)
    print("[INFO] fetch summary:")
    print(f"  {result.summary()}")

    md_path, html_path = write_outputs(result, args.out, ts)
    print(f"[INFO] {'1/1' if result.ok else '0/1'} sources ok, {len(result.items) if result.ok else 0} items total")
    print(f"[INFO] md   → {md_path}")
    print(f"[INFO] html → {html_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
