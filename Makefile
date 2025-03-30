.PHONY: help env init run test clean lint format db-migrate db-upgrade db-downgrade test-data

# Default target when just running 'make'
.DEFAULT_GOAL := help

# Python and virtualenv settings
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
FLASK = $(VENV)/bin/flask

# Environment variables for Flask
export FLASK_APP = app
export FLASK_ENV = development
export PYTHONPATH = $(shell pwd)
PORT ?= 5001  # Default port, can be overridden with make run PORT=xxxx

help:
	@echo "Available commands:"
	@echo "  make help         - Show this help message"
	@echo "  make env         - Create and activate Python virtual environment"
	@echo "  make init        - Initialize the application (create venv, install deps, init db)"
	@echo "  make run         - Run the Flask application in development mode"
	@echo "  make test        - Run all tests with pytest"
	@echo "  make clean       - Remove all build, test, and coverage artifacts"
	@echo "  make lint        - Check code style with flake8"
	@echo "  make format      - Format code with black"
	@echo "  make db-migrate  - Generate a new database migration"
	@echo "  make db-upgrade  - Apply all database migrations"
	@echo "  make db-downgrade- Revert last database migration"
	@echo "  make test-data   - Load sample data into the database"

env:
	@echo "Creating virtual environment..."
	python -m venv $(VENV)
	@echo "Installing pip-tools..."
	$(PIP) install pip-tools
	@echo "Virtual environment created. Activate it with: source venv/bin/activate"

init: env
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "Initializing database..."
	@if [ ! -d "migrations" ]; then \
		. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db init; \
	fi
	@if [ -d "migrations" ]; then \
		. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db migrate -m "Initial migration"; \
		. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db upgrade; \
	fi
	@echo "Creating database tables..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(PYTHON) scripts/init_db.py
	@echo "Initialization complete."

run: env
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "Starting Flask development server on port $(PORT)..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) run --debug -p $(PORT)

test: init
	@echo "Running tests..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(PYTHON) -m pytest -v
	@echo "Backend tests complete."
	. $(VENV)/bin/activate && PYTHONPATH=$PYTHONPATH:. pytest tests/test_frontend.py -v
	@echo "Front end tests complete"
	. $(VENV)/bin/activate && PYTHONPATH=$PYTHONPATH:. pytest tests/test_admin.py -v
	@echo "Admin operation tests complete"

clean:
	@echo "Cleaning project..."
	rm -rf $(VENV)
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -f app/flightschool.db
	rm -rf instance
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

lint:
	@echo "Installing linting dependencies..."
	$(PIP) install flake8
	@echo "Running flake8..."
	. $(VENV)/bin/activate && $(PYTHON) -m flake8 app tests

format:
	@echo "Installing formatting dependencies..."
	$(PIP) install black
	@echo "Formatting code with black..."
	. $(VENV)/bin/activate && $(PYTHON) -m black app tests

db-migrate:
	@echo "Creating database migration..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db migrate -m "$(msg)"
	@echo "Migration created. Review migration files and run 'make db-upgrade' to apply."

db-upgrade:
	@echo "Applying database migrations..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db upgrade
	@echo "Database upgraded."

db-downgrade:
	@echo "Reverting last database migration..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(FLASK) db downgrade
	@echo "Database downgraded."

test-data: init
	@echo "Loading test data..."
	. $(VENV)/bin/activate && PYTHONPATH=$(shell pwd) $(PYTHON) scripts/load_test_data.py
	@echo "Test data loaded successfully."

# Error if running on Windows
ifeq ($(OS),Windows_NT)
$(error This Makefile is not supported on Windows. Please use WSL or Git Bash)
endif
