#!/opt/bin/sh
# NetWeather domestic probe for Keenetic/Entware.
# IMPORTANT: probe traffic must leave through the direct ISP path, not HRNeo/AWG/VPN.
set -u

BASE_URL="${NETWEATHER_URL:-https://netweather.online}"
TOKEN="${NETWEATHER_AGENT_TOKEN:-}"
PROBE_KEY="${NETWEATHER_PROBE_KEY:-RU_HOME}"
PROBE_NAME="${NETWEATHER_PROBE_NAME:-Домашний интернет РФ}"
INTERVAL="${NETWEATHER_PROBE_INTERVAL:-60}"
CURL_BIN="${CURL_BIN:-/opt/bin/curl}"
TRACEROUTE_BIN="${TRACEROUTE_BIN:-traceroute}"
DIRECT_INTERFACE="${NETWEATHER_DIRECT_INTERFACE:-}"

if [ -z "$TOKEN" ]; then
  echo "NETWEATHER_AGENT_TOKEN is not set" >&2
  exit 2
fi
if [ ! -x "$CURL_BIN" ]; then
  CURL_BIN="$(command -v curl 2>/dev/null || true)"
fi
if [ -z "$CURL_BIN" ]; then
  echo "curl not found" >&2
  exit 3
fi

TAB="$(printf '\t')"
TMP="/tmp/netweather-probe.$$"
mkdir -p "$TMP" || exit 4
trap 'rm -rf "$TMP"' EXIT INT TERM

esc_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\r\n\t' '   '
}

ms() {
  awk -v v="$1" 'BEGIN{printf "%d", (v*1000)+0.5}'
}

delta_ms() {
  awk -v a="$1" -v b="$2" 'BEGIN{x=(a-b)*1000; if(x<0)x=0; printf "%d", x+0.5}'
}

probe_one() {
  id="$1"; target="$2"; min_code="$3"; max_code="$4"
  errfile="$TMP/err"
  : > "$errfile"
  iface_args=""
  if [ -n "$DIRECT_INTERFACE" ]; then
    iface_args="--interface $DIRECT_INTERFACE"
  fi

  # shellcheck disable=SC2086
  metrics="$("$CURL_BIN" -sS --max-time 12 -o /dev/null $iface_args     -w '%{http_code}\t%{remote_ip}\t%{time_namelookup}\t%{time_connect}\t%{time_appconnect}\t%{time_starttransfer}\t%{time_total}'     "$target" 2>"$errfile")"
  rc=$?

  oldifs="$IFS"; IFS="$TAB"
  set -- $metrics
  IFS="$oldifs"
  http_code="${1:-000}"; remote_ip="${2:-}"
  t_dns="${3:-0}"; t_connect="${4:-0}"; t_tls="${5:-0}"; t_start="${6:-0}"; t_total="${7:-0}"

  dns_ms="$(ms "$t_dns")"
  tcp_ms="$(delta_ms "$t_connect" "$t_dns")"
  if awk -v v="$t_tls" 'BEGIN{exit !(v>0)}'; then
    tls_ms="$(delta_ms "$t_tls" "$t_connect")"
    base="$t_tls"
  else
    tls_ms="null"
    base="$t_connect"
  fi
  http_ms="$(delta_ms "$t_start" "$base")"
  total_ms="$(ms "$t_total")"
  message="$(cat "$errfile" 2>/dev/null)"

  case "$rc" in
    0)
      if [ "$http_code" -ge "$min_code" ] 2>/dev/null && [ "$http_code" -le "$max_code" ] 2>/dev/null; then
        status="OK"; message="HTTP $http_code"
      else
        status="HTTP_ERROR"; message="HTTP $http_code, expected $min_code-$max_code"
      fi ;;
    6) status="DNS_ERROR" ;;
    7) status="TCP_ERROR" ;;
    28) status="TIMEOUT" ;;
    35|51|58|60) status="TLS_ERROR" ;;
    *) status="HTTP_ERROR" ;;
  esac

  [ "$http_code" = "000" ] && http_json="null" || http_json="$http_code"
  payload="{\"resource_id\":$id,\"status\":\"$status\",\"response_time_ms\":$total_ms,\"dns_ms\":$dns_ms,\"tcp_ms\":$tcp_ms,\"tls_ms\":$tls_ms,\"http_ms\":$http_ms,\"http_status\":$http_json,\"resolved_ip\":\"$(esc_json "$remote_ip")\",\"message\":\"$(esc_json "$message")\"}"

  "$CURL_BIN" -fsS --max-time 10     -H "X-NetWeather-Agent: $TOKEN"     -H "Content-Type: application/json"     -X POST     "$BASE_URL/api/agent/result?probe_key=$PROBE_KEY&probe_name=$(printf '%s' "$PROBE_NAME" | sed 's/ /%20/g')"     -d "$payload" >/dev/null || echo "NetWeather: submit failed for resource $id" >&2
}

run_checks() {
  config="$("$CURL_BIN" -fsS --max-time 10     -H "X-NetWeather-Agent: $TOKEN"     "$BASE_URL/api/agent/config.tsv?probe_key=$PROBE_KEY&probe_name=$(printf '%s' "$PROBE_NAME" | sed 's/ /%20/g')" 2>/dev/null)" || return 1

  printf '%s\n' "$config" | while IFS="$TAB" read -r id name target min_code max_code; do
    [ -z "${id:-}" ] && continue
    probe_one "$id" "$target" "$min_code" "$max_code"
  done
}

run_tasks() {
  tasks="$("$CURL_BIN" -fsS --max-time 10 \
    -H "X-NetWeather-Agent: $TOKEN" \
    "$BASE_URL/api/agent/tasks.tsv?probe_key=$PROBE_KEY&probe_name=$(printf '%s' "$PROBE_NAME" | sed 's/ /%20/g')" 2>/dev/null)" || return 0

  printf '%s\n' "$tasks" | while IFS="$TAB" read -r task_id resource_id task_type target min_code max_code; do
    [ -z "${task_id:-}" ] && continue
    outfile="$TMP/task.$task_id"
    if [ "$task_type" = "CHECK" ]; then
      probe_one "$resource_id" "$target" "${min_code:-200}" "${max_code:-399}"
      echo "domestic check completed" >"$outfile"
    else
      host="$(printf '%s' "$target" | sed -E 's#^[A-Za-z]+://##; s#/.*##; s/:.*##')"
      if command -v "$TRACEROUTE_BIN" >/dev/null 2>&1; then
        "$TRACEROUTE_BIN" -n -w 1 -q 1 -m 15 "$host" >"$outfile" 2>&1 || true
      else
        echo "traceroute is not available on this probe" >"$outfile"
      fi
    fi
    "$CURL_BIN" -fsS --max-time 15 \
      -H "X-NetWeather-Agent: $TOKEN" \
      -H "Content-Type: text/plain; charset=utf-8" \
      -X POST --data-binary "@$outfile" \
      "$BASE_URL/api/agent/tasks/$task_id/complete?probe_key=$PROBE_KEY" >/dev/null || true
  done
}

echo "NetWeather probe started: $PROBE_NAME ($PROBE_KEY)"
while true; do
  run_checks || echo "NetWeather: config fetch failed" >&2
  run_tasks
  sleep "$INTERVAL"
done
