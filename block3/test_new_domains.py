from __future__ import annotations

import unittest

from block3.sources import (
    _extract_whoisds_downloads,
    _parse_domain_lines,
    _rank_domains,
    _score_new_domain,
)


class NewDomainSourceTests(unittest.TestCase):
    def test_extract_whoisds_downloads_returns_latest_links(self) -> None:
        html = """
        <a href="https://www.whoisds.com//whois-database/newly-registered-domains/MjAyNi0wNy0yMC56aXA=/nrd">Download</a>
        <a href="https://www.whoisds.com//whois-database/newly-registered-domains/MjAyNi0wNy0xOS56aXA=/nrd">Download</a>
        <a href="https://example.com/other.zip">Ignore</a>
        """

        downloads = _extract_whoisds_downloads(html, max_days=2)

        self.assertEqual(
            downloads,
            [
                "https://www.whoisds.com//whois-database/newly-registered-domains/MjAyNi0wNy0yMC56aXA=/nrd",
                "https://www.whoisds.com//whois-database/newly-registered-domains/MjAyNi0wNy0xOS56aXA=/nrd",
            ],
        )

    def test_parse_domain_lines_keeps_only_valid_domains(self) -> None:
        raw = """
        Domain Name
        ExampleAI.com
        bad line with spaces
        http://not-a-domain.com
        niche-research.tools
        localhost
        """

        domains = _parse_domain_lines(raw)

        self.assertEqual(domains, ["exampleai.com", "niche-research.tools"])

    def test_score_new_domain_prioritizes_commercial_ai_tools(self) -> None:
        strong = _score_new_domain("seoagent.ai")
        weak = _score_new_domain("xqz-481923.xyz")

        self.assertGreater(strong, weak)
        self.assertGreaterEqual(strong, 80)

    def test_rank_domains_spreads_equal_scores_across_initial_letters(self) -> None:
        domains = [
            "aaai.com",
            "abai.com",
            "acai.com",
            "adai.com",
            "baai.com",
            "bbai.com",
            "bcai.com",
            "bdai.com",
            "caai.com",
            "cbai.com",
            "ccai.com",
            "cdai.com",
            "daai.com",
            "dbai.com",
            "dcai.com",
            "ddai.com",
        ]

        ranked = _rank_domains(domains)
        top_initials = {domain[0] for domain, _score in ranked[:8]}

        self.assertGreaterEqual(len(top_initials), 4)


if __name__ == "__main__":
    unittest.main()
