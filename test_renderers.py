from __future__ import annotations

import re
import unittest

from block1.renderer import render_html as render_trends_html
from block1.renderer import render_markdown as render_trends_markdown
from block3.renderer import render_html as render_domains_html
from block3.renderer import render_markdown as render_domains_markdown
from block4.renderer import render_html as render_digest_html
from block4.renderer import render_markdown as render_digest_markdown
from common.models import FetchResult, Item


TITLE_RE = re.compile(r"<title>(.*?)</title>")
H1_RE = re.compile(r"<h1>(.*?)</h1>")
OLD_PUBLIC_COPY = (
    "Block 1",
    "Block 3",
    "Block 4",
    "生成于",
    "数据源",
    "源状态",
    "所有源都失败",
    "新注册域名",
    "趋势扫描",
    "社区源头",
    " 条",
)


class RendererLanguageTests(unittest.TestCase):
    def test_trends_report_uses_english_public_copy(self) -> None:
        html = render_trends_html([_sample_result("Wikipedia Top")], "2026-07-27T08:00:00+08:00")
        markdown = render_trends_markdown([_sample_result("Wikipedia Top")], "2026-07-27T08:00:00+08:00")

        self.assert_report_copy(html, markdown)

    def test_new_domains_report_uses_english_public_copy(self) -> None:
        result = _sample_result("WhoisDS Newly Registered Domains")
        html = render_domains_html(result, "2026-07-27T08:00:00+08:00")
        markdown = render_domains_markdown(result, "2026-07-27T08:00:00+08:00")

        self.assert_report_copy(html, markdown)

    def test_community_digest_uses_english_public_copy(self) -> None:
        html = render_digest_html([_sample_result("Hacker News")], "2026-07-27T08:00:00+08:00")
        markdown = render_digest_markdown([_sample_result("Hacker News")], "2026-07-27T08:00:00+08:00")

        self.assert_report_copy(html, markdown)

    def assert_report_copy(self, html: str, markdown: str) -> None:
        self.assertIn('<html lang="en">', html)
        title = _required_match(TITLE_RE, html)
        heading = _required_match(H1_RE, html)
        self.assertNotIn("Block", title)
        self.assertNotIn("Block", heading)
        self.assertNotIn("# Block", markdown)
        for phrase in OLD_PUBLIC_COPY:
            self.assertNotIn(phrase, html)
            self.assertNotIn(phrase, markdown)


def _sample_result(source: str) -> FetchResult:
    return FetchResult(
        source=source,
        ok=True,
        items=[
            Item(
                source=source,
                title="Sample opportunity",
                url="https://example.com/sample",
                score=1200,
                comments=34,
                extra={"description": "Sample description", "language": "Python"},
            )
        ],
    )


def _required_match(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"Pattern did not match: {pattern.pattern}")
    return match.group(1)


if __name__ == "__main__":
    unittest.main()
