#!/usr/bin/env bash
# safe-push.sh — 재발방지: push 전 항상 rebase pull 수행
# Usage: ./safe-push.sh [commit message]
#
# 이 스크립트는 git push 실패를 방지하기 위해
# push 전에 반드시 git pull --rebase origin main을 수행합니다.
# rebase가 실패하면 push하지 않고 non-zero로 종료합니다.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="main"
REMOTE="origin"

cd "$SCRIPT_DIR"

echo "[safe-push] Repository: $SCRIPT_DIR"
echo "[safe-push] Branch: $BRANCH"

# 1. 변경사항이 있으면 commit
if [ -n "$(git status --porcelain)" ]; then
    MSG="${1:-auto: $(date '+%Y-%m-%d %H:%M:%S') update)}"
    echo "[safe-push] Staging all changes..."
    git add -A .
    echo "[safe-push] Committing: $MSG"
    git commit -m "$MSG"
else
    echo "[safe-push] No local changes to commit."
fi

# 2. pull --rebase (핵심 재발방지 로직)
echo "[safe-push] Pulling with rebase from $REMOTE/$BRANCH..."
if ! git pull --rebase "$REMOTE" "$BRANCH"; then
    echo "[safe-push] ❌ Rebase FAILED! Aborting rebase and exiting without push."
    git rebase --abort 2>/dev/null || true
    exit 1
fi

# 3. push
echo "[safe-push] Pushing to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH"

echo "[safe-push] ✅ Push completed successfully!"
