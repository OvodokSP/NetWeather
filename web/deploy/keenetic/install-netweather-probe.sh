#!/opt/bin/sh
set -eu
umask 077

REPOSITORY="${NETWEATHER_REPOSITORY:-OvodokSP/NetWeather}"
REF="${NETWEATHER_REF:-}"
DIRECT_INTERFACE="${NETWEATHER_DIRECT_INTERFACE:-eth2.4}"
PROBE_KEY="${NETWEATHER_PROBE_KEY:-RU_VORONEZH_HOME}"
PROBE_NAME="${NETWEATHER_PROBE_NAME:-Домашний Keenetic Воронеж}"
BASE_URL="${NETWEATHER_URL:-https://netweather.online}"
TOKEN="${NETWEATHER_AGENT_TOKEN:-}"
CURL_BIN="${CURL_BIN:-/opt/bin/curl}"

PROBE_SHA256="a6654ee11ddb8985b2af90bc0ddc05253bf140ed96af7c0076e4ee449b0af3c6"
SERVICE_SHA256="c5e9f129b6004bf811683b6fc79c07263e37a6b107c86af068e1d0bc50abebeb"

[ "$(id -u)" -eq 0 ] || { echo "root required" >&2; exit 77; }
[ -n "$REF" ] || { echo "NETWEATHER_REF must be the verified 40-character Git commit" >&2; exit 64; }
case "$REF" in *[!0-9a-f]*|'') echo "invalid NETWEATHER_REF" >&2; exit 64 ;; esac
[ "${#REF}" -eq 40 ] || { echo "NETWEATHER_REF must contain 40 characters" >&2; exit 64; }
case "$REPOSITORY" in
  *[!A-Za-z0-9_.\/-]*|*//*|/*|*/|'') echo "invalid NETWEATHER_REPOSITORY" >&2; exit 64 ;;
esac
case "$DIRECT_INTERFACE" in *[!A-Za-z0-9_.:-]*|'') echo "invalid NETWEATHER_DIRECT_INTERFACE" >&2; exit 64 ;; esac
case "$PROBE_KEY" in *[!A-Za-z0-9_.-]*|'') echo "invalid NETWEATHER_PROBE_KEY" >&2; exit 64 ;; esac
case "$PROBE_NAME" in
  *"'"*|*"
"*|'') echo "invalid NETWEATHER_PROBE_NAME" >&2; exit 64 ;;
esac
case "$BASE_URL" in
  https://* ) ;;
  * ) echo "NETWEATHER_URL must use https://" >&2; exit 64 ;;
esac
case "$BASE_URL" in *[!A-Za-z0-9._~:\/\[\]-]*|*/) echo "invalid NETWEATHER_URL" >&2; exit 64 ;; esac
[ -x "$CURL_BIN" ] || { echo "Entware curl not found at $CURL_BIN" >&2; exit 69; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum not found" >&2; exit 69; }
command -v ip >/dev/null 2>&1 || { echo "ip command not found" >&2; exit 69; }
ip link show dev "$DIRECT_INTERFACE" >/dev/null 2>&1 || {
  echo "confirmed direct WAN interface is unavailable: $DIRECT_INTERFACE" >&2
  exit 69
}

if [ -z "$TOKEN" ]; then
  [ -r /dev/tty ] || { echo "NETWEATHER_AGENT_TOKEN is required" >&2; exit 64; }
  printf 'NETWEATHER_AGENT_TOKEN: ' >/dev/tty
  stty -echo </dev/tty
  IFS= read -r TOKEN </dev/tty || true
  stty echo </dev/tty
  printf '\n' >/dev/tty
fi
[ -n "$TOKEN" ] || { echo "NETWEATHER_AGENT_TOKEN is empty" >&2; exit 64; }
case "$TOKEN" in *[!0-9A-Fa-f]*|'') echo "NETWEATHER_AGENT_TOKEN must be hexadecimal" >&2; exit 64 ;; esac
[ "${#TOKEN}" -eq 64 ] || { echo "NETWEATHER_AGENT_TOKEN must contain 64 hexadecimal characters" >&2; exit 64; }

mkdir -p /opt/tmp
TMP="$(mktemp -d /opt/tmp/netweather-probe.XXXXXX)"
cleanup() { rm -rf "$TMP"; }
stop_install() { cleanup; trap - EXIT; exit 130; }
trap cleanup EXIT
trap stop_install INT TERM HUP
RAW="https://raw.githubusercontent.com/$REPOSITORY/$REF/web/deploy/keenetic"

download_verified() {
  name="$1" expected="$2"
  "$CURL_BIN" -fsSL --proto '=https' --tlsv1.2 --interface "$DIRECT_INTERFACE" \
    "$RAW/$name" -o "$TMP/$name"
  actual="$(sha256sum "$TMP/$name" | awk '{print $1}')"
  [ "$actual" = "$expected" ] || {
    echo "checksum mismatch for $name" >&2
    exit 65
  }
}

download_verified netweather-probe.sh "$PROBE_SHA256"
download_verified S99netweather-probe "$SERVICE_SHA256"
sh -n "$TMP/netweather-probe.sh"
sh -n "$TMP/S99netweather-probe"

/opt/etc/init.d/S99netweather-probe stop >/dev/null 2>&1 || true
mkdir -p /opt/sbin /opt/etc/init.d /opt/var/run/netweather-probe /opt/var/log
cp "$TMP/netweather-probe.sh" /opt/sbin/.netweather-probe.new
chmod 0755 /opt/sbin/.netweather-probe.new
mv /opt/sbin/.netweather-probe.new /opt/sbin/netweather-probe
cp "$TMP/S99netweather-probe" /opt/etc/init.d/.S99netweather-probe.new
chmod 0755 /opt/etc/init.d/.S99netweather-probe.new
mv /opt/etc/init.d/.S99netweather-probe.new /opt/etc/init.d/S99netweather-probe

cat >"$TMP/netweather-probe.env" <<EOF
NETWEATHER_URL=$BASE_URL
NETWEATHER_AGENT_TOKEN=$TOKEN
NETWEATHER_PROBE_KEY=$PROBE_KEY
NETWEATHER_PROBE_NAME='$PROBE_NAME'
NETWEATHER_AGENT_VERSION=0.3.10
NETWEATHER_PROBE_INTERVAL=60
NETWEATHER_DIRECT_INTERFACE=$DIRECT_INTERFACE
CURL_BIN=/opt/bin/curl
TRACEROUTE_BIN=traceroute
EOF
cp "$TMP/netweather-probe.env" /opt/etc/.netweather-probe.env.new
chmod 0600 /opt/etc/.netweather-probe.env.new
mv /opt/etc/.netweather-probe.env.new /opt/etc/netweather-probe.env

set -a
# shellcheck disable=SC1091
. /opt/etc/netweather-probe.env
set +a
NETWEATHER_RUN_ONCE=true NETWEATHER_STATE_DIR=/opt/var/run/netweather-probe /opt/sbin/netweather-probe
/opt/etc/init.d/S99netweather-probe start
/opt/etc/init.d/S99netweather-probe status || true

echo "NetWeather Keenetic probe installed."
echo "Status: /opt/etc/init.d/S99netweather-probe status"
echo "Log:    tail -n 50 /opt/var/log/netweather-probe.log"
