# url2brain Agent Rules

- Follow `/home/kojima/work/AGENTS.md`, `WORKFLOW.md`, and `QUALITY_RULES.md`.
- This is the brain for URL2AI Publisher: URL analysis + announcement/blog article generation +
  posting to Bluesky / Hatena Bookmark / AIxSNS (2026-07-21: posting was moved in-process per the
  user's original design). Posting logic itself is never reimplemented here — `poster.py` imports
  `ksnsposter.bluesky_poster` / `ksnsposter.hatena_bookmark` directly (editable install,
  `--no-deps --ignore-requires-python`, no vendor/fork) and calls aixec's AIxSNS API directly.
  Hatena Blog (`vwork/scripts/post_to_hatena.py`) and VWork Blog (`vwork/scripts/publish.py`) are
  NOT wired in yet — both write markdown files into the vwork git repo and push, a much bigger
  blast radius than a plain API POST; wiring those needs an explicit safety-design decision first.
- All `/v1/post/*` endpoints default to `confirm_post=false` (draft-only, mirroring ksnsposter's own
  safety model). Never flip that default or auto-post without the caller explicitly asking.
- Default LLM is `gemma4:12b-it-qat` (local Ollama); DeepSeek (`deepseek-v4-flash`) is selectable via
  `URL2BRAIN_LLM_PROVIDER=deepseek`, mirroring kcbrain/kfxbrain.
- Always send `think: false` to Gemma 4.
- URL fetching/extraction is not reimplemented here — it calls url2ai's existing
  `oss2api /url/analyze` (and `/url/browse` for JS-heavy pages) internally. Do not vendor a second
  scraper.
- Do not add silent model or template fallbacks. Return a visible error.
- Never commit `.env`.
