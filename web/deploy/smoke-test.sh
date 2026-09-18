#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://127.0.0.1:18081}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi
TOKEN="${NETWEATHER_API_TOKEN:-}"
AUTH=()
if [[ -n "$TOKEN" ]]; then AUTH=(-H "Authorization: Bearer $TOKEN"); fi
ok(){ printf 'PASS  %s\n' "$1"; }
get(){ curl -fsS "$BASE_URL$1" >/dev/null; ok "GET $1"; }

get /api/health
get /api/system
get /api/dashboard
get /api/groups
get /api/resource-catalog
get '/api/resource-catalog/match?target=https%3A%2F%2Fgithub.com'
SESSION_JSON="$(curl -fsS "$BASE_URL/api/session")"
ok 'GET /api/session'
AUTH_REQUIRED="$(python3 -c 'import json,sys; print(str(json.load(sys.stdin).get("auth_required", False)).lower())' <<<"$SESSION_JSON")"
get /api/resources
get '/api/realtime?minutes=60&scope=EXTERNAL'
get '/api/events?limit=10'
get /api/incidents
get '/api/history?hours=24'
curl -fsSI "$BASE_URL/" >/dev/null; ok 'HEAD /'
FRONTEND_HTML="$(curl -fsS "$BASE_URL/")"
grep -Fq 'NetWeather' <<<"$FRONTEND_HTML"; ok 'GET / frontend'
curl -fsS "$BASE_URL/assets/dashboard.js?v=0.3.8" >/dev/null; ok 'GET /assets/dashboard.js'
curl -fsS "$BASE_URL/assets/dashboard.css?v=0.3.8" >/dev/null; ok 'GET /assets/dashboard.css'

if [[ "$AUTH_REQUIRED" == "true" && -z "$TOKEN" ]]; then
  echo 'SKIP  write/diagnostic tests: authentication is required and NETWEATHER_API_TOKEN is unavailable'
  exit 0
fi

if [[ -n "$TOKEN" ]]; then
  curl -fsS "${AUTH[@]}" "$BASE_URL/api/auth/verify" >/dev/null; ok 'GET /api/auth/verify'
else
  ok 'OPEN MODE write access'
fi

TMP_JSON="$(curl -fsS -X POST "${AUTH[@]}" -H 'Content-Type: application/json' "$BASE_URL/api/resources" -d '{"name":"__NetWeather self-test__","target":"https://example.com","group_name":"CUSTOM","interval_seconds":86400,"alerts_enabled":false}')"
RID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$TMP_JSON")"
cleanup(){ curl -fsS -X DELETE "${AUTH[@]}" "$BASE_URL/api/resources/$RID" >/dev/null 2>&1 || true; }
trap cleanup EXIT
ok 'POST /api/resources'
curl -fsS -X PATCH "${AUTH[@]}" -H 'Content-Type: application/json' "$BASE_URL/api/resources/$RID" -d '{"slow_threshold_ms":1200,"failure_threshold":3}' >/dev/null; ok 'PATCH /api/resources/{id}'
curl -fsS -X POST "${AUTH[@]}" "$BASE_URL/api/resources/$RID/check" >/dev/null; ok 'POST /api/resources/{id}/check'
curl -fsS "$BASE_URL/api/resources/$RID" >/dev/null; ok 'GET /api/resources/{id}'
curl -fsS -X POST "${AUTH[@]}" "$BASE_URL/api/resources/$RID/trace" >/dev/null; ok 'POST /api/resources/{id}/trace'
curl -fsS -X POST "${AUTH[@]}" "$BASE_URL/api/check-all" >/dev/null; ok 'POST /api/check-all'
cleanup
trap - EXIT
ok 'DELETE /api/resources/{id}'
echo 'NetWeather smoke test: PASS'
