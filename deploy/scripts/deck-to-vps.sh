#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-${CAPTAINLABS_REMOTE:-}}"
LOCAL_DIR="${2:-${CAPTAINLABS_LOCAL_DIR:-$HOME/code/captains-prediction-companion}}"
REMOTE_DIR="${3:-${CAPTAINLABS_REMOTE_DIR:-~/code/captains-prediction-companion}}"
INCLUDE_STATE="${INCLUDE_STATE:-0}"

if [ -z "$REMOTE" ]; then
  printf 'Usage: %s user@host [local_dir] [remote_dir]\n' "$0" >&2
  exit 1
fi

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

printf 'Syncing code from %s to %s:%s\n' "$LOCAL_DIR" "$REMOTE" "$REMOTE_DIR"
rsync "${RSYNC_OPTS[@]}" "$LOCAL_DIR/" "$REMOTE:$REMOTE_DIR/"

if [ "$INCLUDE_STATE" = "1" ] && [ -d "$LOCAL_DIR/data" ]; then
  printf 'Included local data directory in sync.\n'
else
  printf 'State excluded. To include it, rerun with INCLUDE_STATE=1.\n'
fi

printf '\nSuggested next step on remote:\n'
printf '  ssh %s "cd %s && git status --short && tmux attach -t captain-dev || tmux new -s captain-dev"\n' "$REMOTE" "$REMOTE_DIR"
