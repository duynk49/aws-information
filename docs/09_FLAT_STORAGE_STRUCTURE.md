# Flat Storage Structure

This document describes the new flat storage organization system for AWS automation JSON outputs.

## Overview

All JSON output files are now organized in a single `storages/aws/` directory with descriptive filenames that include data type, date, account name, and account ID.

```
storages/
└── aws/
    ├── billing_2026-04_demo-company-prod_123456789012.json
    ├── infrastructure_2026-04_demo-company-prod_123456789012.json
    └── logs/
```

## File Naming Convention

All AWS data files follow a consistent naming pattern:

### Billing Files
```
billing_{YYYY-MM}_{account_name}_{account_id}.json
```

**Examples:**
- `billing_2026-04_demo-company-prod_123456789012.json`

### Infrastructure Files
```
infrastructure_{YYYY-MM}_{account_name}_{account_id}.json
```

**Examples:**
- `infrastructure_2026-04_demo-company-prod_123456789012.json`

## Filename Components

1. **Data Type**: `billing` or `infrastructure`
2. **Date**: `YYYY-MM` format (consistent for both billing and infrastructure)
3. **Account Name**: From configuration, with spaces/hyphens converted to underscores
4. **Account ID**: AWS account ID (12-digit number)
5. **Extension**: Always `.json`

## Scripts and Storage Usage

### billing.py

- **Writes to**: `storages/aws/`
- **File Pattern**: `billing_{YYYY-MM}_{account_name}_{account_id}.json`
- **Date Format**: Uses month from `--month` parameter or current month

```bash
# Example output
./billing.py --account demo-company-prod --month 2026-04
# → storages/aws/billing_2026-04_demo-company-prod_123456789012.json
```

### aws.py

- **Writes to**: `storages/aws/`
- **File Pattern**: `infrastructure_{YYYY-MM}_{account_name}_{account_id}.json`
- **Date Format**: Uses current month (YYYY-MM)

```bash
# Example output
./aws.py --account demo-company-prod
# → storages/aws/infrastructure_2026-04_demo-company-prod_123456789012.json
```

### Configuration Management

- **Reads from**: `storages/aws/`
- **Analysis**: Processes billing files matching `billing_*.json` pattern
- **Auto-Discovery**: Parses filenames to extract account and date information

```bash
# Example - analyzes files from storages/aws/
./aws.py config --account demo-company-prod --auto-update
```

## Benefits of Flat Structure

1. **Self-Documenting**: Filenames contain all essential metadata
2. **Easy Browsing**: All files in one location, sorted naturally by name
3. **Quick Identification**: Data type, date, and account visible at a glance
4. **Scalable**: No nested directory structure to manage
5. **Cross-Platform**: No path separator issues across operating systems
6. **Version Control Friendly**: Clear file names in git diffs and logs

## File Discovery and Parsing

### Billing File Discovery
The system automatically discovers billing files by:
1. Scanning `storages/aws/` for files matching `billing_*.json`
2. Parsing filename components: `billing_{month}_{account_name}_{account_id}.json`
3. Filtering by account name and/or month if specified

### Infrastructure File Discovery
Infrastructure files are generated with current month format and can be located by:
1. Scanning for files matching `infrastructure_*.json` pattern
2. Parsing filename to extract account and date information
3. Matching against configured account names/IDs

## Implementation Details

### Core Functions

#### `aws_utils.create_flat_storage_directory()`
- Creates `storages/aws/` directory
- Returns path to created directory
- Replaces the old type-specific directory creation

#### `aws_utils.get_flat_storage_filename(data_type, date_str, account_name, account_id, output_arg=None)`
- Generates descriptive filenames following the new convention
- Handles user-provided output override via `output_arg`
- Sanitizes account names (replaces spaces/hyphens with underscores)

### Legacy Support

The old functions remain available for backward compatibility:
- `create_output_directory()` - Still creates type-specific subdirectories
- `get_output_filename()` - Still generates simple account-based filenames

## Migration from Previous Structure

### Old Structure (Legacy)
```
storages/
├── billings/
│   ├── 2026-03/
│   │   └── demo-company-prod.json
│   └── 2026-04/
│       └── demo-company-prod.json
└── infrastructures/
    ├── 2026-04-17/
    │   └── demo-company-prod.json
    └── 2026-04-20/
        └── demo-company-prod.json
```

### New Structure (Current)
```
storages/
└── aws/
    ├── billing_2026-03_demo-company-prod_123456789012.json
    ├── billing_2026-04_demo-company-prod_123456789012.json
    ├── infrastructure_2026-04_demo-company-prod_123456789012.json
    └── logs/
```

### Migration Process

1. **Automatic Generation**: New files automatically use the flat structure
2. **Coexistence**: Old and new structures can coexist during transition
3. **Gradual Migration**: Move old files to new naming convention as needed
4. **Account ID Resolution**: Use account configuration to map old files to account IDs

### Migration Script Example

```bash
# Example migration commands (manual process)
# From: storages/billings/2026-04/demo-company-prod.json
# To: storages/aws/billing_2026-04_demo-company-prod_123456789012.json

mkdir -p storages/aws
cp storages/billings/2026-04/demo-company-prod.json \
   storages/aws/billing_2026-04_demo-company-prod_123456789012.json
```

## Future Enhancements

The flat storage system can easily accommodate additional data types:

- `compliance_{YYYY-MM}_{account_name}_{account_id}.json` - Compliance scan results
- `optimization_{YYYY-MM}_{account_name}_{account_id}.json` - Cost optimization reports
- `backup_{YYYY-MM-DD}_{account_name}_{account_id}.json` - Configuration backups
- `security_{YYYY-MM}_{account_name}_{account_id}.json` - Security assessments

## Best Practices

1. **Consistent Dating**: Use YYYY-MM format for monthly data, YYYY-MM-DD for daily data
2. **Account Mapping**: Ensure account configurations are up-to-date for proper filename generation
3. **File Naming**: Avoid special characters in account names; use underscores for word separation
4. **Regular Cleanup**: Periodically review and archive old data files as needed
5. **Documentation**: Update this document when adding new data types or changing conventions

## Troubleshooting

### Common Issues

**Missing Account ID in Filename:**
- Check that account is properly configured in `configs/accounts.yaml`
- Verify AWS credentials are valid and account ID is accessible

**Filename Parse Errors:**
- Ensure account names don't contain special characters that could break parsing
- Check that files follow the expected naming convention

**File Discovery Issues:**
- Verify files are in `storages/aws/` directory
- Check filename patterns match expected format
- Ensure file permissions allow reading

### Verification Commands

```bash
# Check storage structure
ls -la storages/aws/

# Verify billing files
ls storages/aws/billing_*.json

# Verify infrastructure files
ls storages/aws/infrastructure_*.json

# Test configuration analysis
./aws.py config --dry-run
```
