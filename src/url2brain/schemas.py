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
    provider: str = Field(default="", pattern="^(|ollama|deepseek)$")


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
    provider: str = Field(default="", pattern="^(|ollama|deepseek)$")


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


class PostBlueskyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=280)
    url: str = ""
    confirm_post: bool = False


class PostHatenaBookmarkRequest(BaseModel):
    url: HttpUrl
    comment: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)
    private: bool = False
    confirm_post: bool = False


class PostAixsnsRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    author: str = Field(default="url2brain", max_length=40)
    confirm_post: bool = False


class PostBluditRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body_markdown: str = Field(min_length=1)
    category: str = Field(default="url2pub", max_length=40)
    tags: str = Field(default="url2pub", max_length=200)
    confirm_post: bool = False


class PostHatenaBlogRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body_markdown: str = Field(min_length=1)
    confirm_post: bool = False


class PostResult(BaseModel):
    ok: bool
    status: str
    platform: str
    detail: dict[str, Any] = Field(default_factory=dict)
