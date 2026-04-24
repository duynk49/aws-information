# AWS Configuration Management Consolidation

## Overview

The AWS configuration management functionality has been consolidated into a single, comprehensive `./aws.py config` command. This replaces the previous standalone `billing_analyzer.py` and `config_manager.py` scripts with an integrated solution that provides automatic billing analysis and configuration management.

## Key Benefits

- **🔄 Automatic Workflow**: Default behavior fetches fresh billing data → analyzes service usage → updates configurations
- **🎯 Single Interface**: All configuration management through one unified command
- **📊 Always Current**: Uses latest billing data to drive configuration decisions
- **🛠️ Complete Management**: Full account and service configuration capabilities
- **🔍 Intelligent Analysis**: Maps AWS billing service names to configuration keys with cost thresholds
- **⚡ Better Integration**: Follows existing AWS script patterns and authentication

## Architecture

### Module Structure
```
aws/
├── aws.py                    # Main CLI with config subcommand
├── modules/
│   ├── config.py            # Consolidated configuration management
│   ├── billing.py           # Billing data collection
│   └── infra.py            # Infrastructure inventory
├── aws_utils.py             # Shared utilities
└── docs/
    └── 08_CONFIG_CONSOLIDATION.md
```

### Class Organization
- **`ConfigManager`**: YAML configuration file management (accounts.yaml, commands.yaml)
- **`BillingAnalyzer`**: Billing data analysis and automatic configuration updates
- **`run_config()`**: Main workflow orchestration function

## Usage Guide

### Automatic Configuration Management

The primary use case - automatically fetch billing data, analyze service usage, and update configurations:

```bash
# Default automatic workflow
./aws.py config

# Preview changes without applying them
./aws.py config --dry-run

# Specify account and month
./aws.py config --account demo-company-prod --month 2026-03

# Set minimum cost threshold
./aws.py config --min-cost 0.10 --dry-run
```

### Account Management

#### Add New Account
```bash
./aws.py config add-account \
  --account-id 123456789012 \
  --name production-account \
  --services ec2,s3,iam,vpc,cloudwatch
```

#### Update Existing Account
```bash
# Add services
./aws.py config update-account \
  --account-id 123456789012 \
  --add-services lambda,sns,sqs

# Remove services
./aws.py config update-account \
  --account-id 123456789012 \
  --remove-services backup,glue

# Replace all services
./aws.py config update-account \
  --account-id 123456789012 \
  --set-services ec2,s3,iam,vpc
```

#### List Accounts
```bash
./aws.py config list-accounts
```

Example output:
```
📋 Configured AWS Accounts:
--------------------------------------------------
🏢 demo-company-prod
   ID: 123456789012
   Services (17): ce, cloudfront, cloudwatch, config, ec2, ecr, ecs, elasticache, elbv2, guardduty, kms, rds, route53, s3, securityhub, vpc, waf

🏢 demo-gifts-dev
   ID: 443370719981
   Services: None configured
```

### Service Management

#### Add New Service
```bash
./aws.py config add-service \
  --service dynamodb \
  --commands "aws dynamodb list-tables,aws dynamodb describe-limits"
```

#### List Available Services
```bash
./aws.py config list-services
```

### Configuration Validation
```bash
./aws.py config validate
```

Example output:
```
🔍 Validating configuration files...
⚠️  Validation issues found:
   - Account 123123123131 (demo-gifts-dev) has no services configured
   - Account 345345345345 (demo-gifts-ht) has no services configured

❌ Command 'config' failed: Configuration validation failed
```

## Automatic Workflow Details

### Step 1: Billing Data Collection
- Authenticates with AWS (or uses existing credentials with `--skip-login`)
- Calls AWS Cost Explorer APIs to fetch comprehensive billing data
- Saves billing data to `storages/billings/YYYY-MM/account-name.json`

### Step 2: Service Usage Analysis
- Parses billing JSON files to extract services with costs above threshold
- Maps AWS billing service names to internal configuration keys using comprehensive mapping table
- Identifies unmapped services that need manual configuration
- Compares billing data against current account configurations

### Step 3: Configuration Updates
- Automatically adds services found in billing data to account configurations
- Generates basic AWS CLI commands for newly discovered services
- Updates `accounts.yaml` and `commands.yaml` files
- Provides detailed analysis report showing what changed

### Service Mapping Examples
The analyzer automatically maps AWS billing service names to configuration keys:

| Billing Service Name | Config Key |
|---------------------|------------|
| Amazon Elastic Compute Cloud - Compute | ec2 |
| Amazon Simple Storage Service | s3 |
| AWS Lambda | lambda |
| Amazon Relational Database Service | rds |
| Amazon CloudFront | cloudfront |
| AWS Identity and Access Management | iam |

## Migration from Legacy Scripts

### From `billing_analyzer.py`
| Old Command | New Command |
|-------------|-------------|
| `./billing_analyzer.py --auto-update` | `./aws.py config` |
| `./billing_analyzer.py --dry-run --auto-update` | `./aws.py config --dry-run` |
| `./billing_analyzer.py --account demo-company-prod` | `./aws.py config --account demo-company-prod` |
| `./billing_analyzer.py --month 2026-03` | `./aws.py config --month 2026-03` |
| `./billing_analyzer.py --min-cost 0.10` | `./aws.py config --min-cost 0.10` |

