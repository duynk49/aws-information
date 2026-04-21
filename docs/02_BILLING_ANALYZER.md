# Billing Analyzer Usage Guide

## Overview
The `billing_analyzer.py` script automatically extracts billing information from AWS Cost Explorer data and updates your YAML configuration files using the `config_manager.py`. 

**Key Features:**
- 🔐 **AWS Auto-Detection**: Automatically detects your current AWS account from credentials
- ⚡ **Interactive Setup**: Prompts to add unknown accounts to configuration
- 📊 **Intelligent Analysis**: Compares billing data against your configuration
- 🔄 **Auto-Updates**: Updates YAML files based on actual service usage
- 🛡️ **Safe Operations**: Dry-run mode to preview all changes

## Quick Start

### 1. Basic Analysis (Read-only)
```bash
# Auto-detect current AWS account and analyze (NEW!)
./billing_analyzer.py

# Analyze specific account only
./billing_analyzer.py --account demo-company-prod

# Analyze specific month
./billing_analyzer.py --month 2026-04

# Skip AWS login (use existing credentials) 
./billing_analyzer.py --skip-login
```

**💡 Pro Tip**: When no `--account` is specified, the script will automatically detect your current AWS account from your credentials!

### 2. See What Would Change (Dry Run)
```bash
# Dry run with auto-update to see what would change
./billing_analyzer.py --dry-run --auto-update

# Dry run for current AWS account (auto-detected)
./billing_analyzer.py --skip-login --dry-run --auto-update
```

### 3. Actually Update Configuration
```bash
# Auto-update configurations based on billing data
./billing_analyzer.py --auto-update

# Auto-detect account and update (seamless workflow)
./billing_analyzer.py --skip-login --auto-update
```

## Advanced Usage

### Cost Threshold
By default, only services with costs ≥ $0.01 are considered. You can adjust this:

```bash
# Only consider services with costs ≥ $0.10
./billing_analyzer.py --min-cost 0.10

# Include services with any cost (even $0.00)
./billing_analyzer.py --min-cost 0.00
```

### Combined Options
```bash
# Analyze March 2026 for demo-company-prod with $0.05 threshold
./billing_analyzer.py --account demo-company-prod --month 2026-03 --min-cost 0.05

# Dry run auto-update for current AWS account 
./billing_analyzer.py --dry-run --auto-update --skip-login

# Auto-detect account and update configurations
./billing_analyzer.py --auto-update
```

## Account Auto-Detection & Setup

### 🎯 How Auto-Detection Works
When you run the script without `--account`, it:
1. **Detects current AWS account** from your active credentials
2. **Looks up account name** in your configuration files
3. **Prompts to add unknown accounts** interactively
4. **Proceeds with analysis** using the detected/configured account

### 🔧 Interactive Account Configuration

When the script auto-detects an AWS account that isn't in your configuration, it will guide you through adding it:

```
⚠️  Skipping login. Checking existing credentials...
📋 Detected Account Info:
   Account ID: 1234567890
   User ARN: arn:aws:sts::...

❓ Account ID '1234567890' not found in configuration.
📋 Account Info:
   Account ID: 1234567890
   User ARN: arn:aws:sts::...

➕ Would you like to add this account to the configuration? (y/n): y
📝 Enter a name for this account (default: account-1234567890): demo_account

🛠️  What services should be configured for this account?
💡 You can add common services like: ec2, s3, iam, lambda, rds, vpc, cloudwatch
💡 Or press Enter for a default set: ec2, s3, iam, vpc, cloudwatch
🔧 Enter services (comma-separated): 

✅ Added account 'demo_account' (ID: 1234567890) with services: ec2, s3, iam, vpc, cloudwatch
✅ Successfully added account 'demo_account' to configuration.
🎯 Using account: demo_account (ID: 1234567890)
```

**✅ Result**: Account is now permanently configured and ready for billing analysis!

## What the Script Does

### � AWS Account Detection
- **Auto-detection**: Automatically detects current AWS account from credentials when no `--account` specified
- **AWS SSO Integration**: Uses the same login method as `aws.py` for consistency
- **Account validation**: Prompts to add account to configuration if not found
- **Credential handling**: Handles AWS SSO login or can skip with `--skip-login`
- **Account info display**: Shows account ID, alias (if available), and user ARN

### �📊 Analysis Report
- **Services found in billing**: Lists all AWS services with costs above threshold
- **Services in config but not used**: Services configured but not appearing in billing
- **Services found but not in config**: Services used but not in your configuration
- **Services correctly configured**: Services that match between billing and config
- **Unmapped services**: Services that need mapping rules added to the script

