# AWS Automation Project Guidelines

## Code Style

**Python Standards**
- Follow PEP 8 via ruff formatting (88 character line length)
- Use type hints for all function parameters and return values
- Use double quotes for strings consistently
- Prefer f-strings for string formatting over `.format()` or `%`

**Key Reference Files**
- `aws.py` - Main CLI structure and argument parsing patterns
- `aws_utils.py` - Shared utilities and error handling patterns
- `modules/config.py` - YAML configuration management patterns

## Architecture

**Modular Design Principles**
- Separate concerns into `modules/` directory (billing, config, infra)
- Each module provides `run_*()` function that returns standardized result dict
- Common utilities in `aws_utils.py` for authentication, account detection
- Configuration centralized in `configs/accounts.yaml` using YAML format

**CLI Structure**
- Main script `aws.py` with subcommands: `infra`, `billing`, `config`
- Use argparse with subparsers for nested command structure
- Common arguments handled via `aws_utils.setup_common_parser()`
- Configuration commands have nested subparsers for management operations

**Data Storage**
- All output files in `storages/aws/` directory
- Filename format: `{type}_{YYYY-MM}_{account-name}_{account-id}.json`
- JSON format for structured data with metadata and execution details

## Build and Test

**Setup Commands**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

**Quality Commands**
```bash
ruff format .           # Format code
ruff check .           # Lint code
ruff check --fix .     # Auto-fix issues
mypy .                 # Type checking
```

**VS Code Tasks Available**
- "Format, Lint & Type Check" - Complete quality pipeline
- Individual tasks for format, lint, type checking

## Conventions

**AWS Integration Patterns**
- Always use AWS SSO authentication via `aws_utils.handle_aws_authentication()`
- Account detection and validation before operations
- Service mapping between AWS billing names and CLI service names
- Cost threshold filtering ($0.01 default) for billing analysis

**Configuration Management**
- YAML-first configuration in `configs/accounts.yaml`
- Account mapping by ID to friendly names
- Service definitions with AWS CLI commands
- Use `ConfigManager` class for all YAML operations

**Error Handling**
- Return standardized result dictionaries: `{"success": bool, "error": str, ...}`
- Use try/except with informative error messages
- Display account information before operations
- Graceful handling of missing AWS permissions

**File Naming & Organization**
- Snake_case for Python files and variables
- Kebab-case for account names in config (normalize to underscore for file operations)
- Descriptive filenames with timestamps
- JSON files for data, YAML for configuration

**CLI UX Patterns**
- Emoji prefixes for status messages (🎉, ❌, 📄, 📊)
- Progress indicators for long operations
- Dry-run modes for destructive operations
- Comprehensive help text with examples

**AWS Service Handling**
- Map billing service names to CLI services via `service_mapping` dict
- Filter out non-service billing categories (Tax, Credits, etc.)
- Generate AWS CLI commands for discovered services
- Handle regional vs global services appropriately

**Testing & Quality**
- Type hints required for all functions
- Pre-commit hooks enforce code quality
- Modular architecture enables unit testing
- Configuration validation before operations

**Documentation Standards**
- Docstrings for all public functions
- README.md for user documentation
- `docs/` directory for detailed implementation guides
- Inline comments for complex AWS service mappings
