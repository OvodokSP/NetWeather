#!/opt/bin/sh
# NetWeather domestic probe for Keenetic/Entware.
# IMPORTANT: probe traffic must leave through the direct ISP path, not HRNeo/AWG/VPN.
set -u

BASE_URL="${NETWEATHER_URL:-https://netweather.online}"
TOKEN="${NETWEATHER_AGENT_TOKEN:-}"
PROBE_KEY="${NETWEATHER_PROBE_KEY:-RU_HOME}"
PROBE_NAME="${NETWEATHER_PROBE_NAME:-Домашний интернет РФ}"
AGENT_VERSION="${NETWEATHER_AGENT_VERSION:-0.3.10}"
INTERVAL="${NETWEATHER_PROBE_INTERVAL:-60}"
CURL_BIN="${CURL_BIN:-/opt/bin/curl}"
TRACEROUTE_BIN="${TRACEROUTE_BIN:-traceroute}"
DIRECT_INTERFACE="${NETWEATHER_DIRECT_INTERFACE:-}"
RUN_ONCE="${NETWEATHER_RUN_ONCE:-false}"
STATE_DIR="${NETWEATHER_STATE_DIR:-/opt/var/run/netweather-probe}"

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
if [ -z "$DIRECT_INTERFACE" ]; then
  echo "NETWEATHER_DIRECT_INTERFACE is required; refusing a probe that could use VPN/policy routing" >&2
  exit 4
fi
case "$PROBE_KEY" in
  *[!A-Za-z0-9_.-]*|'') echo "NETWEATHER_PROBE_KEY contains unsupported characters" >&2; exit 5 ;;
esac
case "$PROBE_NAME" in
  *[\&\?\#]*) echo "NETWEATHER_PROBE_NAME contains unsupported URL characters" >&2; exit 5 ;;
esac
if command -v ip >/dev/null 2>&1 && ! ip link show dev "$DIRECT_INTERFACE" >/dev/null 2>&1; then
  echo "direct interface does not exist: $DIRECT_INTERFACE" >&2
  exit 6
fi

TAB="$(printf '\t')"
TMP="/tmp/netweather-probe.$$"
mkdir -p "$TMP" "$STATE_DIR" || exit 7
cleanup() { rm -rf "$TMP"; }
stop_probe() { cleanup; exit 0; }
trap cleanup EXIT
trap stop_probe INT TERM HUP
LAST_SUCCESS_FILE="$STATE_DIR/last-success"

esc_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\r\n\t' '   '
}

urlencode() {
  LC_ALL=C od -An -tx1 | awk '{for (i = 1; i <= NF; i++) printf "%%%s", toupper($i)}'
}

PROBE_KEY_QUERY="$(printf '%s' "$PROBE_KEY" | urlencode)"
PROBE_NAME_QUERY="$(printf '%s' "$PROBE_NAME" | urlencode)"
AGENT_VERSION_QUERY="$(printf '%s' "$AGENT_VERSION" | urlencode)"

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
  metrics="$("$CURL_BIN" -sS --max-time 12 -o /dev/null --interface "$DIRECT_INTERFACE" \
    -w '%{http_code}\t%{remote_ip}\t%{time_namelookup}\t%{time_connect}\t%{time_appconnect}\t%{time_starttransfer}\t%{time_total}' \
    "$target" 2>"$errfile")"
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

  "$CURL_BIN" -fsS --max-time 10 --interface "$DIRECT_INTERFACE" \
    -H "X-NetWeather-Agent: $TOKEN" -H "Content-Type: application/json" -X POST \
    "$BASE_URL/api/agent/result?probe_key=$PROBE_KEY_QUERY&probe_name=$PROBE_NAME_QUERY&agent_version=$AGENT_VERSION_QUERY" \
    -d "$payload" >/dev/null || {
      echo "NetWeather: submit failed for resource $id" >&2
      return 1
    }
}

run_checks() {
  config_file="$TMP/config.tsv"
  "$CURL_BIN" -fsS --max-time 10 --interface "$DIRECT_INTERFACE" \
    -H "X-NetWeather-Agent: $TOKEN" \
    "$BASE_URL/api/agent/config.tsv?probe_key=$PROBE_KEY_QUERY&probe_name=$PROBE_NAME_QUERY&agent_version=$AGENT_VERSION_QUERY" \
    >"$config_file" 2>/dev/null || return 1

  failed=0
  while IFS="$TAB" read -r id name target min_code max_code; do
    [ -z "${id:-}" ] && continue
    probe_one "$id" "$target" "$min_code" "$max_code" || failed=1
  done <"$config_file"
  return "$failed"
}

run_tasks() {
  tasks="$("$CURL_BIN" -fsS --max-time 10 --interface "$DIRECT_INTERFACE" \
    -H "X-NetWeather-Agent: $TOKEN" \
    "$BASE_URL/api/agent/tasks.tsv?probe_key=$PROBE_KEY_QUERY&probe_name=$PROBE_NAME_QUERY&agent_version=$AGENT_VERSION_QUERY" 2>/dev/null)" || return 0

  printf '%s\n' "$tasks" | while IFS="$TAB" read -r task_id resource_id task_type target min_code max_code; do
    [ -z "${task_id:-}" ] && continue
    outfile="$TMP/task.$task_id"
    if [ "$task_type" = "CHECK" ]; then
      probe_one "$resource_id" "$target" "${min_code:-200}" "${max_code:-399}" || continue
      echo "domestic check completed" >"$outfile"
    else
      host="$(printf '%s' "$target" | sed -E 's#^[A-Za-z]+://##; s#/.*##; s/:.*##')"
      if command -v "$TRACEROUTE_BIN" >/dev/null 2>&1; then
        "$TRACEROUTE_BIN" -n -w 1 -q 1 -m 15 -i "$DIRECT_INTERFACE" "$host" >"$outfile" 2>&1 || true
      else
        echo "traceroute is not available on this probe" >"$outfile"
      fi
    fi
    "$CURL_BIN" -fsS --max-time 15 --interface "$DIRECT_INTERFACE" \
      -H "X-NetWeather-Agent: $TOKEN" \
      -H "Content-Type: text/plain; charset=utf-8" \
      -X POST --data-binary "@$outfile" \
      "$BASE_URL/api/agent/tasks/$task_id/complete?probe_key=$PROBE_KEY" >/dev/null || true
  done
}

echo "NetWeather probe started: $PROBE_NAME ($PROBE_KEY), direct interface: $DIRECT_INTERFACE"
while true; do
  if run_checks; then
    date +%s >"$LAST_SUCCESS_FILE"
  else
    echo "NetWeather: one or more checks failed" >&2
    cycle_failed=1
  fi
  run_tasks
  if [ "$RUN_ONCE" = "true" ]; then
    [ "${cycle_failed:-0}" -eq 0 ]
    exit $?
  fi
  cycle_failed=0
  sleep "$INTERVAL"
done