### 🔄 Auto-Update Actions
When using `--auto-update`, the script will:

1. **Add new services** to `commands.yaml` for any services found in billing
2. **Update account configurations** to include all services found in billing data
3. **Generate appropriate AWS CLI commands** for new services

### 🛡️ Safety Features
- **Dry run mode**: Use `--dry-run` to see what would change without making changes
- **Validation**: Uses existing `config_manager.py` validation logic
- **Backup-friendly**: YAML updates preserve formatting and structure

## Example Complete Workflow

### Scenario: First Time Using a New AWS Account

```bash
# 1. Run analyzer (auto-detects unknown account)
$ ./billing_analyzer.py --skip-login --dry-run --auto-update

⚠️  Skipping login. Checking existing credentials...
📋 Detected Account Info:
   Account ID: 1234567890
   User ARN: arn:aws:sts::1234567890:assumed-role/Role/user

❓ Account ID '1234567890' not found in configuration.
# [Interactive prompts to add account]
✅ Successfully added account 'my-new-account' to configuration.

🎯 Using account: my-new-account (ID: 1234567890)
❌ No billing files found to analyze
💡 Expected location: billings/YYYY-MM/my-new-account.json

# 2. Collect billing data first
$ ./billing.py --account my-new-account

# 3. Run analyzer again  
$ ./billing_analyzer.py --skip-login --auto-update
🎯 Using account: my-new-account (ID: 1234567890)
📊 BILLING ANALYSIS REPORT
# [Analysis results and auto-updates]
✅ Configuration update complete!
```

### Scenario: Regular Analysis of Existing Account

```bash
# Simple one-command analysis and update
$ ./billing_analyzer.py --skip-login --auto-update

⚠️  Skipping login. Checking existing credentials...
🎯 Using account: demo-company-prod (ID: 123456789012)
📊 BILLING ANALYSIS REPORT
✅ Services correctly configured (17): ce, cloudfront, cloudwatch, config, ec2...
✅ Configuration update complete!
```

## Prerequisites

1. **AWS Credentials**: Valid AWS credentials configured (same as `aws.py`)
   - AWS SSO login capability OR existing valid credentials
   - Permissions to read billing data and account information

2. **Billing JSON files** must exist in `billings/` directory
   - Organized by month: `billings/2026-04/account-name.json`
   - Generated by your billing collection script (`billing.py`)

3. **Configuration files** must exist:
   - `configs/accounts.yaml`
   - `configs/commands.yaml`
   - `config_manager.py`

4. **Proper structure** in billing JSON files:
   - Account name mapping
   - Cost and usage data from AWS Cost Explorer

**Note**: Unknown accounts will be automatically prompted for addition to configuration!

## Tips

- **Start with auto-detection**: Simply run `./billing_analyzer.py --skip-login --dry-run --auto-update` to see what would happen
- **Use dry-run first**: Always use `--dry-run --auto-update` first to see what would change
- **Review unmapped services**: Check the output for services that need mapping rules
- **Cost threshold**: Adjust `--min-cost` based on your needs (avoid noise from very low costs)
- **Account setup**: Let the script auto-detect and add new accounts interactively
- **Backup configs**: Consider backing up your YAML files before running auto-updates

## Integration with Existing Workflow

This script complements your existing tools:

1. **AWS Authentication**: Uses same method as `aws.py` (AWS SSO login or existing credentials)
2. **Account Setup**: Automatically detects and configures unknown accounts
3. **Collect billing**: Use your existing `billing.py` script  
4. **Analyze & update**: Use `billing_analyzer.py --auto-update`
5. **Execute commands**: Use your existing `aws.py` script with updated configs

**💡 Streamlined workflow**: `./billing_analyzer.py --skip-login --auto-update` does it all!

## Troubleshooting

- **No billing files found**: Check that JSON files exist in `billings/` directory with correct account name
- **Account ID not found**: Script will prompt to add unknown accounts automatically
- **Permission errors**: Make sure script is executable (`chmod +x billing_analyzer.py`)
- **YAML errors**: The script validates configuration before making changes
- **AWS credentials**: Ensure valid AWS credentials or use the login functionality
- **Unknown account prompts**: Follow the interactive prompts to add new accounts to configuration

**🔧 Most common fix**: Run `./billing_analyzer.py --skip-login --dry-run` to test auto-detection