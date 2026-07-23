from __future__ import annotations

# url2pubのu2p_persona_frame(PHP)と同じ枠付けロジック。x402経由の投稿でも同じ人格分け
# (Bluesky/Bludit=Kurage、AIxSNS/はてなブログ=bittensorman)を適用するための移植。

_ANNOUNCEMENT = {
    "kurage": lambda text: f"🪼 {text}",
    "bittensorman": lambda text: f"【開発者より】\n{text}\n— bittensorman",
}
_BLOG = {
    "kurage": lambda text: f"🪼 Kurageです。今日はこちらをご紹介しますね。\n\n{text}\n\n---\n*— Kurage*",
    "bittensorman": lambda text: f"開発者・経営者の視点から。\n\n{text}\n\n---\n*— bittensorman(開発者・経営者)*",
}


def frame(text: str, persona: str, kind: str) -> str:
    text = (text or "").strip()
    if not persona:
        return text
    table = _ANNOUNCEMENT if kind == "announcement" else _BLOG
    fn = table.get(persona)
    return fn(text) if fn else text
