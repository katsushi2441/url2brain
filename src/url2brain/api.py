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
from .schemas import (
    AnalyzeUrlRequest,
    BrainResponse,
    GenerateFromContentRequest,
    GenerateFromUrlRequest,
    GenerateFromUrlResult,
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
        result = generate_announcement(brain, payload.source, payload.language, payload.tone)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _envelope("generate/announcement", brain.model, started, result)


@app.post("/v1/generate/blog-article", response_model=BrainResponse, dependencies=[Depends(require_token)])
def generate_blog_article_endpoint(payload: GenerateFromContentRequest) -> BrainResponse:
    started = time.monotonic()
    try:
        result = generate_blog_article(brain, payload.source, payload.language, payload.tone)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _envelope("generate/blog-article", brain.model, started, result)


@app.post("/v1/generate/from-url", response_model=BrainResponse, dependencies=[Depends(require_token)])
def generate_from_url(payload: GenerateFromUrlRequest) -> BrainResponse:
    """「URL入れるだけ」フロー用の合成エンドポイント: 解析→告知文→ブログ記事を1コールで返す。"""
    started = time.monotonic()
    try:
        source = fetcher.analyze(str(payload.url), payload.depth)
    except FetchError as exc:
        raise HTTPException(502, f"fetch failed: {exc}") from exc
    try:
        announcement = generate_announcement(brain, source, payload.language, payload.tone)
        blog_article = generate_blog_article(brain, source, payload.language, payload.tone)
    except BrainError as exc:
        raise HTTPException(502, str(exc)) from exc
    result = GenerateFromUrlResult(source=source, announcement=announcement, blog_article=blog_article)
    return _envelope("generate/from-url", brain.model, started, result)
