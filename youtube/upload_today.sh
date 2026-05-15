#!/bin/bash
# 今日のぶんを6本までアップロード（YouTube APIのクオータ上限）
# 使い方: ./upload_today.sh
cd "$(dirname "$0")"
python3 upload_videos.py --limit 6 2>&1 | grep -v -E "FutureWarning|NotOpenSSL|warnings.warn|best-effort|OpenSSL|google-auth past|google-api-core supporting|googleapis.com|/Users/don/Library/Python"
