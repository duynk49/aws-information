# Storage Organization

This document describes the storage organization system for AWS automation JSON outputs.

## Overview

All JSON output files are now organized under a centralized `storages/` folder with two main categories:

```
storages/
├── billings/          # AWS billing and cost data
│   ├── 2026-01/
│   ├── 2026-02/
│   ├── 2026-03/
│   └── 2026-04/
└── infrastructures/   # AWS resource inventory data
    ├── 2026-04-15/
    ├── 2026-04-16/
    ├── 2026-04-17/
    └── 2026-04-20/
```

## Storage Categories

### Billings (`storages/billings/`)

Contains AWS Cost Explorer billing data collected by [`billing.py`](../billing.py).

- **Folder Structure**: `storages/billings/{YYYY-MM}/`
- **File Naming**: `{account-name}.json` 
- **Content**: Monthly billing reports including cost breakdowns by service, region, usage type, etc.
- **Example**: `storages/billings/2026-04/demo-company-prod.json`

### Infrastructures (`storages/infrastructures/`)

Contains AWS resource inventory data collected by [`aws.py`](../aws.py).

- **Folder Structure**: `storages/infrastructures/{YYYY-MM-DD}/`
- **File Naming**: `{account-name}.json`
- **Content**: Detailed AWS resource inventories across all configured services
- **Example**: `storages/infrastructures/2026-04-20/demo-company-prod.json`

## Scripts and Storage Usage

### billing.py

- **Writes to**: `storages/billings/{YYYY-MM}/`
- **Folder Creation**: Automatically creates month-based subfolders
- **File Output**: One JSON file per account per month

```bash
# Example output location
./billing.py --account demo-company-prod --month 2026-04
# → storages/billings/2026-04/demo-company-prod.json
```

### aws.py

- **Writes to**: `storages/infrastructures/{YYYY-MM-DD}/`
- **Folder Creation**: Automatically creates daily subfolders
- **File Output**: One JSON file per account per day

```bash
# Example output location
./aws.py --account demo-company-prod
# → storages/infrastructures/2026-04-20/demo-company-prod.json
```

### billing_analyzer.py

- **Reads from**: `storages/billings/`
- **Analysis**: Processes billing JSON files to analyze service usage
- **Auto-Discovery**: Automatically finds billing files in the storage structure

```bash
# Example - analyzes files from storages/billings/
./billing_analyzer.py --account demo-company-prod --auto-update
```

## Migration from Previous Structure

### Old Structure (Before Reorganization)
```
billings/2026-03/demo-company-prod.json    # Billing data
billings/2026-04/demo-company-prod.json    # Billing data
2026-04-17/demo-company-prod.json          # Infrastructure data
2026-04-20/demo-company-prod.json          # Infrastructure data
```

### New Structure (After Reorganization)
```
storages/
  billings/
    2026-03/demo-company-prod.json         # Billing data
    2026-04/demo-company-prod.json         # Billing data
  infrastructures/
    2026-04-17/demo-company-prod.json      # Infrastructure data
    2026-04-20/demo-company-prod.json      # Infrastructure data
```

## Benefits

1. **Centralized Organization**: All AWS data outputs in one place
2. **Clear Categorization**: Separate billing vs infrastructure data
3. **Consistent Structure**: Uniform folder patterns across scripts
4. **Better Scalability**: Easy to add new data categories in the future
5. **Improved Navigation**: Logical hierarchy for finding specific data

## File Naming Conventions

- **Account Names**: Use configured account names from `configs/accounts.yaml`
- **File Extension**: Always `.json`
- **Date Formats**: 
  - Billing: `YYYY-MM` (monthly)
  - Infrastructure: `YYYY-MM-DD` (daily)

## Implementation Details

All scripts use the shared utilities in [`aws_utils.py`](../aws_utils.py):

- `create_output_directory(storage_type="infrastructures")`: Creates infrastructure storage paths
- `get_output_filename(account_name, output_arg)`: Generates consistent filenames
- Storage type parameter distinguishes between `"billings"` and `"infrastructures"`

## Future Enhancements

The storage system is designed to accommodate future data categories:

- `storages/configurations/` - Account and service configurations
- `storages/compliance/` - Compliance and security scan results  
- `storages/optimization/` - Cost and performance optimization reports
- `storages/backups/` - Configuration and data backups

## Maintenance

- Old files in the previous structure can be manually moved to the new organization
- Scripts will automatically create the new folder structure as needed
- No cleanup of old folders is performed automatically - manual removal when ready