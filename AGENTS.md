# url2brain Agent Rules

- Follow `/home/kojima/work/AGENTS.md`, `WORKFLOW.md`, and `QUALITY_RULES.md`.
- This is the brain for URL2AI Publisher: URL analysis + announcement/blog article generation.
  Posting to SNS/blog destinations happens in `url2pub` (or the destinations' own tools:
  `ksnsposter`, `vwork/scripts/publish.py`, `vwork/scripts/post_to_hatena.py`, aixec's AIxSNS API).
  url2brain never posts anywhere itself.
- Default LLM is `gemma4:12b-it-qat` (local Ollama); DeepSeek (`deepseek-v4-flash`) is selectable via
  `URL2BRAIN_LLM_PROVIDER=deepseek`, mirroring kcbrain/kfxbrain.
- Always send `think: false` to Gemma 4.
- URL fetching/extraction is not reimplemented here — it calls url2ai's existing
  `oss2api /url/analyze` (and `/url/browse` for JS-heavy pages) internally. Do not vendor a second
  scraper.
- Do not add silent model or template fallbacks. Return a visible error.
- Never commit `.env`.
