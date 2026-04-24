# 07 - Configuration Simplification: Removing account_mapping

## Overview

This document describes the refactoring that eliminated the redundant `account_mapping` section from `accounts.yaml` and updated all Python scripts to use only `account_configs` for account ID ↔ name mapping.

## Problem Statement

The original configuration structure had redundant information:

```yaml
# OLD STRUCTURE (redundant)
account_mapping:
  '123456789012': example-production
  '234567890123': example-staging
  '345678901234': example-development

account_configs:
  '123456789012':
    name: example-production  # Duplicate information!
    services: [...]
  '234567890123':
    name: example-staging       # Duplicate information!
    services: [...]
```

**Issues:**
- **Data Duplication**: Account names stored in two places
- **Maintenance Overhead**: Need to keep both sections synchronized
- **Error Prone**: Risk of inconsistencies between mapping and configs
- **Complexity**: More complex code patterns needed for lookups

## Solution

Simplified to single source of truth using only `account_configs`:

```yaml
# NEW STRUCTURE (single source of truth)
account_configs:
  '123456789012':
    name: example-production
  '234567890123':
    name: example-staging
    services:
    - cloudwatch
    - config
    # ... other services
  '345678901234':
    name: example-development
    services:
    - ce
    - cloudfront
    # ... other services
```

## Implementation Changes

### 1. Helper Functions Added (aws_utils.py)

```python
def get_account_name_by_id(account_configs, account_id):
    """Get account name from account ID using account_configs"""
    if account_id in account_configs:
        return account_configs[account_id].get('name')
    return None

def get_account_id_by_name(account_configs, account_name):
    """Get account ID from account name using account_configs"""
    for account_id, config in account_configs.items():
        if config.get('name') == account_name:
            return account_id
    return None
```

### 2. Core Function Updates

**Before:**
```python
def determine_account_name(account_info, provided_account, account_id_to_name):
    # Used account_mapping dict directly
    if account_id in account_id_to_name:
        return account_id_to_name[account_id]
```

**After:**
```python
def determine_account_name(account_info, provided_account, account_configs):
    # Uses helper function with account_configs
    account_name = get_account_name_by_id(account_configs, account_id)
    if account_name:
        return account_name
```

### 3. Module Updates

**modules/billing.py:**
```python
# OLD
ACCOUNT_ID_TO_NAME = accounts_config['account_mapping']
account_name = ACCOUNT_ID_TO_NAME[account_id]

# NEW
ACCOUNT_CONFIGS = accounts_config['account_configs']
account_name = aws_utils.get_account_name_by_id(ACCOUNT_CONFIGS, account_id)
```

**modules/infra.py:**
```python
# OLD
ACCOUNT_ID_TO_NAME = accounts_config['account_mapping']
account_name = aws_utils.determine_account_name(info, args.account, ACCOUNT_ID_TO_NAME)

# NEW
ACCOUNT_CONFIGS = accounts_config['account_configs']
account_name = aws_utils.determine_account_name(info, args.account, ACCOUNT_CONFIGS)
```

### 4. Configuration Management

**config_manager.py:**
```python
# OLD - add_account() method
config['account_mapping'][account_id] = name  # Redundant
config['account_configs'][account_id] = {
    'name': name,
    'services': services
}

# NEW - add_account() method
config['account_configs'][account_id] = {
    'name': name,
    'services': services
}
```

## Files Modified

### Python Scripts
- **aws_utils.py** - Added helper functions, updated core lookup functions
- **modules/billing.py** - Removed ACCOUNT_ID_TO_NAME usage
- **modules/infra.py** - Updated to use account_configs only
- **billing_analyzer.py** - Updated account lookup methods
- **config_manager.py** - Removed account_mapping from add operations

### Configuration Files
- **configs/accounts.yaml** - Removed account_mapping section
- **configs/accounts.yaml.example** - Removed account_mapping section

## Pattern Comparison

| Operation | Old Pattern | New Pattern |
|-----------|-------------|-------------|
| ID → Name | `account_mapping[id]` | `aws_utils.get_account_name_by_id(configs, id)` |
| Name → ID | Loop through mapping | `aws_utils.get_account_id_by_name(configs, name)` |
| Add Account | Update both sections | Update account_configs only |
| Validation | Check both sections exist | Check account_configs only |

## Benefits Achieved

### ✅ Simplified Configuration
- **Single Source of Truth**: Account names stored only in `account_configs[id]['name']`
- **Cleaner YAML**: No redundant account_mapping section
- **Easier Maintenance**: Only one place to update account information

### ✅ Better Code Quality
- **Consistent API**: All scripts use same helper functions
- **Reduced Complexity**: Simpler lookup patterns
- **Error Prevention**: No risk of mapping/config inconsistencies

### ✅ Enhanced Maintainability
- **Centralized Logic**: All account operations in aws_utils.py
- **Type Safety**: Better error handling in helper functions
- **Future-Proof**: Easier to extend account configuration structure

## Verification Results

All functionality verified after refactoring:
- ✅ Python syntax validation - no import errors
- ✅ Configuration loading with simplified YAML structure
- ✅ Helper functions work correctly for all lookups
- ✅ All scripts (aws.py, billing modules) function normally
- ✅ Account addition/lookup operations work correctly

## Migration Notes

**For Future Updates:**
1. **New Accounts**: Add only to `account_configs` section with `name` field
2. **Account Lookup**: Always use helper functions from aws_utils.py
3. **Configuration**: No need to maintain separate account_mapping
4. **Validation**: Only validate account_configs section exists

**Backward Compatibility:**
- All existing functionality preserved
- Same command-line interfaces maintained
- No changes to user-facing behavior
- Configuration automatically uses new structure

## Example Usage

### Adding New Account
```bash
# Billing analyzer auto-detection will use new helper functions
./billing_analyzer.py --auto-update --dry-run

# Manually adding via config_manager uses simplified structure
python3 -c "
from config_manager import ConfigManager
cm = ConfigManager()
cm.add_account('123456789', 'new-account-name', ['s3', 'ec2'])
"
```

### Account Lookup
```python
# In any script
import aws_utils

config = aws_utils.load_config()
account_configs = config['account_configs']

# ID to name
name = aws_utils.get_account_name_by_id(account_configs, '123456789012')

# Name to ID
account_id = aws_utils.get_account_id_by_name(account_configs, 'example-production')
```

This refactoring establishes a cleaner, more maintainable configuration structure while preserving all existing AWS automation functionality.
