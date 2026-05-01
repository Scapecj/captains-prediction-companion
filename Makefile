# CaptainLabs Deck <-> VPS workflow shortcuts
# Usage examples:
#   make setup-first-time VPS=deploy@your-vps
#   make sync-up VPS=deploy@your-vps
#   make sync-down VPS=deploy@your-vps
#   make sync-up-state VPS=deploy@your-vps
#   make ssh-dev VPS=deploy@your-vps

VPS ?=
DECK_PROJECT_DIR ?= $(CURDIR)
VPS_PROJECT_DIR ?= ~/code/captains-prediction-companion
RUN_USER ?= $(shell id -un)
DOMAIN ?= captainlabs.io
AUTO_START ?= 0
INSTALL_NGINX_CONFIG ?= 1
INCLUDE_STATE ?= 0

.PHONY: help setup-first-time bootstrap-vps sync-up sync-down sync-up-state sync-down-state ssh-dev ssh-prod tmux-dev tmux-prod

help:
	@printf 'Targets:\n'
	@printf '  make setup-first-time VPS=user@host   # sync repo to VPS and run bootstrap\n'
	@printf '  make bootstrap-vps VPS=user@host      # run bootstrap on VPS only\n'
	@printf '  make sync-up VPS=user@host            # deck -> vps code sync\n'
	@printf '  make sync-down VPS=user@host          # vps -> deck code sync\n'
	@printf '  make sync-up-state VPS=user@host      # deck -> vps sync including data/\n'
	@printf '  make sync-down-state VPS=user@host    # vps -> deck sync including data/\n'
	@printf '  make ssh-dev VPS=user@host            # attach/create captain-dev tmux session\n'
	@printf '  make ssh-prod VPS=user@host           # ssh into VPS prod shell\n'

setup-first-time:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	bash deploy/scripts/deck-to-vps.sh "$(VPS)" "$(CURDIR)" "$(VPS_PROJECT_DIR)"
	ssh "$(VPS)" "cd $(VPS_PROJECT_DIR) && chmod +x deploy/scripts/bootstrap-vps.sh && RUN_USER=$(RUN_USER) DOMAIN=$(DOMAIN) AUTO_START=$(AUTO_START) INSTALL_NGINX_CONFIG=$(INSTALL_NGINX_CONFIG) bash deploy/scripts/bootstrap-vps.sh"

bootstrap-vps:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	ssh "$(VPS)" "cd $(VPS_PROJECT_DIR) && chmod +x deploy/scripts/bootstrap-vps.sh && RUN_USER=$(RUN_USER) DOMAIN=$(DOMAIN) AUTO_START=$(AUTO_START) INSTALL_NGINX_CONFIG=$(INSTALL_NGINX_CONFIG) bash deploy/scripts/bootstrap-vps.sh"

sync-up:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	bash deploy/scripts/deck-to-vps.sh "$(VPS)" "$(DECK_PROJECT_DIR)" "$(VPS_PROJECT_DIR)"

sync-down:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	bash deploy/scripts/vps-to-deck.sh "$(VPS)" "$(VPS_PROJECT_DIR)" "$(DECK_PROJECT_DIR)"

sync-up-state:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	INCLUDE_STATE=1 bash deploy/scripts/deck-to-vps.sh "$(VPS)" "$(DECK_PROJECT_DIR)" "$(VPS_PROJECT_DIR)"

sync-down-state:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	INCLUDE_STATE=1 bash deploy/scripts/vps-to-deck.sh "$(VPS)" "$(VPS_PROJECT_DIR)" "$(DECK_PROJECT_DIR)"

ssh-dev:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	ssh -t "$(VPS)" "tmux attach -t captain-dev || tmux new -s captain-dev"

ssh-prod:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	ssh -t "$(VPS)" "cd /srv/captainlabs && exec \$$SHELL -l"

tmux-dev:
	@tmux attach -t captain-local-dev || tmux new -s captain-local-dev

tmux-prod:
	@test -n "$(VPS)" || (echo 'Set VPS=user@host' >&2; exit 1)
	ssh -t "$(VPS)" "tmux attach -t captain-prod || tmux new -s captain-prod"
