from __future__ import annotations

from .llm import ArticleBrain, BrainError
from .schemas import AnalyzeUrlResult, AnnouncementResult, BlogArticleResult

_LANGUAGE_NAME = {"ja": "Japanese", "en": "English"}


def _evidence_block(source: AnalyzeUrlResult) -> str:
    headings = "\n".join(f"- {h.get('tag', '')}: {h.get('text', '')}" for h in source.headings[:20])
    content = source.content[:6000]
    return (
        f"URL: {source.url}\n"
        f"Title: {source.title}\n"
        f"Description: {source.description}\n"
        f"Headings:\n{headings}\n\n"
        f"Content (markdown, truncated):\n{content}"
    )


def generate_announcement(brain: ArticleBrain, source: AnalyzeUrlResult, language: str, tone: str) -> AnnouncementResult:
    lang_name = _LANGUAGE_NAME.get(language, "Japanese")
    prompt = (
        "You are writing a short social-media announcement post introducing the page below to readers. "
        f"Write in {lang_name}. Tone: {tone}. Ground every claim in the supplied evidence only — do not "
        "invent facts, numbers, or opinions not present in the content. Include the URL. Keep it under "
        "280 characters (count characters, not words) so it fits common SNS length limits.\n\n"
        f"{_evidence_block(source)}\n\n"
        'Return exactly one JSON object: {"text": "..."}'
    )
    result = brain.generate_json(prompt, max_tokens=400)
    text = str(result.get("text") or "").strip()
    if not text:
        raise BrainError("model returned an empty announcement text")
    return AnnouncementResult(text=text, char_count=len(text))


def generate_blog_article(brain: ArticleBrain, source: AnalyzeUrlResult, language: str, tone: str) -> BlogArticleResult:
    lang_name = _LANGUAGE_NAME.get(language, "Japanese")
    prompt = (
        "You are writing a short blog article introducing the page below to readers who have not seen it. "
        f"Write in {lang_name}. Tone: {tone}. Ground every claim in the supplied evidence only — do not "
        "invent facts, numbers, or opinions not present in the content. If the content is insufficient to "
        "say something, say so honestly instead of inventing it. Include a markdown link to the source URL. "
        "Body length: roughly 300-600 words in the target language.\n\n"
        f"{_evidence_block(source)}\n\n"
        'Return exactly one JSON object: {"title": "...", "body_markdown": "..."}'
    )
    result = brain.generate_json(prompt, max_tokens=1800)
    title = str(result.get("title") or "").strip()
    body = str(result.get("body_markdown") or "").strip()
    if not title or not body:
        raise BrainError("model returned an incomplete blog article (missing title or body)")
    return BlogArticleResult(title=title, body_markdown=body)
