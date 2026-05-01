#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-${CAPTAINLABS_REMOTE:-}}"
REMOTE_DIR="${2:-${CAPTAINLABS_REMOTE_DIR:-~/code/captains-prediction-companion}}"
LOCAL_DIR="${3:-${CAPTAINLABS_LOCAL_DIR:-$HOME/code/captains-prediction-companion}}"
INCLUDE_STATE="${INCLUDE_STATE:-0}"

if [ -z "$REMOTE" ]; then
  printf 'Usage: %s user@host [remote_dir] [local_dir]\n' "$0" >&2
  exit 1
fi

mkdir -p "$LOCAL_DIR"

RSYNC_OPTS=(
  -az
  --delete
  --info=progress2
  --exclude=.git
  --exclude=node_modules
  --exclude=.next
  --exclude=.env
  --exclude=.env.local
  --exclude=.env.*.local
  --exclude=coverage
  --exclude=dist
  --exclude=build
)

if [ "$INCLUDE_STATE" != "1" ]; then
  RSYNC_OPTS+=(--exclude=data)
fi

printf 'Syncing code from %s:%s to %s\n' "$REMOTE" "$REMOTE_DIR" "$LOCAL_DIR"
rsync "${RSYNC_OPTS[@]}" "$REMOTE:$REMOTE_DIR/" "$LOCAL_DIR/"

if [ "$INCLUDE_STATE" = "1" ]; then
  printf 'Included remote data directory in sync.\n'
else
  printf 'State excluded. To include it, rerun with INCLUDE_STATE=1.\n'
fi

printf '\nSuggested next step locally:\n'
printf '  cd %s && git status --short\n' "$LOCAL_DIR"
