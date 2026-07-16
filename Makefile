# Graphite — Intelligent Network Copilot
# Makefile for a two-terminal local development workflow:
#   Terminal 1: make lab   (backend)
#   Terminal 2: make ui    (frontend)

.PHONY: help install env lab ui test clean

VENV ?= backend/.venv
PYTHON := $(CURDIR)/$(VENV)/bin/python
PIP := $(CURDIR)/$(VENV)/bin/pip

BACKEND_DIR := backend
FRONTEND_DIR := frontend

help:
	@echo "Graphite — Intelligent Network Copilot"
	@echo ""
	@echo "Two-terminal workflow:"
	@echo "  Terminal 1: make lab   Start the backend digital twin (http://localhost:8000)"
	@echo "  Terminal 2: make ui    Start the operator console (http://localhost:3000)"
	@echo ""
	@echo "  make install    Create backend venv, install Python deps, and npm install frontend"
	@echo "  make env        Copy backend/.env.example and create frontend/.env.local"
	@echo "  make test       Run the backend pytest suite"
	@echo "  make clean      Remove backend venv and frontend node_modules/.next"

install:
	@echo "==> Creating Python virtual environment..."
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	$(PIP) install -e $(BACKEND_DIR)/
	@echo "==> Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install

env:
	@test -f $(BACKEND_DIR)/.env \
		|| (cp $(BACKEND_DIR)/.env.example $(BACKEND_DIR)/.env \
			&& echo "Created $(BACKEND_DIR)/.env — add your GEMINI_API_KEY to enable the agent.")
	@test -f $(FRONTEND_DIR)/.env.local \
		|| (echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > $(FRONTEND_DIR)/.env.local \
			&& echo "Created $(FRONTEND_DIR)/.env.local")

lab:
	@echo "==> Starting Graphite backend (Ctrl+C to stop)..."
	cd $(BACKEND_DIR) && $(PYTHON) -m graphite.api

ui:
	@echo "==> Starting Graphite frontend (Ctrl+C to stop)..."
	cd $(FRONTEND_DIR) && npm run dev

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q

clean:
	rm -rf $(VENV)
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/.next
