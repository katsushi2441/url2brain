from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeUrlRequest(BaseModel):
    url: HttpUrl
    depth: str = Field(default="full", pattern="^(basic|full)$")


class AnalyzeUrlResult(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    headings: list[dict[str, str]] = Field(default_factory=list)
    content: str = ""
    links: list[dict[str, str]] = Field(default_factory=list)


class GenerateFromContentRequest(BaseModel):
    """記事生成系の共通入力。source は analyze/url の結果をそのまま渡すのが基本だが、
    呼び出し側が既に持っている素材(title/content等)を直接渡してもよい。"""

    url: str = ""
    source: AnalyzeUrlResult
    language: str = Field(default="ja", pattern="^(ja|en)$")
    tone: str = Field(default="neutral", max_length=40)


class AnnouncementResult(BaseModel):
    text: str
    char_count: int


class BlogArticleResult(BaseModel):
    title: str
    body_markdown: str


class GenerateFromUrlRequest(BaseModel):
    url: HttpUrl
    depth: str = Field(default="full", pattern="^(basic|full)$")
    language: str = Field(default="ja", pattern="^(ja|en)$")
    tone: str = Field(default="neutral", max_length=40)


class GenerateFromUrlResult(BaseModel):
    source: AnalyzeUrlResult
    announcement: AnnouncementResult
    blog_article: BlogArticleResult


class BrainResponse(BaseModel):
    endpoint: str
    request_id: str
    model: str
    latency_ms: int
    result: dict[str, Any]
