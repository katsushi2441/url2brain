from __future__ import annotations

import requests

from .config import Settings
from .schemas import AnalyzeUrlResult


class FetchError(RuntimeError):
    pass


class UrlFetcher:
    """url2ai の oss2api(/url/analyze) を内部で呼ぶ薄いクライアント。
    url2brainはスクレイパーを二重実装しない(AGENTS.md参照)。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, url: str, depth: str = "full") -> AnalyzeUrlResult:
        try:
            response = requests.post(
                f"{self.settings.oss2api_url}/oss2api/url/analyze",
                json={"url": url, "depth": depth, "format": "markdown"},
                timeout=self.settings.fetch_timeout,
            )
        except requests.RequestException as exc:
            raise FetchError(f"oss2api request failed: {exc}") from exc
        if response.status_code >= 400:
            raise FetchError(f"oss2api returned {response.status_code}: {response.text[:300]}")
        body = response.json()
        if body.get("ok") is False:
            raise FetchError(f"oss2api reported failure: {body}")
        return AnalyzeUrlResult(
            url=str(body.get("url") or url),
            title=str(body.get("title") or ""),
            description=str(body.get("description") or ""),
            headings=list(body.get("headings") or []),
            content=str(body.get("markdown") or body.get("content") or body.get("summary") or ""),
            links=list(body.get("links") or []),
        )
