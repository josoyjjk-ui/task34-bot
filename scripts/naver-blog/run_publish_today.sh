#!/bin/bash
set -euo pipefail
mkdir -p /tmp/openclaw/uploads
cp '/Users/fireant/.openclaw/media/tool-image-generation/daily-report-latest-ai---4ab1028f-a431-4608-9f4c-1be6c13e254e.jpg' /tmp/openclaw/uploads/daily_blog_20260408.png
python3 /Users/fireant/.openclaw/workspace/scripts/naver-blog/publish.py
