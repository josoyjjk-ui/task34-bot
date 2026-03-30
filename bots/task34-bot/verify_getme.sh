#!/usr/bin/env bash
set -euo pipefail
TOKEN=$(security find-generic-password -s task34-bot-token -w)
curl -sS "https://api.telegram.org/bot${TOKEN}/getMe"
