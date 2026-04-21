#!/usr/bin/env python3
"""
AWS Multi-Account Automation Script

This script provides modular AWS automation functionality including:
- Infrastructure resource inventory collection
- Billing data collection and analysis

Usage:
    ./aws.py infra --account demo-company-prod
    ./aws.py billing --account demo-gifts --month 2026-04
    ./aws.py infra -a demo-gifting --output custom-name
    ./aws.py billing --month 2026-03

Prerequisites:
    - AWS CLI configured with named profiles for each account
    - Appropriate permissions for each service/operation in each account
"""
import argparse
import sys
import aws_utils
from modules import infra, billing, config


def setup_parser():
    """Setup argument parser with subcommands"""
    parser = argparse.ArgumentParser(
        description="AWS Multi-Account Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        dest='command', 
        help='Available commands',
        metavar='COMMAND'
    )
    
    # Infrastructure subcommand
    infra_parser = subparsers.add_parser(
        'infra', 
        help='Collect AWS infrastructure resource inventory',
        description='Collect AWS resources from accounts using account-specific service configurations',
        parents=[aws_utils.setup_common_parser(account_required=False)]
    )
    
    # Billing subcommand  
    billing_parser = subparsers.add_parser(
        'billing',
        help='Collect AWS billing data',
        description='Collect AWS billing data using AWS Cost Explorer',
        parents=[aws_utils.setup_common_parser(account_required=False)]
    )
    billing_parser.add_argument(
        '--month', '-m',
        help='Month in YYYY-MM format (default: current month)'
    )
    
    # Configuration subcommand with nested subcommands
    config_parser = subparsers.add_parser(
        'config',
        help='Manage AWS configurations and analyze billing',
        description='Automatic configuration management: fetch billing data, analyze service usage, and update configurations'
    )
    
    # Add common arguments to config parser
    config_parser.add_argument(
        '--account', '-a',
        help='AWS account name to operate on'
    )
    config_parser.add_argument(
        '--skip-login',
        action='store_true',
        help='Skip automatic AWS SSO login (assume already logged in)'
    )
    config_parser.add_argument(
        '--month', '-m',
        help='Month for billing analysis in YYYY-MM format (default: current month)'
    )
    config_parser.add_argument(
        '--min-cost', 
        type=float, 
        default=0.01,
        help='Minimum cost threshold in USD for service inclusion (default: 0.01)'
    )
    config_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what changes would be made without applying them'
    )
    config_parser.add_argument(
        '--output', '-o',
        help='Custom output filename (without extension)'
    )
    
    # Create nested subparsers for config management commands
    config_subparsers = config_parser.add_subparsers(
        dest='config_action', 
        help='Configuration management commands',
        metavar='ACTION'
    )
    
    # add-account subcommand
    add_account_parser = config_subparsers.add_parser(
        'add-account', 
        help='Add a new AWS account to configuration'
    )
    add_account_parser.add_argument('--account-id', required=True, help='AWS Account ID')
    add_account_parser.add_argument('--name', required=True, help='Account name/alias')
    add_account_parser.add_argument('--services', required=True, help='Comma-separated list of services')
    
    # update-account subcommand
    update_account_parser = config_subparsers.add_parser(
        'update-account',
        help='Update existing account configuration'
    )
    update_account_parser.add_argument('--account-id', required=True, help='AWS Account ID')
    update_account_parser.add_argument('--add-services', help='Comma-separated services to add')
    update_account_parser.add_argument('--remove-services', help='Comma-separated services to remove')
    update_account_parser.add_argument('--set-services', help='Comma-separated services to replace all current services')
    
    # add-service subcommand
    add_service_parser = config_subparsers.add_parser(
        'add-service',
        help='Add a new AWS service configuration'
    )
    add_service_parser.add_argument('--service', required=True, help='Service name')
    add_service_parser.add_argument('--commands', required=True, help='Comma-separated list of AWS CLI commands')
    
    # list-accounts subcommand
    config_subparsers.add_parser(
        'list-accounts',
        help='List all configured accounts'
    )
    
    # list-services subcommand
    config_subparsers.add_parser(
        'list-services', 
        help='List all configured services'
    )
    
    # validate subcommand
    config_subparsers.add_parser(
        'validate',
        help='Validate configuration files'
    )
    
    return parser


def main():
    """Main entry point"""
    parser = setup_parser()
    args = parser.parse_args()
    
    # Check if a command was provided
    if not args.command:
        parser.print_help()
        print("\n❌ Error: Please specify a command (infra, billing, or config)")
        sys.exit(1)
    
    # Handle AWS Authentication and Account Detection
    try:
        account_info = aws_utils.handle_aws_authentication(skip_login=args.skip_login)
        if not account_info:
            print("❌ Failed to authenticate or get account information")
            sys.exit(1)
    except Exception as e:
        print(f"❌ AWS Authentication failed: {str(e)}")
        sys.exit(1)

    # Display account information
    aws_utils.display_account_info(account_info)

    # Route to appropriate module based on command
    if args.command == 'infra':
        print("🏗️  Running Infrastructure Resource Collection...")
        result = infra.run_infra(account_info, args)
    elif args.command == 'billing':
        print("💰 Running Billing Data Collection...")
        result = billing.run_billing(account_info, args)
    elif args.command == 'config':
        print("⚙️  Running Configuration Management...")
        result = config.run_config(account_info, args)
    else:
        print(f"❌ Unknown command: {args.command}")
        sys.exit(1)
    
    # Handle results
    if result["success"]:
        print(f"\n🎉 Command '{args.command}' completed successfully!")
        if "output_path" in result:
            print(f"📄 Output saved to: {result['output_path']}")
        if "stats" in result:
            stats = result["stats"]
            # Handle different stat formats from different modules
            if 'success_rate' in stats:
                print(f"📊 Success Rate: {stats['success_rate']:.1f}% ({stats['successful_commands']}/{stats['total_commands']})")
            elif 'accounts_analyzed' in stats:
                print(f"📊 Analysis: {stats['accounts_analyzed']} accounts, {stats['billing_files_processed']} files, {stats['unmapped_services']} unmapped services")
    else:
        print(f"\n❌ Command '{args.command}' failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()