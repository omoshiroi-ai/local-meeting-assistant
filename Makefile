# Local Meeting Assistant
# Apple Silicon only — requires uv, node, brew
#
# First-time setup:
#   make setup
#
# Daily use:
#   make backend      (terminal 1)
#   make frontend     (terminal 2)
#
# Maintenance:
#   make sync-db      sync ChromaDB with SQLite sessions
#   make check        report model cache and index status

.PHONY: help setup install install-py install-frontend models sync-db check \
        backend frontend dev test lint clean \
        uv-sync uv-add uv-remove uv-lock uv-tree

# ── Defaults ──────────────────────────────────────────────────────────────────

PYTHON   := uv run python
NPM      := npm
FRONTEND := frontend

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Local Meeting Assistant"
	@echo ""
	@echo "  First-time setup"
	@echo "    make setup           Install everything and download all models"
	@echo ""
	@echo "  Running (open two terminals)"
	@echo "    make backend         Start FastAPI + mlx-lm (port 8765)"
	@echo "    make frontend        Start Next.js dev server (port 3000)"
	@echo "    make dev             Start both in one terminal (requires tmux)"
	@echo ""
	@echo "  Maintenance"
	@echo "    make sync-db         Sync ChromaDB with all completed sessions"
	@echo "    make check           Report model cache and index status"
	@echo "    make reindex         Wipe and rebuild ChromaDB from scratch"
	@echo ""
	@echo "  Development"
	@echo "    make test            Run backend tests"
	@echo "    make lint            Run ruff linter"
	@echo "    make clean           Remove generated data (meetings.db, chromadb, uploads)"
	@echo ""
	@echo "  UV Package Management"
	@echo "    make uv-sync         Sync dependencies from lockfile"
	@echo "    make uv-add pkg=X    Add a dependency"
	@echo "    make uv-remove pkg=X Remove a dependency"
	@echo "    make uv-lock         Regenerate uv.lock"
	@echo "    make uv-tree         Show dependency tree"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────

## Full first-time setup: system deps → python deps → frontend deps → models → sync vector db
setup: install models sync-db
	@echo ""
	@echo "  ✓ Setup complete."
	@echo ""
	@echo "  Next:"
	@echo "    Terminal 1:  make backend"
	@echo "    Terminal 2:  make frontend"
	@echo ""

## Install all dependencies (Python + frontend)
install: install-py install-frontend

install-py:
	@echo "==> Installing Python dependencies…"
	uv sync

install-frontend:
	@echo "==> Installing frontend dependencies…"
	cd $(FRONTEND) && $(NPM) install

## Download and warm up Whisper + embedding models
models:
	@echo "==> Downloading models…"
	$(PYTHON) scripts/setup_models.py

## Check model cache status without downloading
check:
	@echo "==> Model cache status:"
	$(PYTHON) scripts/setup_models.py --check-only
	@echo ""
	@echo "==> ChromaDB index status:"
	$(PYTHON) scripts/reindex.py --check

# ── Running ───────────────────────────────────────────────────────────────────

## Start the FastAPI backend (also starts mlx-lm subprocess on :8080)
backend:
	$(PYTHON) -m backend.main

## Start the Next.js frontend dev server
frontend:
	cd $(FRONTEND) && $(NPM) run dev

## Start both backend and frontend in split tmux panes
dev:
	@command -v tmux >/dev/null 2>&1 || { echo "tmux is required for 'make dev'. Install with: brew install tmux"; exit 1; }
	tmux new-session -d -s meeting-assistant -x 220 -y 50 \
	  "$(PYTHON) -m backend.main; read" \; \
	  split-window -h \
	  "cd $(FRONTEND) && $(NPM) run dev; read" \; \
	  attach

# ── Maintenance ───────────────────────────────────────────────────────────────

## Sync ChromaDB — index any sessions not yet in the vector store
sync-db:
	$(PYTHON) scripts/reindex.py

## Wipe ChromaDB and reindex all sessions from scratch
reindex:
	$(PYTHON) scripts/reindex.py --reset

# ── Development ───────────────────────────────────────────────────────────────

test:
	uv run pytest

lint:
	uv run ruff check backend scripts tests

# ── UV Package Management ────────────────────────────────────────────────────

## Sync dependencies from lockfile
uv-sync:
	uv sync

## Add a dependency: make uv-add pkg=httpx
uv-add:
	uv add $(pkg)

## Remove a dependency: make uv-remove pkg=httpx
uv-remove:
	uv remove $(pkg)

## Regenerate uv.lock
uv-lock:
	uv lock

## Show dependency tree
uv-tree:
	uv tree

## Remove generated data directories (keeps models in HF cache)
clean:
	@echo "This will delete data/meetings.db, data/chromadb/, and data/uploads/."
	@read -p "Are you sure? [y/N] " ans && [ "$$ans" = "y" ] || exit 0
	rm -rf data/meetings.db data/chromadb data/uploads
	@echo "Cleaned."
