# Contributing to pyrbmi

Thank you for your interest in contributing to pyrbmi! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/statparity/pyrbmi.git
   cd pyrbmi
   ```

2. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**:
   ```bash
   uv sync --extra bayes --extra dev
   ```

## Development Workflow

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes**: Write code, tests, and documentation
3. **Run linting**: `uv run ruff check . --fix`
4. **Run type checking**: `uv run mypy src/pyrbmi`
5. **Run tests**: `uv run pytest`
6. **Format code**: `uv run ruff format .`
7. **Commit**: Use conventional commits (e.g., `feat:`, `fix:`, `docs:`)
8. **Push and open a PR**

## Code Standards

- **Python**: ≥3.11
- **Line length**: 100 characters
- **Type hints**: Required for all public APIs
- **Tests**: Required for new features (aim for ≥90% coverage)
- **Docstrings**: Google style

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `style:` — Code style (formatting, no logic change)
- `refactor:` — Code refactoring
- `perf:` — Performance improvement
- `test:` — Tests only
- `chore:` — Build/tooling changes

Example: `feat: add MAR imputation strategy`

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=pyrbmi --cov-report=html

# Run specific test file
uv run pytest tests/test_imputation.py
```

## Release Process

Releases are automated via GitHub Actions when a version tag is pushed:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Questions?

Open an issue or reach out to the maintainers.
