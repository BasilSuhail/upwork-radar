#!/usr/bin/env bash
# Full backup to the owner's own Gitea: every code branch, plus ~/.upwork-radar (profile, database, config)
# packed into ONE AES-256 encrypted file on branch `backup`. No readable secret ever lands in git.
# GitHub (origin) gets code only, through normal pushes; this script never touches it.
# Gitea address: GITEA_BACKUP_URL in ~/.upwork-radar/radar.conf.
# Passphrase: asked once, then kept in the macOS keychain (service "upwork-radar-backup") or, on Linux,
# ~/.config/upwork-radar-backup-pass (mode 600). Restore: scripts/restore.sh
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
DATA=${RADAR_HOME:-$HOME/.upwork-radar}
# shellcheck source=/dev/null
source "$DATA/radar.conf"
: "${GITEA_BACKUP_URL:?set GITEA_BACKUP_URL in $DATA/radar.conf}"

PASSFILE=${RADAR_PASSFILE:-$HOME/.config/upwork-radar-backup-pass}
if [[ $(uname) == Linux ]]; then pass=$(cat "$PASSFILE" 2>/dev/null || true)
else pass=$(security find-generic-password -s upwork-radar-backup -w 2>/dev/null || true); fi
if [[ -z $pass ]]; then
  [[ -t 0 ]] || { echo "No backup passphrase saved yet: run this once by hand."; exit 1; }
  read -rsp "New backup passphrase (needed to restore - write it down): " pass; echo
  read -rsp "Again: " again; echo
  [[ $pass == "$again" && -n $pass ]] || { echo "Passphrases differ."; exit 1; }
  if [[ $(uname) == Linux ]]; then mkdir -p ~/.config && (umask 077; printf '%s\n' "$pass" > "$PASSFILE")
  else security add-generic-password -s upwork-radar-backup -a "$USER" -w "$pass"; fi
fi

cd "$REPO"
git remote get-url gitea >/dev/null 2>&1 || git remote add gitea "$GITEA_BACKUP_URL"
git push -q gitea --all
git push -q gitea --tags

# Private data: consistent DB copy even while the web page is writing to it.
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/private/upwork-radar"
rsync -a --exclude 'radar.db*' "$DATA/" "$tmp/private/upwork-radar/"
[[ -f $DATA/radar.db ]] && python3 -c 'import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d)' \
  "$DATA/radar.db" "$tmp/private/upwork-radar/radar.db"
[[ -f $REPO/.env ]] && cp "$REPO/.env" "$tmp/private/repo.env"
tar -czf "$tmp/private.tar.gz" -C "$tmp" private
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in "$tmp/private.tar.gz" -out "$tmp/private.tar.gz.enc" -pass fd:3 3<<<"$pass"

# Branch `backup` holds only the encrypted file, one commit per snapshot (never force-pushed).
# Built in a throwaway repo so no extra branch ever appears in this one (or in `push --all`).
wt="$tmp/wt"
git init -q "$wt"
git -C "$wt" config user.name "$(git config user.name)"
git -C "$wt" config user.email "$(git config user.email)"
if git ls-remote --exit-code -q "$GITEA_BACKUP_URL" backup >/dev/null 2>&1; then
  git -C "$wt" fetch -q "$GITEA_BACKUP_URL" backup
  git -C "$wt" checkout -q FETCH_HEAD
fi
cp "$tmp/private.tar.gz.enc" "$wt/private.tar.gz.enc"
git -C "$wt" add -f private.tar.gz.enc
git -C "$wt" commit -q -m "chore(backup): snapshot $(date '+%Y-%m-%d %H:%M')"
git -C "$wt" push -q "$GITEA_BACKUP_URL" HEAD:refs/heads/backup
echo "Backed up to Gitea: code branches + backup ($(du -h "$tmp/private.tar.gz.enc" | cut -f1) encrypted)."
