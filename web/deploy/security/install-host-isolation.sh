#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${EUID}" -eq 0 ]] || { echo "Run as root" >&2; exit 77; }

PROJECT="/opt/NetWeather/web"
DEPLOY_USER="netweather-deploy"
SECURITY_SRC="${PROJECT}/deploy/security"

for cmd in docker nft python3 systemctl sudo visudo; do
  command -v "${cmd}" >/dev/null || { echo "Missing required command: ${cmd}" >&2; exit 69; }
done
id "${DEPLOY_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${DEPLOY_USER}"

echo "=== REMOVE ROOT-EQUIVALENT DOCKER ACCESS ==="
if id -nG "${DEPLOY_USER}" | tr ' ' '\n' | grep -qx docker; then
  gpasswd -d "${DEPLOY_USER}" docker
fi
passwd -l "${DEPLOY_USER}" >/dev/null 2>&1 || true

echo "=== MOVE NETWEATHER SECRETS OUTSIDE DEPLOY TREE ==="
install -d -o root -g root -m 0700 /etc/netweather
if [[ ! -s /etc/netweather/netweather.env ]]; then
  [[ -s "${PROJECT}/.env" ]] || { echo "Neither /etc/netweather/netweather.env nor ${PROJECT}/.env exists" >&2; exit 78; }
  install -o root -g root -m 0600 "${PROJECT}/.env" /etc/netweather/netweather.env
fi
chmod 0600 /etc/netweather/netweather.env
chown root:root /etc/netweather/netweather.env
rm -f "${PROJECT}/.env"

echo "=== INSTALL ROOT-OWNED SECURITY BOUNDARY ==="
install -o root -g root -m 0755 "${SECURITY_SRC}/netweather-deploy-helper" /usr/local/sbin/netweather-deploy-helper
install -o root -g root -m 0755 "${SECURITY_SRC}/netweather-ssh-gate" /usr/local/sbin/netweather-ssh-gate
install -o root -g root -m 0755 "${SECURITY_SRC}/netweather-egress-guard" /usr/local/sbin/netweather-egress-guard
install -o root -g root -m 0644 "${SECURITY_SRC}/netweather-egress-guard.service" /etc/systemd/system/netweather-egress-guard.service

cat >/etc/sudoers.d/netweather-deploy <<'SUDOERS'
Defaults:netweather-deploy !authenticate
netweather-deploy ALL=(root) NOPASSWD: /usr/local/sbin/netweather-deploy-helper *
SUDOERS
chmod 0440 /etc/sudoers.d/netweather-deploy
visudo -cf /etc/sudoers.d/netweather-deploy >/dev/null

echo "=== LOCK SSH KEY TO ONE FORCED COMMAND ==="
AUTH="/home/${DEPLOY_USER}/.ssh/authorized_keys"
[[ -f "${AUTH}" ]] || { echo "Missing ${AUTH}; install the deployment public key first" >&2; exit 78; }
python3 - "${AUTH}" <<'PY'
import re, sys
from pathlib import Path
p=Path(sys.argv[1])
lines=[x.strip() for x in p.read_text().splitlines() if x.strip() and not x.lstrip().startswith("#")]
keys=[]
for line in lines:
    m=re.search(r'(?<!\S)(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|sk-ssh-ed25519@openssh\.com)\s+\S+(?:\s+.*)?$', line)
    if m:
        keys.append(m.group(0))
if len(keys) != 1:
    raise SystemExit(f"Expected exactly one deployment public key, found {len(keys)}")
prefix='restrict,command="/usr/local/sbin/netweather-ssh-gate" '
p.write_text(prefix+keys[0]+"\n")
PY
chown -R root:root "/home/${DEPLOY_USER}"
chmod 0755 "/home/${DEPLOY_USER}"
chmod 0700 "/home/${DEPLOY_USER}/.ssh"
chmod 0600 "${AUTH}"

echo "=== CREATE DEDICATED DOCKER NETWORK / DATA VOLUME ==="
if ! docker network inspect netweather-isolated >/dev/null 2>&1; then
  docker network create --driver bridge --subnet 172.30.250.0/28 --gateway 172.30.250.1 \
    -o com.docker.network.bridge.enable_icc=false netweather-isolated >/dev/null
fi
ACTUAL="$(docker network inspect -f '{{(index .IPAM.Config 0).Subnet}}' netweather-isolated)"
[[ "${ACTUAL}" == "172.30.250.0/28" ]] || { echo "Unexpected netweather-isolated subnet: ${ACTUAL}" >&2; exit 67; }

docker volume inspect web_netweather_data >/dev/null 2>&1 || docker volume create web_netweather_data >/dev/null
VOLUME_PATH="$(docker volume inspect -f '{{.Mountpoint}}' web_netweather_data)"
chown -R 10001:10001 "${VOLUME_PATH}"
chmod 0750 "${VOLUME_PATH}"

echo "=== APPLY KERNEL-LEVEL NETWORK ISOLATION ==="
systemctl daemon-reload
systemctl enable --now netweather-egress-guard.service
nft list table inet netweather_guard >/dev/null

echo "=== REMOVE DEPLOY USER WRITE ACCESS TO APPLICATION TREE ==="
chown -R root:root /opt/NetWeather/web
chmod -R o-w,g-w /opt/NetWeather/web

echo "=== SECURITY STATE ==="
echo "deploy groups: $(id -nG "${DEPLOY_USER}")"
echo "env: $(stat -c '%U:%G %a %n' /etc/netweather/netweather.env)"
echo "authorized_keys: $(stat -c '%U:%G %a %n' "${AUTH}")"
echo "network: ${ACTUAL}"
nft list table inet netweather_guard

cat <<'NEXT'

Host isolation is installed.
The deploy SSH key now has:
  - no interactive shell
  - no port/agent/X11 forwarding
  - no Docker group membership
  - exactly one sudo entry, for the root-owned NetWeather deployment helper

Next: enable repository variable NETWEATHER_DEPLOY_ENABLED=true
and run the "Deploy NetWeather Web" workflow once.
NEXT
