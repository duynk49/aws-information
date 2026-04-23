#!/usr/bin/env python3
"""
AWS Configuration Management Module

This module provides comprehensive AWS configuration management including:
- Billing data analysis and service mapping
- YAML configuration file management (accounts.yaml, commands.yaml)
- Automatic configuration updates based on billing analysis

Classes:
    ConfigManager: Manages YAML configuration files
    BillingAnalyzer: Analyzes billing data and updates configurations

Functions:
    run_config: Main configuration workflow function
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import aws_utils
from . import billing


class ConfigManager:
    """Manages AWS configuration YAML files (accounts.yaml and commands.yaml)"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / "configs"
        self.accounts_file = self.config_dir / "accounts.yaml"
        self.commands_file = self.config_dir / "commands.yaml"
    
    def load_accounts(self):
        """Load accounts configuration from YAML"""
        with open(self.accounts_file, 'r') as f:
            return yaml.safe_load(f)
    
    def save_accounts(self, config):
        """Save accounts configuration to YAML"""
        with open(self.accounts_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
    
    def load_commands(self):
        """Load commands configuration from YAML"""
        with open(self.commands_file, 'r') as f:
            return yaml.safe_load(f)
    
    def save_commands(self, config):
        """Save commands configuration to YAML"""
        with open(self.commands_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
    
    def add_account(self, account_id, name, services):
        """Add a new account to the configuration"""
        config = self.load_accounts()
        
        # Add to account configs only
        config['account_configs'][account_id] = {
            'name': name,
            'services': services
        }
        
        self.save_accounts(config)
        print(f"✅ Added account '{name}' (ID: {account_id}) with services: {', '.join(services)}")
    
    def update_account(self, account_id, add_services=None, remove_services=None, set_services=None):
        """Update an existing account configuration"""
        config = self.load_accounts()
        
        if account_id not in config['account_configs']:
            print(f"❌ Account ID '{account_id}' not found in configuration")
            return False
        
        account_config = config['account_configs'][account_id]
        current_services = set(account_config.get('services', []))  # Handle missing services field
        
        if set_services:
            # Replace all services
            new_services = set_services
        else:
            # Modify existing services
            new_services = current_services.copy()
            
            if add_services:
                new_services.update(add_services)
                print(f"➕ Adding services: {', '.join(add_services)}")
            
            if remove_services:
                new_services -= set(remove_services)
                print(f"➖ Removing services: {', '.join(remove_services)}")
        
        account_config['services'] = sorted(list(new_services))
        self.save_accounts(config)
        
        account_name = account_config['name']
        print(f"✅ Updated account '{account_name}' (ID: {account_id})")
        print(f"   New services: {', '.join(sorted(new_services))}")
        return True
    
    def add_service(self, service_name, commands):
        """Add a new service with its commands"""
        config = self.load_commands()
        
        config['commands'][service_name] = commands
        self.save_commands(config)
        
        print(f"✅ Added service '{service_name}' with {len(commands)} command(s):")
        for cmd in commands:
            print(f"   - {cmd}")
    
    def list_accounts(self):
        """List all configured accounts"""
        config = self.load_accounts()
        
        print("📋 Configured AWS Accounts:")
        print("-" * 50)
        
        for account_id, account_config in config['account_configs'].items():
            name = account_config['name']
            services = account_config.get('services', [])  # Handle missing services field
            print(f"🏢 {name}")
            print(f"   ID: {account_id}")
            if services:
                print(f"   Services ({len(services)}): {', '.join(services)}")
            else:
                print(f"   Services: None configured")
            print()
    
    def list_services(self):
        """List all configured services"""
        config = self.load_commands()
        
        print("🛠️  Configured AWS Services:")
        print("-" * 50)
        
        for service_name, commands in config['commands'].items():
            print(f"⚙️  {service_name} ({len(commands)} commands)")
            for cmd in commands:
                print(f"   - {cmd}")
            print()
    
    def validate(self):
        """Validate configuration files"""
        print("🔍 Validating configuration files...")
        
        try:
            # Load and validate accounts.yaml
            accounts_config = self.load_accounts()
            commands_config = self.load_commands()
            
            # Check for required keys
            required_account_keys = ['account_configs']
            for key in required_account_keys:
                if key not in accounts_config:
                    print(f"❌ Missing required key '{key}' in accounts.yaml")
                    return False
            
            if 'commands' not in commands_config:
                print("❌ Missing required key 'commands' in commands.yaml")
                return False
            
            # Validate account configurations
            available_services = set(commands_config['commands'].keys())
            issues = []
            
            for account_id, account_config in accounts_config['account_configs'].items():
                if 'name' not in account_config:
                    issues.append(f"Account {account_id} missing 'name' field")
                
                services = account_config.get('services', [])
                if not services:
                    issues.append(f"Account {account_id} ({account_config.get('name', 'unnamed')}) has no services configured")
                    continue
                
                # Check if all services are defined in commands.yaml
                for service in services:
                    if service not in available_services:
                        issues.append(f"Account {account_id} uses undefined service '{service}'")
            
            if issues:
                print("⚠️  Validation issues found:")
                for issue in issues:
                    print(f"   - {issue}")
                return False
            
            print("✅ All configuration files are valid!")
            print(f"   📊 {len(accounts_config['account_configs'])} accounts configured")
            print(f"   🛠️  {len(commands_config['commands'])} services defined")
            
            return True
            
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error: {e}")
            return False
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False


class BillingAnalyzer:
    """Analyzes AWS billing data and automatically updates configurations"""
    
    def __init__(self, min_cost_threshold=0.01):
        self.config_manager = ConfigManager()
        self.min_cost_threshold = Decimal(str(min_cost_threshold))
        
        # AWS service name mapping from billing service names to our config keys
        self.service_mapping = {
            # Core Compute & Containers
            'Amazon Elastic Compute Cloud - Compute': 'ec2',
            'Amazon EC2 Container Registry (ECR)': 'ecr',
            'Amazon EC2 Container Service': 'ecs',
            'Amazon Elastic Container Service': 'ecs',
            'AWS Lambda': 'lambda',
            'AWS Batch': 'batch',
            
            # Storage
            'Amazon Simple Storage Service': 's3',
            'Amazon Elastic Block Store': 'ebs',
            'Amazon Elastic File System': 'efs',
            'Amazon FSx': 'fsx',
            
            # Database
            'Amazon Relational Database Service': 'rds',
            'Amazon DynamoDB': 'dynamodb',
            'Amazon ElastiCache': 'elasticache',
            'Amazon MemoryDB for Redis': 'memorydb',
            'Amazon DocumentDB': 'documentdb',
            'Amazon Neptune': 'neptune',
            'Amazon Timestream': 'timestream',
            
            # Networking & Content Delivery
            'Amazon Virtual Private Cloud': 'vpc',
            'Amazon CloudFront': 'cloudfront',
            'Amazon Route 53': 'route53',
            'Elastic Load Balancing': 'elbv2',
            'Amazon Elastic Load Balancing': 'elbv2',
            'Amazon API Gateway': 'apigateway',
            'AWS Direct Connect': 'directconnect',
            'Amazon VPC': 'vpc',
            
            # Security & Identity
            'AWS Identity and Access Management': 'iam',
            'AWS Key Management Service': 'kms',
            'AWS Secrets Manager': 'secretsmanager',
            'AWS Certificate Manager': 'acm',
            'Amazon Cognito': 'cognito',
            'AWS WAF': 'waf',
            'AWS WAFv2': 'wafv2',
            'AWS Shield': 'shield',
            'Amazon GuardDuty': 'guardduty',
            'AWS Security Hub': 'securityhub',
            'Amazon Inspector': 'inspector',
            'Amazon Macie': 'macie',
            
            # Analytics & Machine Learning
            'Amazon Kinesis': 'kinesis',
            'Amazon Kinesis Data Firehose': 'firehose',
            'AWS Glue': 'glue',
            'Amazon Athena': 'athena',
            'Amazon QuickSight': 'quicksight',
            'Amazon Elasticsearch Service': 'elasticsearch',
            'Amazon OpenSearch Service': 'opensearch',
            'Amazon SageMaker': 'sagemaker',
            'Amazon Comprehend': 'comprehend',
            'Amazon Rekognition': 'rekognition',
            'Amazon Translate': 'translate',
            'Amazon Polly': 'polly',
            'Amazon Transcribe': 'transcribe',
            'Amazon Textract': 'textract',
            
            # Application Integration
            'Amazon Simple Notification Service': 'sns',
            'Amazon Simple Queue Service': 'sqs',
            'AWS Step Functions': 'stepfunctions',
            'Amazon EventBridge': 'eventbridge',
            'Amazon Simple Email Service': 'ses',
            
            # Management & Monitoring
            'Amazon CloudWatch': 'cloudwatch',
            'AmazonCloudWatch': 'cloudwatch',
            'AWS CloudTrail': 'cloudtrail',
            'AWS Config': 'config',
            'AWS Systems Manager': 'ssm',
            'AWS Backup': 'backup',
            'AWS CloudFormation': 'cloudformation',
            'AWS Auto Scaling': 'autoscaling',
            'Amazon CloudWatch Events': 'cloudwatch-events',
            'Amazon CloudWatch Logs': 'cloudwatch-logs',
            'AWS X-Ray': 'xray',
            
            # Developer Tools
            'AWS CodeCommit': 'codecommit',
            'AWS CodeBuild': 'codebuild',
            'AWS CodePipeline': 'codepipeline',
            'AWS CodeDeploy': 'codedeploy',
            'AWS CodeStar': 'codestar',
            'AWS Cloud9': 'cloud9',
            
            # Cost Management
            'AWS Cost Explorer': 'ce',
            'AWS Budgets': 'budgets',
            'AWS Cost and Usage Report': 'cur',
            
            # Migration & Transfer
            'AWS Database Migration Service': 'dms',
            'AWS DataSync': 'datasync',
            'AWS Migration Hub': 'migrationhub',
            'AWS Server Migration Service': 'sms',
            
            # IoT
            'AWS IoT Core': 'iot',
            'AWS IoT Device Management': 'iot-device',
            'AWS IoT Analytics': 'iot-analytics',
            
            # Game Development
            'Amazon GameLift': 'gamelift',
            
            # Media Services
            'Amazon Elastic Transcoder': 'elastictranscoder',
            'AWS Elemental MediaConvert': 'mediaconvert',
            'AWS Elemental MediaLive': 'medialive',
            'AWS Elemental MediaPackage': 'mediapackage',
            'AWS Elemental MediaStore': 'mediastore',
            
            # Quantum Computing
            'Amazon Braket': 'braket',
            
            # Blockchain
            'Amazon Managed Blockchain': 'managedblockchain',
            
            # Satellite
            'AWS Ground Station': 'groundstation',

            # Bedrock
            'Cohere Rerank v3.5 (Amazon Bedrock Edition)': 'bedrock',
            
            # Amazon Lightsail
            'Amazon Lightsail': 'lightsail'
        }
    
    def get_billing_files(self, account_name=None, month=None):
        """Get list of billing JSON files to analyze from flat storage structure"""
        aws_dir = Path("storages/aws")
        
        if not aws_dir.exists():
            print("❌ No storages/aws/ directory found")
            return []
        
        files = []
        
        # Get all billing files from flat structure
        billing_pattern = "billing_*.json"
        for file in aws_dir.glob(billing_pattern):
            # Parse filename: billing_{YYYY-MM}_{account_name}_{account_id}.json
            parts = file.stem.split('_')
            if len(parts) >= 4 and parts[0] == 'billing':
                file_month = parts[1]  # YYYY-MM format
                file_account_name = '_'.join(parts[2:-1])  # Account name (may contain underscores)
                
                # Filter by month if specified
                if month and file_month != month:
                    continue
                    
                # Filter by account name if specified
                if account_name:
                    # Normalize both names by replacing hyphens with underscores for comparison
                    # This handles the inconsistency where billing files use underscores but 
                    # account names from config may have hyphens
                    normalized_account_name = account_name.replace('-', '_')
                    normalized_file_account_name = file_account_name.replace('-', '_')
                    
                    if normalized_account_name not in normalized_file_account_name:
                        continue
                
                files.append(file)
        
        return sorted(files)
    
    def extract_services_from_billing(self, billing_file):
        """Extract services with costs above threshold from billing JSON"""
        with open(billing_file, 'r') as f:
            data = json.load(f)
        
        account_name = data.get('account', 'unknown')
        month = data.get('billing_period', {}).get('month', 'unknown')
        
        # Services to ignore (not actual AWS services)
        ignored_services = {
            'Tax',
            'EC2 - Other',
            'Credits',
            'Refunds',
            'Upfront Fee',
            'Support',
            'AWS Support'
        }
        
        services_found = []
        groups = data.get('billing_data', {}).get('monthly_cost_by_service', {}).get('ResultsByTime', [])
        
        if not groups:
            print(f"⚠️  No billing data found in {billing_file}")
            return account_name, month, services_found
        
        # Extract services from the first (and typically only) time period
        for time_period in groups:
            for group in time_period.get('Groups', []):
                service_name = group.get('Keys', [''])[0]
                if not service_name or service_name in ignored_services:
                    continue
                
                # Get cost amount - try UnblendedCost first, then BlendedCost
                metrics = group.get('Metrics', {})
                amount = '0'
                if 'UnblendedCost' in metrics:
                    amount = metrics['UnblendedCost'].get('Amount', '0')
                elif 'BlendedCost' in metrics:
                    amount = metrics['BlendedCost'].get('Amount', '0')
                
                try:
                    cost = Decimal(amount)
                    if cost >= self.min_cost_threshold:
                        # Map to our service key
                        service_key = self.service_mapping.get(service_name)
                        if service_key:
                            services_found.append((service_key, service_name, cost))
                        else:
                            # Unmapped service - still include for tracking
                            services_found.append((service_name, service_name, cost))
                except (ValueError, TypeError):
                    continue
        
        return account_name, month, services_found
    
    def get_account_id_by_name(self, account_name):
        """Get account ID from account name using current YAML config"""
        try:
            config = self.config_manager.load_accounts()
            account_configs = config.get('account_configs', {})
            for account_id, account_config in account_configs.items():
                if account_config.get('name') == account_name:
                    return account_id
            return None
        except Exception:
            return None
    
    def analyze_billing_files(self, files):
        """Analyze all billing files and return comprehensive analysis"""
        analysis_results = {}
        unmapped_services = set()
        
        print(f"🔍 Analyzing {len(files)} billing files...")
        print()
        
        for billing_file in files:
            print(f"📄 Analyzing: {billing_file}")
            account_name, month, services = self.extract_services_from_billing(billing_file)
            
            if account_name not in analysis_results:
                analysis_results[account_name] = {
                    'account_id': self.get_account_id_by_name(account_name),
                    'months': {},
                    'all_services': set(),
                    'unmapped_services': set()
                }
            
            analysis_results[account_name]['months'][month] = services
            
            # Track all services found for this account
            for service in services:
                service_key, original_name, cost = service
                analysis_results[account_name]['all_services'].add(service_key)
                
                # Track unmapped services
                if service_key == original_name and service_key not in self.service_mapping.values():
                    analysis_results[account_name]['unmapped_services'].add(service_key)
                    unmapped_services.add(service_key)
            
            print(f"   Found {len(services)} services with costs >= ${self.min_cost_threshold}")
        
        return analysis_results, unmapped_services
    
    def generate_service_commands(self, service_key):
        """Generate basic AWS CLI commands for a new service"""
        # Service-specific commands
        service_commands = {
            'stepfunctions': [
                'aws stepfunctions list-state-machines',
                'aws stepfunctions describe-state-machine'
            ],
            'waf': [
                'aws waf list-web-acls',
                'aws waf list-rules'
            ],
            'securityhub': [
                'aws securityhub get-enabled-standards',
                'aws securityhub get-findings'
            ],
            'glue': [
                'aws glue get-databases',
                'aws glue get-tables',
                'aws glue get-jobs'
            ],
            'athena': [
                'aws athena list-work-groups',
                'aws athena list-query-executions'
            ],
            'ce': [
                'aws ce get-cost-and-usage --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY --metrics BlendedCost',
                'aws ce get-reservation-coverage --time-period Start=2026-03-01,End=2026-04-01 --granularity MONTHLY'
            ],
            'guardduty': [
                'aws guardduty list-detectors',
                'aws guardduty get-findings'
            ]
        }
        
        return service_commands.get(service_key, [
            f'aws {service_key} describe-{service_key}',
            f'aws {service_key} list-{service_key}'
        ])
    
    def print_analysis_report(self, analysis_results, unmapped_services):
        """Print comprehensive analysis report"""
        print("=" * 80)
        print("📊 BILLING ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        # Load current configuration for comparison
        try:
            current_config = self.config_manager.load_accounts()
            current_commands = self.config_manager.load_commands()
        except Exception as e:
            print(f"⚠️  Could not load current configuration: {e}")
            current_config = {'account_configs': {}}
            current_commands = {'commands': {}}
        
        for account_name, data in analysis_results.items():
            account_id = data['account_id']
            print(f"🏢 Account: {account_name}")
            if account_id:
                print(f"   ID: {account_id}")
            else:
                print(f"   ID: Not found in configuration")
            print()
            
            # Services found in billing
            found_services = sorted(data['all_services'])
            print(f"   📈 Services found in billing ({len(found_services)}):")
            for service in found_services:
                mapped_status = "✅" if service in self.service_mapping.values() else "❓"
                print(f"      {mapped_status} {service}")
            print()
            
            # Current configuration vs found services
            if account_id and account_id in current_config.get('account_configs', {}):
                current_services = set(current_config['account_configs'][account_id].get('services', []))
                
                # Services in config but not in billing
                config_only = current_services - data['all_services']
                if config_only:
                    print(f"   ⚠️  Services in config but not in billing ({len(config_only)}):")
                    for service in sorted(config_only):
                        print(f"      📝 {service}")
                    print()
                
                # Services in billing but not in config
                billing_only = data['all_services'] - current_services
                if billing_only:
                    print(f"   ➕ Services in billing but not in config ({len(billing_only)}):")
                    for service in sorted(billing_only):
                        print(f"      💰 {service}")
                    print()
                
                # Services in both
                both = current_services & data['all_services']
                if both:
                    print(f"   ✅ Services in both config and billing ({len(both)}):")
                    for service in sorted(both):
                        print(f"      🎯 {service}")
                    print()
                elif not current_services:
                    print(f"   📝 Account has no services configured yet")
                    print()
            
            # Unmapped services for this account
            if data['unmapped_services']:
                print(f"   🔧 Unmapped services ({len(data['unmapped_services'])}):")
                for service in sorted(data['unmapped_services']):
                    print(f"      ❓ {service}")
            
            print("-" * 60)
            print()
        
        # Global unmapped services
        if unmapped_services:
            print("🔧 UNMAPPED SERVICES (need to add to service_mapping):")
            print("-" * 60)
            for service in sorted(unmapped_services):
                print(f"❓ {service}")
            print()
    
    def auto_update_configurations(self, analysis_results, dry_run=False):
        """Automatically update account and service configurations"""
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print("=" * 50)
        else:
            print("🔄 AUTO-UPDATING CONFIGURATIONS")
            print("=" * 50)
        
        try:
            current_commands = self.config_manager.load_commands()
            available_services = set(current_commands.get('commands', {}).keys())
        except Exception as e:
            print(f"❌ Error loading commands configuration: {e}")
            return False
        
        for account_name, data in analysis_results.items():
            account_id = data['account_id']
            if not account_id:
                print(f"⚠️  Skipping {account_name}: Account ID not found in configuration")
                continue
            
            # Services that need to be added to the account
            found_services = data['all_services']
            mapped_services = {s for s in found_services if s in available_services}
            
            if mapped_services:
                if dry_run:
                    print(f"📝 Would add services to {account_name}: {', '.join(sorted(mapped_services))}")
                else:
                    print(f"➕ Adding services to {account_name}: {', '.join(sorted(mapped_services))}")
                    self.config_manager.update_account(account_id, add_services=list(mapped_services))
            
            # Services that need command definitions
            unmapped_services = data['unmapped_services']
            for service in unmapped_services:
                if service not in available_services:
                    commands = self.generate_service_commands(service)
                    if dry_run:
                        print(f"📝 Would add service definition for {service} with {len(commands)} commands")
                    else:
                        print(f"➕ Adding service definition for {service}")
                        self.config_manager.add_service(service, commands)
        
        if not dry_run:
            print("✅ Configuration update completed!")
        
        return True


def prompt_add_account(account_id, account_info, config_manager):
    """Prompt user to add account to configuration"""
    print(f"\n❓ Account ID '{account_id}' not found in configuration.")
    print(f"📋 Account Info:")
    print(f"   Account ID: {account_info['account_id']}")
    if account_info['account_alias']:
        print(f"   Account Alias: {account_info['account_alias']}")
    print(f"   User ARN: {account_info['arn']}")
    
    while True:
        response = input(f"\n➕ Would you like to add this account to the configuration? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            break
        elif response in ['n', 'no']:
            print("❌ Skipping account addition.")
            return None
        else:
            print("Please enter 'y' or 'n'")
    
    # Get account name
    default_name = account_info['account_alias'] if account_info['account_alias'] else f"account-{account_id}"
    while True:
        account_name = input(f"📝 Enter a name for this account (default: {default_name}): ").strip()
        if not account_name:
            account_name = default_name
        
        if account_name:
            break
        print("Account name cannot be empty.")
    
    # Get services to configure
    print(f"\n🛠️  What services should be configured for this account?")
    print(f"💡 You can add common services like: ec2, s3, iam, lambda, rds, vpc, cloudwatch")
    print(f"💡 Or press Enter for a default set: ec2, s3, iam, vpc, cloudwatch")
    
    services_input = input(f"🔧 Enter services (comma-separated): ").strip()
    if not services_input:
        services = ['ec2', 's3', 'iam', 'vpc', 'cloudwatch']
    else:
        services = [s.strip() for s in services_input.split(',') if s.strip()]
    
    # Add the account
    try:
        config_manager.add_account(account_id, account_name, services)
        print(f"✅ Successfully added account '{account_name}' to configuration.")
        return account_name
    except Exception as e:
        print(f"❌ Failed to add account: {e}")
        return None


def run_config(account_info, args):
    """
    Main function to run configuration management operations
    
    Args:
        account_info: Dictionary containing AWS account information
        args: Parsed command line arguments for config operations
        
    Returns:
        Dict containing results and status
    """
    
    # If this is a management subcommand, handle it directly
    if hasattr(args, 'config_action') and args.config_action:
        return handle_config_management(args)
    
    # Default behavior: automatic billing fetch -> analysis -> config update
    print("🔄 Running automatic configuration update workflow...")
    print("   1. Fetching fresh billing data")
    print("   2. Analyzing billing for service usage") 
    print("   3. Updating configurations based on analysis")
    print()
    
    try:
        # Step 1: Fetch fresh billing data
        print("💰 Fetching fresh billing data...")
        billing_result = billing.run_billing(account_info, args)
        
        if not billing_result["success"]:
            return {
                "success": False,
                "error": f"Failed to fetch billing data: {billing_result.get('error', 'Unknown error')}"
            }
        
        print(f"✅ Billing data fetched successfully")
        if "output_path" in billing_result:
            print(f"📄 Billing data saved to: {billing_result['output_path']}")
        print()
        
        # Step 2: Analyze billing data
        print("🔍 Analyzing billing data for service usage...")
        analyzer = BillingAnalyzer(min_cost_threshold=getattr(args, 'min_cost', 0.01))
        
        # Get account name for billing file lookup
        account_name = None
        if account_info:
            # Try to find account name from configuration
            accounts_config = aws_utils.load_config(include_commands=False)
            account_name = aws_utils.get_account_name_by_id(
                accounts_config.get('account_configs', {}), 
                account_info['account_id']
            )
        
        # Get billing files to analyze (latest month if no specific month provided)
        billing_files = analyzer.get_billing_files(
            account_name=account_name,
            month=getattr(args, 'month', None)
        )
        
        if not billing_files:
            return {
                "success": False,
                "error": "No billing files found to analyze after data fetch"
            }
        
        # Analyze the billing files
        analysis_results, unmapped_services = analyzer.analyze_billing_files(billing_files)
        
        # Step 3: Print analysis report
        analyzer.print_analysis_report(analysis_results, unmapped_services)
        
        # Step 4: Auto-update configurations
        dry_run = getattr(args, 'dry_run', False)
        update_success = analyzer.auto_update_configurations(analysis_results, dry_run=dry_run)
        
        if not update_success:
            return {
                "success": False,
                "error": "Failed to update configurations"
            }
        
        # Return success
        stats = {
            'accounts_analyzed': len(analysis_results),
            'billing_files_processed': len(billing_files),
            'unmapped_services': len(unmapped_services)
        }
        
        return {
            "success": True,
            "message": "Configuration update workflow completed successfully",
            "stats": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Configuration workflow failed: {str(e)}"
        }


def handle_config_management(args):
    """Handle configuration management subcommands"""
    config_manager = ConfigManager()
    
    try:
        if args.config_action == 'add-account':
            services = [s.strip() for s in args.services.split(',')]
            config_manager.add_account(args.account_id, args.name, services)
            return {"success": True, "message": f"Added account '{args.name}'"}
        
        elif args.config_action == 'update-account':
            add_services = [s.strip() for s in args.add_services.split(',')] if args.add_services else None
            remove_services = [s.strip() for s in args.remove_services.split(',')] if args.remove_services else None
            set_services = [s.strip() for s in args.set_services.split(',')] if args.set_services else None
            
            success = config_manager.update_account(
                args.account_id,
                add_services=add_services,
                remove_services=remove_services,
                set_services=set_services
            )
            
            if success:
                return {"success": True, "message": f"Updated account '{args.account_id}'"}
            else:
                return {"success": False, "error": f"Account '{args.account_id}' not found"}
        
        elif args.config_action == 'add-service':
            commands = [cmd.strip() for cmd in args.commands.split(',')]
            config_manager.add_service(args.service, commands)
            return {"success": True, "message": f"Added service '{args.service}'"}
        
        elif args.config_action == 'list-accounts':
            config_manager.list_accounts()
            return {"success": True, "message": "Listed all accounts"}
        
        elif args.config_action == 'list-services':
            config_manager.list_services()
            return {"success": True, "message": "Listed all services"}
        
        elif args.config_action == 'validate':
            is_valid = config_manager.validate()
            if is_valid:
                return {"success": True, "message": "Configuration validation passed"}
            else:
                return {"success": False, "error": "Configuration validation failed"}
        
        else:
            return {"success": False, "error": f"Unknown config action: {args.config_action}"}
    
    except Exception as e:
        return {"success": False, "error": f"Config management error: {str(e)}"}