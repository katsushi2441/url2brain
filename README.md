# url2brain

URL2AI Publisherの「頭脳」。URLを1つ渡すと、内容を解析し、SNS告知文とブログ記事を生成します。投稿は一切行いません(投稿先ごとの既存ツールが担当)。

Web版(url2ai.exbridge.jp、人間向け)とOSS版(url2pub、AIエージェント向けx402 API)は**同じurl2brainを共用**します。ブレインを1つ改善すれば、両方が同時に賢くなります。

## エンドポイント

- `POST /v1/analyze/url` — URLを取得・構造化抽出(url2aiのoss2api `/url/analyze`を内部利用。二重スクレイパーは持たない)
- `POST /v1/generate/announcement` — 解析結果からSNS告知文(280字以内)を生成
- `POST /v1/generate/blog-article` — 解析結果からブログ記事(タイトル+Markdown本文)を生成
- `POST /v1/generate/from-url` — 上記3つを1コールで実行する合成エンドポイント(「URL入れるだけ」フロー用)

すべて認証必須(`X-URL2BRAIN-Token`ヘッダ、または`Authorization: Bearer`)。

## LLM

既定は`gemma4:12b-it-qat`(ローカルOllama)。`URL2BRAIN_LLM_PROVIDER=deepseek`でDeepSeek(`deepseek-v4-flash`)に切替可能(kcbrain/kfxbrainと同じ選択式)。

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.sample .env
# URL2BRAIN_API_TOKENを設定
set -a; source .env; set +a
.venv/bin/uvicorn url2brain.api:app --app-dir src --host 0.0.0.0 --port 18332
```

`oss2api`(url2ai)が`URL2BRAIN_OSS2API_URL`(既定 `http://127.0.0.1:8015`)で稼働している必要があります。

## 実測(2026-07-21)

`generate/from-url`をkfxbrain.exbridge.jp/に対して実行し、動作確認済み:
- HTTP 200、65.8秒(gemma4、初回)
- announcement: 178〜191字、事実に基づく内容・URL付き
- blog_article: タイトル+約400字のMarkdown本文、出典リンク付き
