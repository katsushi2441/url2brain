from __future__ import annotations

import hmac
import time
import uuid
from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .articles import generate_announcement, generate_blog_article
from .config import settings
from .fetcher import FetchError, UrlFetcher
from .llm import ArticleBrain, BrainError
from . import persona as persona_mod
from . import poster
from .poster import PostError
from .schemas import (
    AnalyzeUrlRequest,
    BrainResponse,
    GenerateFromContentRequest,
    GenerateFromUrlRequest,
    GenerateFromUrlResult,
    PostAixsnsRequest,
    PostBluditRequest,
    PostBlueskyRequest,
    PostHatenaBlogRequest,
    PostHatenaBookmarkRequest,
    PostResult,
)

app = FastAPI(
    title="url2brain API",
    version=__version__,
    description="URL analysis + announcement/blog article generation. Never posts anywhere itself.",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
brain = ArticleBrain(settings)
fetcher = UrlFetcher(settings)


@app.middleware("http")
async def restrict_write_clients(request: Request, call_next: Callable):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and settings.allowed_client_ips:
        client_ip = request.client.host if request.client else ""
        if client_ip not in settings.allowed_client_ips and client_ip != "testclient":
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=403, content={"ok": False, "detail": "client IP is not allowed"})
    return await call_next(request)


def require_token(
    x_url2brain_token: str = Header(default=""),
    authorization: str = Header(default=""),
) -> None:
    if not settings.api_token:
        raise HTTPException(503, "URL2BRAIN_API_TOKEN is not configured")
    supplied_token = x_url2brain_token
    if not supplied_token and authorization.lower().startswith("bearer "):
        supplied_token = authorization[7:].strip()
    if not hmac.compare_digest(supplied_token, settings.api_token):
        raise HTTPException(401, "invalid API token")


@app.get("/health")
def health() -> dict:
    status = brain.health()
    return {
        "ok": True,
        "service": "url2brain",
        "version": __version__,
        "provider": settings.llm_provider,
        "model": settings.active_model,
        "llm": status,
    }


def _envelope(endpoint: str, model: str, started: float, result) -> BrainResponse:
    return BrainResponse(
        endpoint=endpoint,
        request_id=uuid.uuid4().hex[:16],
        model=model,
        latency_ms=round((time.monotonic() - started) * 1000),
        result=result.model_dump() if hasattr(result, "model_dump") else result,
    )


@app.post("/v1/analyze/url", response_model=BrainResponse, dependencies=[Depends(require_token)])
def analyze_url(payload: AnalyzeUrlRequest) -> BrainResponse:
    started = time.monotonic()
    try:
        source = fetcher.analyze(str(payload.url), payload.depth)
    except FetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _envelope("analyze/url", "oss2api", started, source)


@app.post("/v1/generate/announcement", response_model=BrainResponse, dependencies=[Depends(require_token)])
def generate_announcement_endpoint(payload: GenerateFromContentRequest) -> BrainResponse:
    started = time.monotonic()
    try:
        result = generate_announcement(brain, payload.source, payload.language, payload.tone, payload.provider)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _envelope("generate/announcement", brain.model_for(payload.provider), started, result)


@app.post("/v1/generate/blog-article", response_model=BrainResponse, dependencies=[Depends(require_token)])
def generate_blog_article_endpoint(payload: GenerateFromContentRequest) -> BrainResponse:
    started = time.monotonic()
    try:
        result = generate_blog_article(brain, payload.source, payload.language, payload.tone, payload.provider)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _envelope("generate/blog-article", brain.model_for(payload.provider), started, result)


@app.post("/v1/generate/from-url", response_model=BrainResponse, dependencies=[Depends(require_token)])
def generate_from_url(payload: GenerateFromUrlRequest) -> BrainResponse:
    """「URL入れるだけ」フロー用の合成エンドポイント: 解析→告知文→ブログ記事を1コールで返す。
    provider省略時はconfig既定(url2pub Webアプリ=ローカルGemma4)。x402ゲートウェイは
    provider="deepseek"を注入して有料コールをDeepSeekへ流す(ローカルGPUを本番系と競合させない)。"""
    started = time.monotonic()
    try:
        source = fetcher.analyze(str(payload.url), payload.depth)
    except FetchError as exc:
        raise HTTPException(502, f"fetch failed: {exc}") from exc
    try:
        announcement = generate_announcement(brain, source, payload.language, payload.tone, payload.provider)
        blog_article = generate_blog_article(brain, source, payload.language, payload.tone, payload.provider)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = GenerateFromUrlResult(source=source, announcement=announcement, blog_article=blog_article)
    return _envelope("generate/from-url", brain.model_for(payload.provider), started, result)


