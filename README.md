# AWS Multi-Account Automation Tool

A comprehensive Python-based automation tool for managing AWS infrastructure inventory, billing analysis, and configuration management across multiple AWS accounts.

## 🚀 Features

### Infrastructure Management
- **Multi-Account Support**: Collect resources from multiple AWS accounts using account-specific configurations
- **Service Discovery**: Automatically inventory AWS resources across 60+ services
- **Custom Commands**: Flexible AWS CLI command execution with account-specific service configurations

### Billing Analysis
- **Cost Explorer Integration**: Fetch billing data using AWS Cost Explorer API
- **Service Mapping**: Intelligent mapping between billing service names and AWS CLI services
- **Cost Thresholds**: Filter services by minimum cost to focus on meaningful usage
- **Trend Analysis**: Month-over-month billing comparison and analysis

### Configuration Management
- **YAML-Based Config**: Centralized configuration using `configs/accounts.yaml`
- **Automatic Updates**: Auto-generate missing service configurations from billing analysis
- **Account Discovery**: Detect current AWS account and prompt to add unknown accounts
- **Service Management**: Add, update, and manage AWS services and their CLI commands

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- AWS CLI configured with SSO or profiles
- Appropriate AWS permissions for target services

### Setup
```bash
# Clone and enter directory
cd /path/to/aws-automation

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install
```

## ⚙️ Configuration

### Account Configuration
Copy and customize the example configuration:
```bash
cp configs/accounts.yaml.example configs/accounts.yaml
```

Edit `configs/accounts.yaml` to define your AWS accounts and services:
```yaml
account_mapping:
  "123456789012": "my-prod-account"
  "987654321098": "my-dev-account"

account_configs:
  my-prod-account:
    services:
      - ec2
      - s3
      - lambda
      - iam

service_commands:
  ec2:
    - aws ec2 describe-instances
    - aws ec2 describe-security-groups
  s3:
    - aws s3 ls
    - aws s3api list-buckets
```

## 📋 Usage

### Quick Start
```bash
# Automatic workflow: fetch billing data, analyze, and update configs
./aws.py config

# Infrastructure inventory
./aws.py infra --account my-prod-account

# Billing analysis
./aws.py billing --account my-dev-account --month 2026-04
```

### Infrastructure Commands
```bash
# Collect infrastructure data for specific account
./aws.py infra --account demo-company-prod

# Use custom output filename
./aws.py infra --account demo-gifts --output custom-inventory

# Auto-detect current account (no --account needed)
./aws.py infra
```

### Billing Commands
```bash
# Collect billing data for specific month
./aws.py billing --account demo-gifts --month 2026-04

# Current month (default)
./aws.py billing --account demo-company-prod

# Auto-detect account, analyze current month
./aws.py billing
```

### Configuration Management
```bash
# Automatic configuration update workflow
./aws.py config                           # Fetch → analyze → update
./aws.py config --dry-run                 # Show changes without applying
./aws.py config --account specific-account

# Account management
./aws.py config add-account --account-id 123456789012 --name prod-account --services ec2,s3,iam
./aws.py config update-account --account-id 123456789012 --add-services lambda,cloudwatch
./aws.py config list-accounts

# Service management
./aws.py config add-service --service dynamodb --commands "aws dynamodb list-tables,aws dynamodb describe-table --table-name TableName"
./aws.py config list-services
./aws.py config validate
```

## 📊 Output

### File Structure
All output files are saved to `storages/aws/` with descriptive filenames:
- Infrastructure: `infrastructure_YYYY-MM_account-name_account-id.json`
- Billing: `billing_YYYY-MM_account-name_account-id.json`

### Data Format
Output files contain comprehensive JSON data:
- **Infrastructure**: Service-grouped AWS resources with command execution details
- **Billing**: Cost Explorer data with service breakdown and usage metrics
- **Metadata**: Execution timestamps, account info, success rates, and error logs

## 🏗️ Architecture

### Project Structure
```
aws/
├── aws.py                 # Main CLI entry point
├── aws_utils.py          # Shared utilities and authentication
├── modules/              # Modular functionality
│   ├── billing.py        # Billing data collection
│   ├── config.py         # Configuration management
│   └── infra.py          # Infrastructure inventory
├── configs/              # Configuration files
│   ├── accounts.yaml     # Account and service definitions
│   └── commands.yaml     # Additional command definitions
├── storages/aws/         # Output data storage
└── docs/                 # Documentation
```

### Key Components
- **ConfigManager**: YAML configuration management with validation
- **BillingAnalyzer**: Cost Explorer integration and service mapping
- **Authentication**: AWS SSO integration with account auto-detection
- **Modular Design**: Separate modules for different functionality

## 🔧 Development

### Code Quality Tools
```bash
# Format code
ruff format .

# Lint code
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Type checking
mypy .

# Run all quality checks
make quality
```

### Pre-commit Hooks
Pre-commit hooks automatically run quality checks:
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Testing
```bash
# Run specific module tests
python -m pytest tests/

# Run with coverage
pytest --cov=modules tests/
```

## 🔐 AWS Permissions

### Required IAM Permissions
Each account needs permissions for:

**Cost Explorer (Billing)**:
- `ce:GetCostAndUsage`
- `ce:GetUsageReport`

**Core Services**:
- Service-specific `List*`, `Describe*`, and `Get*` permissions
- Example: `ec2:DescribeInstances`, `s3:ListBuckets`, `iam:ListUsers`

**Account Information**:
- `sts:GetCallerIdentity`
- `organizations:DescribeAccount` (if using AWS Organizations)

### Authentication Methods
- **AWS SSO**: Preferred method (automatic login)
- **Named Profiles**: Traditional profile-based authentication
- **Environment Variables**: For CI/CD environments

## 📚 Documentation

Detailed documentation available in `docs/`:
- [Billing Analysis](docs/02_BILLING_ANALYZER.md)
- [Configuration Management](docs/08_CONFIG_CONSOLIDATION.md)
- [Code Quality Setup](docs/10_CODE_QUALITY_SETUP.md)
- [Modular Architecture](docs/06_MODULAR_REFACTORING.md)

## 🤝 Contributing

1. Follow code quality standards (ruff, mypy, pre-commit)
2. Update documentation for new features
3. Add tests for new functionality
4. Use conventional commit messages

## 📄 License

This project is part of the GTV Foundry sandbox environment.
