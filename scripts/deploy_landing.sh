#!/usr/bin/env bash
# landing/ を heteml(url2brain.exbridge.jp)へデプロイする。
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . /home/kojima/work/aixec/.env; set +a

REMOTE="/web/url2brain_exbridge_jp"
for f in index.html url2brain.html robots.txt sitemap.xml assets/style.css assets/icon.png; do
  curl --fail --ftp-create-dirs -T "landing/$f" \
    "ftp://${FTP_USER}:${FTP_PASS}@${FTP_HOST}${REMOTE}/$f"
  echo "deployed landing/$f"
done
echo "-> https://url2brain.exbridge.jp/"
