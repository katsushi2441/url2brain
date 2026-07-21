# url2brain Design

- Same brain, two callers: the URL2AI Publisher website (url2ai.exbridge.jp, human users) and the
  OSS `url2pub` body / any x402 AI agent. Improving url2brain once improves both simultaneously.
- Pipeline: `analyze/url` (fetch+extract via oss2api) -> `generate/announcement` and
  `generate/blog-article` (LLM, from the extracted content) -> caller posts wherever it wants.
  url2brain never posts; it only analyzes and writes.
- `generate/from-url` is a convenience endpoint that chains analyze + both generators in one call,
  for the "just paste a URL" web flow.
- Output language defaults to Japanese; callable in English via `language`.
- No exchange/broker/social-account credentials live here — those stay in the destination-specific
  posting tools.
