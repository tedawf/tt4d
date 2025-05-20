#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_FILE="/var/log/tt4d_scraper.log"

if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Cron: $ENV_FILE not found. Exiting." >>"$LOG_FILE"
  exit 1
fi

if [ -z "$TT4D_API_KEY" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Cron: TT4D_API_KEY is not set or empty in $ENV_FILE. Exiting." >>"$LOG_FILE"
  exit 1
fi

API_URL="http://localhost:8000/scrape/task"

echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - Cron: Triggering scrape task via API (Key: ${TT4D_API_KEY:0:4}****)." >>"$LOG_FILE"

RESPONSE_CODE=$(
  curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$API_URL" \
    -H "X-API-Key: $TT4D_API_KEY" \
    -H "Content-Type: application/json"
)

if [ "$RESPONSE_CODE" -eq 200 ] || [ "$RESPONSE_CODE" -eq 202 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - Cron: API call successful (HTTP $RESPONSE_CODE)." >>"$LOG_FILE"
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Cron: API call failed (HTTP $RESPONSE_CODE)." >>"$LOG_FILE"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - Cron: Trigger script finished." >>"$LOG_FILE"
echo "---" >>"$LOG_FILE"
