# Code Quality & Formatting Setup

This project uses modern Python code quality tools for consistent formatting and linting.

## Tools Used

- **[Ruff](https://docs.astral.sh/ruff/)** - Fast Python linter and formatter (replaces flake8, black, isort)
- **[MyPy](https://mypy.readthedocs.io/)** - Static type checking
- **[Pre-commit](https://pre-commit.com/)** - Git hooks for automated checks

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or use make
   make install-dev
   ```

2. **Install pre-commit hooks (recommended):**
   ```bash
   pre-commit install
   # or use make
   make pre-commit-install
   ```

3. **Run all checks:**
   ```bash
   make check
   ```

## Available Commands

### Using Make (Recommended)
```bash
make format        # Format code with ruff
make lint          # Check linting issues
make lint-fix      # Fix auto-fixable linting issues
make type-check    # Run type checking
make check         # Run all checks (format + lint + type check)
make clean         # Clean cache files
```

### Direct Commands
```bash
ruff format .      # Format all Python files
ruff check .       # Lint all Python files
ruff check --fix . # Fix auto-fixable issues
mypy .             # Type check all Python files
```

### VS Code Integration

If you're using VS Code, the workspace is configured to:
- Use ruff for formatting and linting
- Format on save
- Show linting errors inline
- Auto-organize imports

**Available VS Code Tasks:**
- `Ctrl+Shift+P` → "Tasks: Run Task" → Choose from:
  - Format Code
  - Lint Code
  - Lint and Fix
  - Type Check
  - Format, Lint & Type Check (default build task)

## Pre-commit Hooks

When you install pre-commit hooks, every git commit will automatically:
1. Format your code with ruff
2. Fix auto-fixable linting issues
3. Check for common issues (trailing whitespace, large files, etc.)
4. Run type checking with mypy

To skip hooks (not recommended): `git commit --no-verify`

## Configuration

- **Ruff & MyPy config:** [`pyproject.toml`](pyproject.toml)
- **Pre-commit config:** [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
- **VS Code config:** [`.vscode/settings.json`](.vscode/settings.json)

## What Gets Checked

### Ruff Linting Rules
- Pyflakes (F) - Unused imports, undefined names
- pycodestyle (E4, E7, E9) - Style errors
- isort (I) - Import sorting
- pyupgrade (UP) - Modern Python syntax
- flake8-bugbear (B) - Common bug patterns
- flake8-simplify (SIM) - Code simplification
- Plus other helpful rules

### MyPy Type Checking
- Currently configured to be less strict with existing code
- Gradually can be made stricter as types are added
- Ignores missing imports for third-party libraries

## Troubleshooting

**"Command not found" errors:**
- Make sure you've installed the dependencies: `pip install -r requirements.txt`
- Activate your virtual environment if using one

**VS Code not showing linting:**
- Install the Ruff extension: `charliermarsh.ruff`
- Check that your Python interpreter points to the right environment

**Pre-commit hooks failing:**
- Run `pre-commit run --all-files` to see what's failing
- Fix the issues and try committing again
- Or run `make check` to fix issues manually first
