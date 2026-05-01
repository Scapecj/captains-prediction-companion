# CaptainLabs Deck <-> VPS first-time setup

Goal: let you start on Steam Deck, continue on VPS, and move back without setup drift.

## Assumptions
- Repo on Deck: `$(pwd)` when running commands from repo root
- Repo remote: `https://github.com/captainslab/captains-prediction-companion`
- VPS is Debian/Ubuntu with SSH access
- You want:
  - VPS working tree path: `~/code/captains-prediction-companion`
  - prod clone on VPS: `/srv/captainlabs`
  - persistent state on VPS: `/var/lib/captains`
  - env files on VPS: `/etc/captainlabs`

## One-command first-time setup from Deck
From repo root on the Deck:

```bash
make setup-first-time VPS=youruser@your-vps RUN_USER=youruser DOMAIN=captainlabs.io

# if you want the VPS working tree to be a real git clone instead of an rsynced tree:
make bootstrap-vps VPS=youruser@your-vps RUN_USER=youruser DOMAIN=captainlabs.io
ssh youruser@your-vps 'rm -rf ~/code/captains-prediction-companion && git clone https://github.com/captainslab/captains-prediction-companion ~/code/captains-prediction-companion'
```

Important:
- run this from the repo root on the Deck
- `DECK_PROJECT_DIR` defaults to the current directory for safety
- the bootstrap step does not install the TLS nginx site until certs exist

What it does:
1. rsyncs the current repo from Deck to `~/code/captains-prediction-companion` on the VPS
2. runs `deploy/scripts/bootstrap-vps.sh` on the VPS
3. creates/updates:
   - prod clone: `/srv/captainlabs`
   - state dir: `/var/lib/captains`
   - env dir: `/etc/captainlabs`
4. keeps the rsynced VPS working tree at `~/code/captains-prediction-companion` for resume-anywhere development
5. installs npm dependencies and builds the prod frontend
6. installs systemd units and nginx site config

## Immediately after bootstrap
SSH to the VPS and fill in env files:

```bash
ssh youruser@your-vps
sudoedit /etc/captainlabs/api.env
sudoedit /etc/captainlabs/frontend.env
```

Backend env must include real provider credentials for your Hermes/Gemini setup.

## Copy persistent runtime state to VPS
The sync helpers only move the repo working tree and, if requested, the repo-local `data/` directory.
They do not sync deployed VPS state stored under `/var/lib/captains`.

If you want to preserve repo-local app state from Deck:

```bash
INCLUDE_STATE=1 make sync-up-state VPS=youruser@your-vps
```

For deployed production state, copy specific files into `/var/lib/captains` manually.

Recommended files if they exist:
- `/var/lib/captains/notes.json`
- `/var/lib/captains/pipeline-state.json`
- `/var/lib/captains/pipeline-card-outputs.json`
- `/var/lib/captains/captainlabs-state.json`

## Start production services on VPS
On the VPS:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now captainlabs-api.service captainlabs-frontend.service
sudo nginx -t
sudo systemctl reload nginx
```

Check health:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:3000/
curl -i http://127.0.0.1:3000/api/health
```

## Enable TLS after DNS points at VPS
On the VPS:

```bash
sudo certbot --nginx -d captainlabs.io -d www.captainlabs.io
sudo cp /srv/captainlabs/deploy/nginx/captainlabs.io.conf.example /etc/nginx/sites-available/captainlabs.io.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Day-to-day workflow

### Normal code handoff
If you want git-based handoff on both machines, clone the repo normally on the VPS once:

```bash
ssh youruser@your-vps
mkdir -p ~/code
cd ~/code
rm -rf captains-prediction-companion
git clone https://github.com/captainslab/captains-prediction-companion captains-prediction-companion
```

After that, Deck -> VPS:
```bash
git add -A
git commit -m "wip: continue from deck"
git push origin main
ssh youruser@your-vps "cd ~/code/captains-prediction-companion && git pull --rebase"
```

VPS -> Deck:
```bash
git add -A
git commit -m "wip: continue from vps"
git push origin main
# back on Deck
git pull --rebase
```

### Uncommitted handoff
Deck -> VPS:
```bash
make sync-up VPS=youruser@your-vps
```

VPS -> Deck:
```bash
make sync-down VPS=youruser@your-vps
```

### Including runtime state during handoff
Deck -> VPS:
```bash
make sync-up-state VPS=youruser@your-vps
```

VPS -> Deck:
```bash
make sync-down-state VPS=youruser@your-vps
```

### Persistent terminal continuity
Attach to dev tmux session on VPS:
```bash
make ssh-dev VPS=youruser@your-vps
```

Open a prod shell on VPS:
```bash
make ssh-prod VPS=youruser@your-vps
```

## Recommended habit
- committed work -> git
- unfinished handoff -> rsync helpers / make targets
- long-running dev work -> tmux on VPS
- production state -> `/var/lib/captains`
- production deploy -> `/srv/captainlabs`
- development on VPS -> `~/code/captains-prediction-companion`

## Safety notes
- Do not commit `.env`
- Do not rsync `node_modules` or `.next`
- Avoid editing the same uncommitted files on both machines at once
- If both sides diverged, commit or stash before syncing
