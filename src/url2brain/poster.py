from __future__ import annotations

import os
import re
import sys
from typing import Any

import requests
from ksnsposter.bluesky_poster import create_bluesky_post, resolve_bluesky_config
from ksnsposter.hatena_bookmark import add_bookmark, resolve_hatena_config

# AIxSNS: aixecのkgrowth_jobs.py/vworkのpublish.pyと同じ投稿先(認証不要のJSON POST)。
AIXSNS_API = os.environ.get("URL2BRAIN_AIXSNS_API", "https://aixec.exbridge.jp/api.php?path=posts")

# Bludit(Kurageブログ): 所有者はkfreqai(kurage-advisory/kurage_blog.py)。kcbrain/kfxbrainと
# 同じく一方向で利用する(循環依存を避ける、2026-07-17方針)。VWork Blog(git push前提)は
# 2026-07-21にやめ、こちらのurl2pubカテゴリに統一。
_KURAGE_ADVISORY_DIR = "/home/kojima/work/kfreqai/kurage-advisory"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:60] or "post"


def post_bludit(title: str, body_markdown: str, category: str = "url2pub", tags: str = "url2pub") -> dict[str, Any]:
    if _KURAGE_ADVISORY_DIR not in sys.path:
        sys.path.insert(0, _KURAGE_ADVISORY_DIR)
    try:
        import kurage_blog  # noqa: PLC0415
    except ImportError as exc:
        raise PostError(f"kurage_blog import failed: {exc}") from exc
    try:
        slug, permalink = kurage_blog.post_to_bludit(
            title=title, slug=_slugify(title), body=body_markdown, tags=tags, category=category,
        )
    except Exception as exc:
        raise PostError(f"Bludit post failed: {exc}") from exc
    return {"ok": True, "status": "posted", "platform": "bludit", "slug": slug, "permalink": permalink}


# はてなブログ: vwork/scripts/post_to_hatena.pyのsend_mail()をそのまま呼ぶ(SMTP送信のみ、
# vworkのfrontmatterファイル/git状態には依存しない)。
_VWORK_SCRIPTS_DIR = "/home/kojima/work/vwork/scripts"


def post_hatena_blog(title: str, body_markdown: str) -> dict[str, Any]:
    if _VWORK_SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _VWORK_SCRIPTS_DIR)
    try:
        import post_to_hatena  # noqa: PLC0415
    except ImportError as exc:
        raise PostError(f"post_to_hatena import failed: {exc}") from exc
    try:
        post_to_hatena.send_mail(title, body_markdown)
    except KeyError as exc:
        raise PostError(f"missing SMTP/Hatena env var: {exc}") from exc
    except Exception as exc:
        raise PostError(f"Hatena Blog send failed: {exc}") from exc
    return {"ok": True, "status": "posted", "platform": "hatena-blog", "title": title}


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
