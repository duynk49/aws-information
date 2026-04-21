# AWS Scripts Code Refactoring Documentation

## Overview

This document describes the major refactoring performed to eliminate code duplication between `aws.py` and `billing.py` by extracting common functionality into a shared utilities module `aws_utils.py`.

## Problem Statement

The original `aws.py` and `billing.py` scripts contained significant duplicate code (~150 lines) including:
- AWS authentication logic
- Configuration loading from YAML files  
- Account information handling
- Argument parsing setup
- File/directory management

This duplication made maintenance difficult and increased the risk of inconsistencies between scripts.

## Solution: aws_utils.py Module

Created a centralized utilities module that provides common functions for all AWS automation scripts.

### Core Functions

#### Configuration Management
```python
load_config(include_commands=False)
```
- Loads accounts.yaml configuration
- Optionally loads commands.yaml for resource collection scripts
- Returns parsed configuration dictionaries

#### Authentication & Credentials
```python
handle_aws_authentication(skip_login=False)
check_aws_credentials()  
aws_login()
get_account_info()
```
- Unified AWS authentication workflow
- Credential validation with detailed account info
- Consistent error handling and user feedback

#### Account Management
```python
determine_account_name(account_info, provided_account, account_id_to_name)
find_account_config(account_arg, account_configs, account_id_to_name)
display_account_info(account_info)
```
- Account name resolution (ID ↔ name mapping)
- Configuration lookup by name or ID
- Formatted account information display

#### Argument Parsing
```python
setup_common_parser(account_required=False, account_help=None)
```
- Flexible argument parser for different script requirements
- Common arguments: `--account`, `--skip-login`, `--output`
- Customizable account requirement and help text

#### File Operations
```python
create_output_directory(date_folder=None)
get_output_filename(account_name, output_arg=None, file_extension=".json")
```
- Standardized output directory creation
- Consistent filename generation

## Integration Examples

### aws.py Integration
```python
import aws_utils

# Parse arguments (account optional)
common_parser = aws_utils.setup_common_parser(account_required=False)
parser = argparse.ArgumentParser(
    description="Collect AWS resources and save to JSON file",
    parents=[common_parser]
)

# Load configuration with commands
accounts_config, commands_config = aws_utils.load_config(include_commands=True)

# Handle authentication
account_info = aws_utils.handle_aws_authentication(skip_login=args.skip_login)

# Determine account name with auto-detection
account_name = aws_utils.determine_account_name(account_info, args.account, ACCOUNT_ID_TO_NAME)
```

### billing.py Integration
```python
import aws_utils

# Parse arguments (account required)
common_parser = aws_utils.setup_common_parser(account_required=True)
parser = argparse.ArgumentParser(
    description='Collect AWS billing data and save to JSON file',
    parents=[common_parser]
)

# Load configuration (no commands needed)
accounts_config = aws_utils.load_config(include_commands=False)

# Find account configuration
account_found, account_config, found_account_id = aws_utils.find_account_config(
    args.account, ACCOUNT_CONFIGS, ACCOUNT_ID_TO_NAME
)
```

## Benefits Achieved

### Code Quality
- **~150 lines of duplicate code eliminated**
- **Single source of truth** for common operations
- **Consistent error handling** across all scripts
- **Better maintainability** - changes in one place

### User Experience
- **Consistent CLI interface** across all AWS scripts
- **Uniform authentication flow** 
- **Standardized error messages** and help text
- **Predictable file naming** and directory structure

### Developer Experience
- **Easier to add new AWS scripts** using established patterns
- **Reduced testing surface** - common functions tested once
- **Clear separation of concerns** between utilities and business logic
- **Better documentation** through centralized function definitions

## Usage Patterns

### Creating New AWS Scripts
1. Import `aws_utils`
2. Use `setup_common_parser()` for argument parsing
3. Call `load_config()` for YAML configuration
4. Use `handle_aws_authentication()` for login workflow
5. Leverage account management functions as needed

### Example New Script Template
```python
#!/usr/bin/env python3
import argparse
import aws_utils

# Parse arguments
common_parser = aws_utils.setup_common_parser(account_required=True)
parser = argparse.ArgumentParser(
    description="New AWS automation script",
    parents=[common_parser]
)
# Add script-specific arguments here
args = parser.parse_args()

# Load configuration
accounts_config = aws_utils.load_config()
ACCOUNT_CONFIGS = accounts_config['account_configs']
ACCOUNT_ID_TO_NAME = accounts_config['account_mapping']

# Handle authentication
account_info = aws_utils.handle_aws_authentication(skip_login=args.skip_login)
if not account_info:
    sys.exit(1)

# Your script logic here...
```

## Testing

All refactored functionality maintains backward compatibility:

```bash
# aws.py - works with and without account specification
./aws.py --skip-login                    # Auto-detects account
./aws.py --account demo-company-prod   # Explicit account

# billing.py - requires account specification  
./billing.py --account demo-company-prod --skip-login
./billing.py --account 1234567890 --month 2026-04
```

## Future Enhancements

### Potential Additions to aws_utils.py
- **Region management** functions for multi-region operations
- **Profile management** for AWS CLI profile handling  
- **Resource tagging** utilities for consistent resource labeling
- **Pagination helpers** for large AWS API responses
- **Retry logic** with exponential backoff for API calls
- **Logging configuration** for structured logging across scripts

### Script Organization
- Consider creating submodules for specific AWS services
- Add configuration validation functions
- Implement script discovery/registry for available automation tools

## Migration Notes

### Breaking Changes
- **None** - All existing command-line interfaces remain unchanged
- **None** - All output formats and file locations preserved

### Internal Changes
- Functions moved from individual scripts to `aws_utils.py`
- Import statements added to both scripts
- No changes to business logic or AWS API interactions

This refactoring establishes a solid foundation for AWS automation script development while maintaining full backward compatibility.