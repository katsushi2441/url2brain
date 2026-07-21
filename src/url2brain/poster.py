from __future__ import annotations

import os
from typing import Any

import requests
from ksnsposter.bluesky_poster import create_bluesky_post, resolve_bluesky_config
from ksnsposter.hatena_bookmark import add_bookmark, resolve_hatena_config

# AIxSNS: aixecのkgrowth_jobs.py/vworkのpublish.pyと同じ投稿先(認証不要のJSON POST)。
AIXSNS_API = os.environ.get("URL2BRAIN_AIXSNS_API", "https://aixec.exbridge.jp/api.php?path=posts")


class PostError(RuntimeError):
    pass


def post_bluesky(text: str, url: str, confirm_post: bool) -> dict[str, Any]:
    """ksnsposterのbluesky_posterをそのまま呼ぶ。confirm_post=Falseなら投稿せずdraft_readyのみ返す
    (ksnsposterの既定の安全モデルをそのまま踏襲)。"""
    try:
        config = resolve_bluesky_config()
    except ValueError as exc:
        raise PostError(str(exc)) from exc
    return create_bluesky_post(text=text, url=url, confirm_post=confirm_post, config=config)


def post_hatena_bookmark(
    url: str, comment: str, tags: list[str] | None = None, private: bool = False
) -> dict[str, Any]:
    try:
        config = resolve_hatena_config()
    except ValueError as exc:
        raise PostError(str(exc)) from exc
    return add_bookmark(url=url, comment=comment, tags=tags, private=private, config=config)


def post_aixsns(content: str, author: str = "url2brain") -> dict[str, Any]:
    try:
        response = requests.post(AIXSNS_API, json={"author": author, "content": content}, timeout=15)
    except requests.RequestException as exc:
        raise PostError(f"AIxSNS request failed: {exc}") from exc
    if response.status_code >= 400:
        raise PostError(f"AIxSNS returned {response.status_code}: {response.text[:300]}")
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:500]}
    return {
        "ok": bool(body.get("ok", True)),
        "status": "posted",
        "platform": "aixsns",
        "item": body.get("item"),
    }
