from unittest import TestCase
from unittest.mock import Mock, patch

from common.models import Item
from block1.sources import JEV_ENDPOINT, screen_google_trends


class TrendScreeningTests(TestCase):
    def setUp(self):
        self.items = [
            Item("Google Trends (US)", "durable topic", "https://example.test/1"),
            Item("Google Trends (US)", "celebrity news", "https://example.test/2"),
            Item("Google Trends (US)", "ambiguous term", "https://example.test/3"),
        ]

    @patch("block1.sources.requests.post")
    def test_separates_research_from_transient_and_uncertain_terms(self, post):
        post.side_effect = [
            self.response("research", 0.91),
            self.response("transient", 0.98),
            self.response("uncertain", 0.52),
        ]

        kept, excluded, error = screen_google_trends(self.items, "US", "secret")

        self.assertIsNone(error)
        self.assertEqual([item.title for item in kept], ["durable topic"])
        self.assertEqual([item.extra["jev_decision"] for item in excluded], ["transient", "uncertain"])
        self.assertEqual(post.call_count, 3)
        self.assertTrue(all(call.args[0] == JEV_ENDPOINT for call in post.call_args_list))
        self.assertEqual(post.call_args_list[0].kwargs["json"]["state"]["candidate"]["term"], "durable topic")

    @patch("block1.sources.requests.post")
    def test_api_failure_returns_all_original_terms_for_unscreened_fallback(self, post):
        from requests import RequestException

        response = Mock()
        response.raise_for_status.side_effect = RequestException("offline")
        post.return_value = response

        kept, excluded, error = screen_google_trends(self.items, "US", "secret")

        self.assertEqual(kept, self.items)
        self.assertEqual(excluded, [])
        self.assertIn("showing unscreened trends", error)

    def test_missing_key_keeps_all_terms_without_request(self):
        with patch("block1.sources.requests.post") as post:
            kept, excluded, error = screen_google_trends(self.items, "US", "")

        self.assertEqual(kept, self.items)
        self.assertEqual(excluded, [])
        self.assertIn("TYPESAFE_API_KEY", error)
        post.assert_not_called()

    @staticmethod
    def response(choice, confidence):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "answers": {"screen": {"choice": choice, "confidence": confidence}}
        }
        return response
