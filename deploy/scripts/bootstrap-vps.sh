#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/captainslab/captains-prediction-companion}"
APP_SLUG="${APP_SLUG:-captains-prediction-companion}"
RUN_USER="${RUN_USER:-${SUDO_USER:-$USER}}"
if [ "$RUN_USER" = "$(id -un)" ]; then
  RUN_HOME="$HOME"
else
  RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
fi
if [ -z "$RUN_HOME" ]; then
  printf 'Unable to determine home directory for RUN_USER=%s\n' "$RUN_USER" >&2
  exit 1
fi
DEV_DIR="${DEV_DIR:-${RUN_HOME}/code/${APP_SLUG}}"
PROD_DIR="${PROD_DIR:-/srv/captainlabs}"
STATE_DIR="${STATE_DIR:-/var/lib/captains}"
ENV_DIR="${ENV_DIR:-/etc/captainlabs}"
DOMAIN="${DOMAIN:-captainlabs.io}"
AUTO_START="${AUTO_START:-0}"
INSTALL_NGINX_CONFIG="${INSTALL_NGINX_CONFIG:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

log() {
  printf '\n==> %s\n' "$1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  }
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

run_as_user() {
  if [ "$(id -un)" = "$RUN_USER" ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -u "$RUN_USER" -- "$@"
  elif command -v runuser >/dev/null 2>&1; then
    runuser -u "$RUN_USER" -- "$@"
  else
    printf 'Need sudo or runuser to execute as %s\n' "$RUN_USER" >&2
    exit 1
  fi
}

apt_install() {
  export DEBIAN_FRONTEND=noninteractive
  as_root apt-get update
  as_root apt-get install -y "$@"
}

ensure_node() {
  local major
  if command -v node >/dev/null 2>&1; then
    major="$(node -p "process.versions.node.split('.')[0]")"
    if [ "$major" -ge 20 ]; then
      printf 'Node %s already present; skipping install.\n' "$(node --version)"
      return
    fi
  fi

  log "Installing Node.js 22.x"
  apt_install ca-certificates curl gnupg
  curl -fsSL https://deb.nodesource.com/setup_22.x | as_root bash -
  apt_install nodejs
}

clone_or_update_repo() {
  local target_dir="$1"
  if [ -d "$target_dir/.git" ]; then
    log "Updating repo in $target_dir"
    run_as_user git -C "$target_dir" fetch --all --prune
    run_as_user git -C "$target_dir" pull --rebase
  elif [ -d "$target_dir" ] && [ -n "$(find "$target_dir" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    log "Using existing non-git working tree in $target_dir"
  else
    log "Cloning repo into $target_dir"
    run_as_user mkdir -p "$(dirname "$target_dir")"
    run_as_user git clone "$REPO_URL" "$target_dir"
  fi
}

install_repo_deps() {
  local target_dir="$1"
  log "Installing backend deps in $target_dir"
  if [ -f "$target_dir/package-lock.json" ]; then
    run_as_user bash -lc "cd '$target_dir' && npm ci"
  else
    run_as_user bash -lc "cd '$target_dir' && npm install"
  fi

  log "Installing frontend deps in $target_dir/frontend"
  if [ -f "$target_dir/frontend/package-lock.json" ]; then
    run_as_user bash -lc "cd '$target_dir/frontend' && npm ci"
  else
    run_as_user bash -lc "cd '$target_dir/frontend' && npm install"
  fi
}

install_prod_build() {
  local target_dir="$1"
  log "Building frontend in $target_dir/frontend"
  run_as_user bash -lc "cd '$target_dir/frontend' && npm run build"
}

install_if_missing() {
  local src="$1"
  local dest="$2"
  local mode="$3"
  if [ -e "$dest" ]; then
    printf 'Keeping existing %s\n' "$dest"
  else
    log "Installing $dest from template"
    as_root install -D -m "$mode" "$src" "$dest"
  fi
}

render_systemd_unit() {
  local template="$1"
  local dest="$2"
  log "Rendering $(basename "$dest")"
  sed "s/^User=.*/User=${RUN_USER}/" "$template" | as_root tee "$dest" >/dev/null
  as_root chmod 0644 "$dest"
}

main() {
  require_cmd git
  require_cmd bash

  if ! command -v apt-get >/dev/null 2>&1; then
    printf 'This bootstrap script currently supports apt-based Debian/Ubuntu VPSes.\n' >&2
    exit 1
  fi

  log "Installing base packages"
  apt_install git rsync tmux nginx certbot python3-certbot-nginx build-essential
  ensure_node

  log "Preparing directories"
  as_root mkdir -p "$STATE_DIR" "$PROD_DIR" "$ENV_DIR"
  run_as_user mkdir -p "$(dirname "$DEV_DIR")"
  as_root chown -R "$RUN_USER:$RUN_USER" "$PROD_DIR" "$STATE_DIR"

  clone_or_update_repo "$DEV_DIR"
  clone_or_update_repo "$PROD_DIR"

  install_repo_deps "$DEV_DIR"
  install_repo_deps "$PROD_DIR"
  install_prod_build "$PROD_DIR"

  install_if_missing "$PROD_DIR/deploy/env/captainlabs-api.env.example" "$ENV_DIR/api.env" 0640
  install_if_missing "$PROD_DIR/deploy/env/captainlabs-frontend.env.example" "$ENV_DIR/frontend.env" 0640

  render_systemd_unit "$PROD_DIR/deploy/systemd/captainlabs-api.service.example" "/etc/systemd/system/captainlabs-api.service"
  render_systemd_unit "$PROD_DIR/deploy/systemd/captainlabs-frontend.service.example" "/etc/systemd/system/captainlabs-frontend.service"

  if [ "$INSTALL_NGINX_CONFIG" = "1" ]; then
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ]; then
      install_if_missing "$PROD_DIR/deploy/nginx/captainlabs.io.conf.example" "/etc/nginx/sites-available/captainlabs.io.conf" 0644
    else
      install_if_missing "$PROD_DIR/deploy/nginx/captainlabs.io.http.conf.example" "/etc/nginx/sites-available/captainlabs.io.conf" 0644
    fi
    if [ ! -L /etc/nginx/sites-enabled/captainlabs.io.conf ]; then
      log "Enabling nginx site"
      as_root ln -s /etc/nginx/sites-available/captainlabs.io.conf /etc/nginx/sites-enabled/captainlabs.io.conf
    fi
    if [ -L /etc/nginx/sites-enabled/default ]; then
      log "Disabling default nginx site"
      as_root rm -f /etc/nginx/sites-enabled/default
    fi
    as_root nginx -t
  fi

  log "Reloading daemon metadata"
  as_root systemctl daemon-reload

  if [ "$AUTO_START" = "1" ]; then
    log "Enabling and starting services"
    as_root systemctl enable --now captainlabs-api.service captainlabs-frontend.service
    as_root systemctl reload nginx
  fi

  cat <<EOF

Bootstrap complete.

Created/updated:
- Dev clone: $DEV_DIR
- Prod clone: $PROD_DIR
- State dir: $STATE_DIR
- Env dir: $ENV_DIR

Next steps:
1. Edit $ENV_DIR/api.env and $ENV_DIR/frontend.env
2. Copy any existing state JSON files into $STATE_DIR
3. Review /etc/nginx/sites-available/captainlabs.io.conf
4. Start services:
   sudo systemctl enable --now captainlabs-api.service captainlabs-frontend.service
   sudo systemctl reload nginx
5. Issue TLS certs after DNS points at this VPS:
   sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN
6. Create a persistent shell session for development:
   tmux new -s captain-dev

Tip: rerun this script safely; it preserves existing env files and updates both git checkouts.
EOF
}

main "$@"