### From `config_manager.py`
| Old Command | New Command |
|-------------|-------------|
| `./config_manager.py add-account --account-id X --name Y --services Z` | `./aws.py config add-account --account-id X --name Y --services Z` |
| `./config_manager.py update-account --account-id X --add-services Y` | `./aws.py config update-account --account-id X --add-services Y` |
| `./config_manager.py add-service --service X --commands Y` | `./aws.py config add-service --service X --commands Y` |
| `./config_manager.py list-accounts` | `./aws.py config list-accounts` |
| `./config_manager.py list-services` | `./aws.py config list-services` |
| `./config_manager.py validate` | `./aws.py config validate` |

## Configuration Files

### accounts.yaml Structure
```yaml
account_configs:
  '123456789012':
    name: demo-company-prod
    services:
    - ec2
    - s3
    - iam
    - vpc
    - cloudwatch
  '443370719981':
    name: demo-gifts-dev
    # No services configured yet
```

### commands.yaml Structure
```yaml
commands:
  ec2:
  - aws ec2 describe-instances
  - aws ec2 describe-security-groups
  s3:
  - aws s3api list-buckets
  - aws s3control get-public-access-block --account-id $(aws sts get-caller-identity --query Account --output text)
```

## Advanced Usage

### Cost Thresholds
Control which services are included based on spending:
```bash
# Only include services costing $1.00 or more
./aws.py config --min-cost 1.00 --dry-run

# Include all services with any cost (minimum $0.01)
./aws.py config --min-cost 0.01
```

### Account Auto-Detection
The system can automatically detect your current AWS account and update its configuration:
```bash
# Login and auto-detect current account
./aws.py config

# Use existing credentials
./aws.py config --skip-login
```

### Dry Run Analysis
Always preview changes before applying them:
```bash
./aws.py config --dry-run
```

Example dry-run output:
```
🔍 DRY RUN MODE - No changes will be made
==================================================
📝 Would add services to demo-gifts-dev: ecs, cloudfront, elbv2
📝 Would add service definition for stepfunctions with 2 commands
```

## Common Workflows

### 1. Monthly Configuration Review
```bash
# Analyze last month's usage and update configs
./aws.py config --month 2026-03 --dry-run
./aws.py config --month 2026-03  # Apply if satisfied
```

### 2. New Account Setup
```bash
# Add account manually with initial services
./aws.py config add-account \
  --account-id 123456789012 \
  --name production \
  --services ec2,s3,iam,vpc

# Then run automatic analysis to discover additional services
./aws.py config --account production
```

### 3. Service Discovery
```bash
# Discover services being used but not configured
./aws.py config --dry-run

# Add specific service configurations
./aws.py config add-service \
  --service newservice \
  --commands "aws newservice describe-resources"
```

### 4. Configuration Maintenance
```bash
# Regular validation
./aws.py config validate

# Review all current configurations
./aws.py config list-accounts
./aws.py config list-services
```

## Error Handling

The system gracefully handles various scenarios:

- **Missing services field**: Accounts without configured services are handled properly
- **Unmapped billing services**: New AWS services are identified and can be configured manually
- **Authentication issues**: Clear error messages for AWS credential problems
- **Cost thresholds**: Services below cost threshold are ignored to reduce noise
- **Future billing data**: Gracefully handles when requesting future month data

## Integration with Existing Commands

The config consolidation maintains full compatibility with existing commands:

```bash
# These continue to work unchanged
./aws.py infra --account demo-company-prod
./aws.py billing --account demo-gifts-dev --month 2026-03

# New integrated config management
./aws.py config --account demo-company-prod --dry-run
```

## Best Practices

1. **Always dry-run first**: Use `--dry-run` to preview changes before applying
2. **Regular analysis**: Run monthly to keep configurations current with actual usage
3. **Cost thresholds**: Adjust `--min-cost` based on your environment to avoid noise
4. **Validate regularly**: Use `./aws.py config validate` to check configuration health
5. **Account naming**: Use descriptive account names that match your environment structure

## Troubleshooting

### Common Issues

**Issue**: Account shows "Services: None configured"
**Solution**: Either run automatic analysis or manually add services:
```bash
./aws.py config --account account-name --dry-run
./aws.py config update-account --account-id 123456789012 --add-services ec2,s3,iam
```

**Issue**: Services appear in billing but not in configuration
**Solution**: Run automatic update or manually map the service:
```bash
./aws.py config --account account-name
```

**Issue**: Authentication errors
**Solution**: Login first or use skip-login with valid credentials:
```bash
aws login  # Or use ./aws.py config without --skip-login
```

**Issue**: Validation fails
**Solution**: Review validation output and fix configuration issues:
```bash
./aws.py config validate
./aws.py config list-accounts  # Check accounts needing services
```

## Files Removed

The following files have been removed as their functionality is now integrated:
- ❌ `billing_analyzer.py` → Use `./aws.py config`
- ❌ `config_manager.py` → Use `./aws.py config [subcommand]`

All functionality from these scripts is preserved in the new consolidated interface.
