from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Item:
    source: str
    title: str
    url: str
    score: int | None = None
    comments: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "score": self.score,
            "comments": self.comments,
            "extra": self.extra,
        }


@dataclass
class FetchResult:
    source: str
    ok: bool
    items: list[Item] = field(default_factory=list)
    error: str | None = None
    fetched_at: str = ""

    def summary(self) -> str:
        if self.ok:
            return f"[OK] {self.source}: {len(self.items)} items"
        return f"[FAIL] {self.source}: {self.error}"
