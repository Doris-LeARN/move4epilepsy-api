.PHONY: help test test-verbose test-fast test-coverage test-security test-auth test-patients clean format lint

VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PYTEST = $(VENV)/bin/pytest

help:
	@echo "🧪 Move4Epilepsy API - Test Commands"
	@echo "===================================="
	@echo ""
	@echo "Tests:"
	@echo "  make test              - Lancer tous les tests"
	@echo "  make test-verbose      - Tests avec sortie détaillée"
	@echo "  make test-fast         - Tests rapides seulement (pas slow)"
	@echo "  make test-coverage     - Tests + couverture (HTML report)"
	@echo "  make test-security     - Tests de sécurité seulement"
	@echo "  make test-auth         - Tests authentification seulement"
	@echo "  make test-patients     - Tests patients seulement"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format            - Format code (black)"
	@echo "  make lint              - Lint code (flake8, pylint)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             - Nettoyer fichiers temporaires"
	@echo "  make clean-cache       - Nettoyer cache pytest"
	@echo ""

# Tests
test:
	@echo "🧪 Running all tests..."
	$(PYTEST)

test-verbose:
	@echo "🧪 Running tests (verbose)..."
	$(PYTEST) -vv

test-fast:
	@echo "⚡ Running fast tests (skipping slow)..."
	$(PYTEST) -m "not slow" -v

test-coverage:
	@echo "📊 Running tests with coverage..."
	$(PYTEST) --cov=app --cov-report=html --cov-report=term-missing
	@echo "✅ Coverage report generated: htmlcov/index.html"

test-security:
	@echo "🔐 Running security tests..."
	$(PYTEST) tests/core/test_security.py -v

test-auth:
	@echo "🔑 Running auth tests..."
	$(PYTEST) tests/api/test_auth.py -v

test-patients:
	@echo "🏥 Running patients tests..."
	$(PYTEST) tests/api/test_patients.py -v

# Code quality
format:
	@echo "🎨 Formatting code..."
	$(PYTHON) -m black app tests

lint:
	@echo "🔍 Linting code..."
	$(PYTHON) -m flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics || true
	$(PYTHON) -m pylint app tests --disable=all --enable=E,F || true

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "✅ Cleanup done!"

clean-cache:
	@echo "🗑️  Cleaning pytest cache..."
	$(PYTEST) --cache-clear
	@echo "✅ Cache cleared!"

# Development
install-test-deps:
	@echo "📦 Installing test dependencies..."
	$(PIP) install -q pytest pytest-asyncio pytest-cov black flake8 pylint

watch:
	@echo "👀 Watching for changes..."
	$(PYTEST) --looponfail tests/

debug:
	@echo "🐛 Running tests in debug mode (pdb)..."
	$(PYTEST) --pdb

# Combined commands
all: clean format lint test-coverage
	@echo "✅ All checks passed!"

check: lint
	@echo "✅ Code quality check passed!"

quick: test-fast
	@echo "✅ Quick test run completed!"
