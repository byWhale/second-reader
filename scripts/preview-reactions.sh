#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

book_id="${BOOK_ID:-}"
chapter_id="${CHAPTER_ID:-}"
base_url="${API_BASE_URL:-$DEFAULT_API_BASE_URL}"

if [[ -z "$book_id" || -z "$chapter_id" ]]; then
  echo "usage: make preview-reactions BOOK_ID=<bookId> CHAPTER_ID=<chapterId> [API_BASE_URL=http://localhost:8000]"
  exit 1
fi

cd "$FRONTEND_DIR"
npm run preview-reactions -- --book-id "$book_id" --chapter-id "$chapter_id" --base-url "$base_url"
