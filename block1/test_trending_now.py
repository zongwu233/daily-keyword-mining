import json
import tempfile
from pathlib import Path
from unittest import TestCase

from block1.sources import fetch_google_trends_json


class TrendingNowAdapterTests(TestCase):
    def test_maps_only_successful_trending_now_items_to_existing_model(self):
        payload = {
            "source": "google_trending_now",
            "fetch_status": "success",
            "items": [
                {
                    "position": 1,
                    "query": "  solar rebate  ",
                    "normalized_query": "solar rebate",
                    "search_volume_label": "5000+",
                    "increase_percentage": 200,
                    "active": True,
                    "categories": [{"id": 18, "name": "Technology"}],
                    "explore_url": "https://trends.google.com/trends/explore?q=solar+rebate",
                },
                {"position": 2, "query": "second topic"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "US.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = fetch_google_trends_json(path, "US", 1)

        self.assertTrue(result.ok)
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertEqual(item.title, "solar rebate")
        self.assertEqual(item.url, payload["items"][0]["explore_url"])
        self.assertEqual(item.extra["approx_traffic"], "5000+")
        self.assertEqual(item.extra["increase_percentage"], 200)
        self.assertEqual(item.extra["categories"], [{"id": 18, "name": "Technology"}])

    def test_fallback_required_for_non_success_or_empty_response(self):
        for envelope in (
            {"source": "rss_limited", "fetch_status": "manual_review_required", "items": []},
            {"source": "google_trending_now", "fetch_status": "success", "items": []},
        ):
            with self.subTest(envelope=envelope), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "US.json"
                path.write_text(json.dumps(envelope), encoding="utf-8")
                result = fetch_google_trends_json(path, "US", 30)

            self.assertFalse(result.ok)
            self.assertEqual(result.items, [])