# 投稿エンドポイント群。ksnsposter(Bluesky/はてなブックマーク)とAIxSNS(aixec)を薄くラップする。
# url2brainは投稿先を増やさない・ロジックを書き換えない(AGENTS.md)。安全モデルはksnsposterに
# 合わせ、confirm_post=false(既定)なら実際には投稿せずdraft_readyのみ返す。

@app.post("/v1/post/bluesky", response_model=BrainResponse, dependencies=[Depends(require_token)])
def post_bluesky_endpoint(payload: PostBlueskyRequest) -> BrainResponse:
    started = time.monotonic()
    text = persona_mod.frame(payload.text, payload.persona, "announcement")
    try:
        raw = poster.post_bluesky(text, payload.url, payload.confirm_post)
    except PostError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = PostResult(ok=bool(raw.get("ok")), status=str(raw.get("status", "")), platform="bluesky", detail=raw)
    return _envelope("post/bluesky", "ksnsposter", started, result)


@app.post("/v1/post/hatena-bookmark", response_model=BrainResponse, dependencies=[Depends(require_token)])
def post_hatena_bookmark_endpoint(payload: PostHatenaBookmarkRequest) -> BrainResponse:
    started = time.monotonic()
    if not payload.confirm_post:
        result = PostResult(
            ok=True, status="draft_ready", platform="hatena-bookmark",
            detail={"url": str(payload.url), "comment": payload.comment, "tags": payload.tags,
                    "note": "confirm_post=true で実際に投稿します(ksnsposterの安全モデルに合わせて既定は下書きのみ)。"},
        )
        return _envelope("post/hatena-bookmark", "ksnsposter", started, result)
    try:
        raw = poster.post_hatena_bookmark(str(payload.url), payload.comment, payload.tags, payload.private)
    except PostError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = PostResult(ok=bool(raw.get("ok")), status=str(raw.get("status", "")), platform="hatena-bookmark", detail=raw)
    return _envelope("post/hatena-bookmark", "ksnsposter", started, result)


@app.post("/v1/post/aixsns", response_model=BrainResponse, dependencies=[Depends(require_token)])
def post_aixsns_endpoint(payload: PostAixsnsRequest) -> BrainResponse:
    started = time.monotonic()
    content = persona_mod.frame(payload.content, payload.persona, "announcement")
    if not payload.confirm_post:
        result = PostResult(
            ok=True, status="draft_ready", platform="aixsns",
            detail={"content": content, "author": payload.author,
                    "note": "confirm_post=true で実際に投稿します(ksnsposterの安全モデルに合わせて既定は下書きのみ)。"},
        )
        return _envelope("post/aixsns", "aixec", started, result)
    try:
        raw = poster.post_aixsns(content, payload.author)
    except PostError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = PostResult(ok=bool(raw.get("ok")), status=str(raw.get("status", "")), platform="aixsns", detail=raw)
    return _envelope("post/aixsns", "aixec", started, result)


@app.post("/v1/post/bludit", response_model=BrainResponse, dependencies=[Depends(require_token)])
def post_bludit_endpoint(payload: PostBluditRequest) -> BrainResponse:
    started = time.monotonic()
    body = persona_mod.frame(payload.body_markdown, payload.persona, "blog")
    if not payload.confirm_post:
        result = PostResult(
            ok=True, status="draft_ready", platform="bludit",
            detail={"title": payload.title, "category": payload.category, "tags": payload.tags,
                    "note": "confirm_post=true で実際に投稿します(ksnsposterの安全モデルに合わせて既定は下書きのみ)。"},
        )
        return _envelope("post/bludit", "kurage_blog", started, result)
    try:
        raw = poster.post_bludit(payload.title, body, payload.category, payload.tags)
    except PostError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = PostResult(ok=bool(raw.get("ok")), status=str(raw.get("status", "")), platform="bludit", detail=raw)
    return _envelope("post/bludit", "kurage_blog", started, result)


@app.post("/v1/post/hatena-blog", response_model=BrainResponse, dependencies=[Depends(require_token)])
def post_hatena_blog_endpoint(payload: PostHatenaBlogRequest) -> BrainResponse:
    started = time.monotonic()
    body = persona_mod.frame(payload.body_markdown, payload.persona, "blog")
    if not payload.confirm_post:
        result = PostResult(
            ok=True, status="draft_ready", platform="hatena-blog",
            detail={"title": payload.title,
                    "note": "confirm_post=true で実際に投稿します(ksnsposterの安全モデルに合わせて既定は下書きのみ)。"},
        )
        return _envelope("post/hatena-blog", "post_to_hatena", started, result)
    try:
        raw = poster.post_hatena_blog(payload.title, body)
    except PostError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = PostResult(ok=bool(raw.get("ok")), status=str(raw.get("status", "")), platform="hatena-blog", detail=raw)
    return _envelope("post/hatena-blog", "post_to_hatena", started, result)
