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

# 실제 git repo root를 감지 (task34-bot/가 아닌 상위 workspace)
GIT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
cd "$GIT_ROOT"

echo "[safe-push] Git root: $GIT_ROOT"
echo "[safe-push] Branch: $BRANCH"

# 1. task34-bot 하위 변경사항이 있으면 commit
BOT_CHANGES="$(git status --porcelain task34-bot/)"
if [ -n "$BOT_CHANGES" ]; then
    MSG="${1:-auto: $(date '+%Y-%m-%d %H:%M:%S') update)}"
    echo "[safe-push] Staging task34-bot changes..."
    git add task34-bot/
    echo "[safe-push] Committing: $MSG"
    git commit -m "$MSG"
else
    echo "[safe-push] No task34-bot changes to commit."
fi

# 2. 작업공간에 다른 dirty 파일이 있으면 stash
STASHED=false
if [ -n "$(git status --porcelain)" ]; then
    echo "[safe-push] Stashing uncommitted changes before rebase..."
    git stash --include-untracked -q
    STASHED=true
fi

# 3. pull --rebase (핵심 재발방지 로직)
echo "[safe-push] Pulling with rebase from $REMOTE/$BRANCH..."
REBASE_OK=true
if ! git pull --rebase "$REMOTE" "$BRANCH"; then
    echo "[safe-push] ❌ Rebase FAILED! Aborting rebase and exiting without push."
    git rebase --abort 2>/dev/null || true
    # stash 복원 시도
    if [ "$STASHED" = true ]; then
        git stash pop -q 2>/dev/null || true
    fi
    exit 1
fi

# 4. push
echo "[safe-push] Pushing to $REMOTE/$BRANCH..."
if ! git push "$REMOTE" "$BRANCH"; then
    echo "[safe-push] ❌ Push FAILED!"
    if [ "$STASHED" = true ]; then
        git stash pop -q 2>/dev/null || true
    fi
    exit 1
fi

# 5. stash 복원
if [ "$STASHED" = true ]; then
    echo "[safe-push] Restoring stashed changes..."
    git stash pop -q
fi

echo "[safe-push] ✅ Push completed successfully!"
