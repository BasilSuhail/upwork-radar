#!/usr/bin/env bash
# Rebuild on a fresh machine from Gitea:
#   git clone <gitea url> upwork-radar && cd upwork-radar && git checkout feat/paste-radar   (or main once merged)
#   scripts/restore.sh
# Nothing is deleted: an existing ~/.upwork-radar is moved aside, not overwritten.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
DATA=${RADAR_HOME:-$HOME/.upwork-radar}
cd "$REPO"
remote=$(git remote get-url gitea >/dev/null 2>&1 && echo gitea || echo origin)
git fetch -q "$remote" backup
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git show FETCH_HEAD:private.tar.gz.enc > "$tmp/private.tar.gz.enc"
read -rsp "Backup passphrase: " pass; echo
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in "$tmp/private.tar.gz.enc" -pass fd:3 3<<<"$pass" \
  | tar -xzf - -C "$tmp" || { echo "Wrong passphrase (or damaged file)."; exit 1; }

if [[ -e $DATA ]]; then
  echo "$DATA exists; moving it to $DATA.before-restore.$(date +%s)"
  mv "$DATA" "$DATA.before-restore.$(date +%s)"
fi
mv "$tmp/private/upwork-radar" "$DATA"
if [[ -f $tmp/private/repo.env ]]; then
  [[ -e $REPO/.env ]] && mv "$REPO/.env" "$REPO/.env.before-restore.$(date +%s)"
  mv "$tmp/private/repo.env" "$REPO/.env"
fi
if [[ $(uname) == Linux ]]; then mkdir -p ~/.config && (umask 077; printf '%s\n' "$pass" > "${RADAR_PASSFILE:-$HOME/.config/upwork-radar-backup-pass}")
else security add-generic-password -U -s upwork-radar-backup -a "$USER" -w "$pass"; fi
echo "Restored $DATA. Start it: python3 -m radar serve  (or the systemd unit in scripts/linux/)."
