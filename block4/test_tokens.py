from __future__ import annotations

import json
import sys
from pathlib import Path

from .sources import fetch_producthunt, fetch_youtube

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def main() -> int:
    if not CONFIG_PATH.exists():
        print(f"[ERR] config not found: {CONFIG_PATH}")
        print("      run: cp block4/config.example.json block4/config.json")
        return 2

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    ph_token = cfg.get("producthunt", {}).get("token", "")
    yt_key = cfg.get("youtube", {}).get("api_key", "")
    yt_region = cfg.get("youtube", {}).get("region_code", "US")

    print("=" * 50)
    print("Token validation (PH + YouTube only)")
    print("=" * 50)

    exit_code = 0
    tested = 0

    if not ph_token:
        print("[PH]  SKIP  (producthunt.token is empty)")
    else:
        tested += 1
        r = fetch_producthunt(token=ph_token, top_n=5)
        if r.ok and r.items:
            print(f"[PH]  OK    {len(r.items)} items fetched (token valid)")
        else:
            print(f"[PH]  FAIL  {r.error}")
            exit_code = 1

    if not yt_key:
        print("[YT]  SKIP  (youtube.api_key is empty)")
    else:
        tested += 1
        r = fetch_youtube(api_key=yt_key, region_code=yt_region, top_n=5)
        if r.ok and r.items:
            print(f"[YT]  OK    {len(r.items)} items fetched (api_key valid)")
        else:
            print(f"[YT]  FAIL  {r.error}")
            exit_code = 1

    print("=" * 50)
    if tested == 0:
        print("No tokens configured yet. Edit block4/config.json first.")
        return 0
    if exit_code == 0:
        print(f"All configured tokens are valid ({tested}/{tested} passed). Ready to run main.")
    else:
        print(f"Some tokens failed ({exit_code} failed). Check errors above.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
