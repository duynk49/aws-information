#!/usr/bin/env python3
"""
AWS Common Utilities

Shared utilities for AWS scripts including authentication, configuration loading,
and account management.
"""
import json
import os
import subprocess
import yaml
import argparse
import sys
from datetime import datetime


def load_config(include_commands=False):
    """
    Load configuration from YAML files
    
    Args:
        include_commands (bool): Whether to also load commands.yaml
        
    Returns:
        tuple: (accounts_config, commands_config) if include_commands=True
        dict: accounts_config if include_commands=False
    """
    config_dir = os.path.join(os.path.dirname(__file__), 'configs')
    
    # Load accounts configuration
    accounts_path = os.path.join(config_dir, 'accounts.yaml')
    with open(accounts_path, 'r') as f:
        accounts_config = yaml.safe_load(f)
    
    if include_commands:
        # Load commands configuration
        commands_path = os.path.join(config_dir, 'commands.yaml')
        with open(commands_path, 'r') as f:
            commands_config = yaml.safe_load(f)
        return accounts_config, commands_config
    
    return accounts_config


def check_aws_credentials():
    """
    Check if AWS credentials are valid and return formatted account info
    
    Returns:
        tuple: (is_valid: bool, account_info: dict or None)
    """
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            
            # Try to get account alias
            account_alias = None
            try:
                alias_result = subprocess.run(
                    ["aws", "iam", "list-account-aliases"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if alias_result.returncode == 0:
                    alias_data = json.loads(alias_result.stdout)
                    aliases = alias_data.get('AccountAliases', [])
                    if aliases:
                        account_alias = aliases[0]
            except Exception:
                # If we can't get alias, that's ok
                pass
            
            # Return formatted account info
            formatted_info = {
                'account_id': identity.get('Account'),
                'account_alias': account_alias,
                'arn': identity.get('Arn'),
                'user_id': identity.get('UserId')
            }
            return True, formatted_info
        else:
            return False, None
    except Exception:
        return False, None


def aws_login():
    """
    Perform AWS login
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n🔐 Starting AWS Login...")
    try:
        result = subprocess.run(
            ["aws", "login"],
            timeout=300  # 5 minutes timeout
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ AWS login timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ AWS login failed: {e}")
        return False


def get_account_info():
    """
    Get current AWS account information
    
    Returns:
        dict or None: Account information if successful
    """
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            identity = json.loads(result.stdout)
            account_id = identity.get('Account')
            
            # Try to get account alias
            alias_result = subprocess.run(
                ["aws", "iam", "list-account-aliases"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            account_alias = None
            if alias_result.returncode == 0:
                alias_data = json.loads(alias_result.stdout)
                aliases = alias_data.get('AccountAliases', [])
                if aliases:
                    account_alias = aliases[0]
            
            return {
                'account_id': account_id,
                'account_alias': account_alias,
                'arn': identity.get('Arn'),
                'user_id': identity.get('UserId')
            }
        else:
            return None
    except Exception as e:
        print(f"❌ Failed to get account info: {e}")
        return None


def get_account_name_by_id(account_configs, account_id):
    """
    Get account name from account ID using account_configs
    
    Args:
        account_configs (dict): Account configurations
        account_id (str): Account ID to lookup
        
    Returns:
        str or None: Account name if found, None otherwise
    """
    if account_id in account_configs:
        return account_configs[account_id].get('name')
    return None


def get_account_id_by_name(account_configs, account_name):
    """
    Get account ID from account name using account_configs
    
    Args:
        account_configs (dict): Account configurations
        account_name (str): Account name to lookup
        
    Returns:
        str or None: Account ID if found, None otherwise
    """
    for account_id, config in account_configs.items():
        if config.get('name') == account_name:
            return account_id
    return None


def determine_account_name(account_info, provided_account, account_configs):
    """
    Determine the account name to use based on account info and configurations
    
    Args:
        account_info (dict): Account information from AWS
        provided_account (str): Account name provided by user
        account_configs (dict): Account configurations
        
    Returns:
        str or None: Account name to use
    """
    if provided_account:
        return provided_account
    
    if not account_info:
        return None
    
    account_id = account_info['account_id']
    
    # Check if account ID exists in our configs
    account_name = get_account_name_by_id(account_configs, account_id)
    if account_name:
        return account_name
    
    # If no config found, use account ID as name
    print(f"⚠️  Account ID '{account_id}' not found in account configs.")
    print("💡 You may need to add this account ID to configs/accounts.yaml")
    return account_id


def find_account_config(account_arg, account_configs):
    """
    Find account configuration by account name or ID
    
    Args:
        account_arg (str): Account name or ID provided by user
        account_configs (dict): Account configurations
        
    Returns:
        tuple: (account_found: bool, account_config: dict or None, account_id: str or None)
    """
    account_found = False
    account_config = None
    found_account_id = None
    
    # Check if provided account matches any account name in the configs
    for account_id, config in account_configs.items():
        if account_arg == config.get('name'):
            account_config = config
            account_found = True
            found_account_id = account_id
            break
    
    # If not found by name, check if it's an account ID directly
    if not account_found and account_arg in account_configs:
        account_config = account_configs[account_arg]
        account_found = True
        found_account_id = account_arg
    
    return account_found, account_config, found_account_id


def handle_aws_authentication(skip_login=False):
    """
    Handle AWS authentication workflow
    
    Args:
        skip_login (bool): Skip automatic AWS login
        
    Returns:
        dict or None: Account information if successful, None otherwise
    """
    if not skip_login:
        print("🔐 Running AWS login...")
        if not aws_login():
            print("❌ AWS login failed. Exiting.")
            return None
        
        print("✅ AWS login completed.")
        
        # Check credentials after login
        print("🔍 Verifying credentials...")
        credentials_valid, account_info = check_aws_credentials()
        if not credentials_valid:
            print("❌ AWS credentials still not valid after login. Exiting.")
            return None
        
        print("✅ Valid AWS credentials confirmed.")
    else:
        print(f"⚠️  Skipping login. Checking existing credentials...")
        credentials_valid, account_info = check_aws_credentials()
        if not credentials_valid:
            print("❌ No valid AWS credentials found and login was skipped.")
            return None
    
    return account_info


def display_account_info(account_info):
    """
    Display formatted account information
    
    Args:
        account_info (dict): Account information to display
    """
    if account_info:
        print(f"📋 Account Info:")
        print(f"   Account ID: {account_info['account_id']}")
        if account_info['account_alias']:
            print(f"   Account Alias: {account_info['account_alias']}")
        print(f"   User ARN: {account_info['arn']}")


def setup_common_parser(account_required=False, account_help=None):
    """
    Set up common command line arguments used by both aws.py and billing.py
    
    Args:
        account_required (bool): Whether the account argument is required
        account_help (str): Custom help text for account argument
    
    Returns:
        argparse.ArgumentParser: Parser with common arguments
    """
    parser = argparse.ArgumentParser(add_help=False)  # Don't add help so it can be inherited
    
    # Set default help text based on whether account is required
    if account_help is None:
        if account_required:
            account_help = "AWS account name/identifier"
        else:
            account_help = "AWS account name/identifier (optional - will auto-detect if not provided)"
    
    parser.add_argument(
        "--account", "-a", 
        required=account_required,
        help=account_help
    )
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="Skip automatic AWS login (assume already logged in)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON filename without extension (default: based on account name)",
    )
    
    return parser


def create_output_directory(date_folder=None, storage_type="infrastructures"):
    """
    Create output directory with date folder under storages (legacy function)
    
    Args:
        date_folder (str, optional): Custom date folder name. If None, uses current date.
        storage_type (str): Type of storage - "infrastructures" or "billings"
        
    Returns:
        str: Path to the created directory
    """
    if date_folder is None:
        date_folder = datetime.now().strftime("%Y-%m-%d")
    
    full_path = f"storages/{storage_type}/{date_folder}"
    os.makedirs(full_path, exist_ok=True)
    return full_path


def create_flat_storage_directory():
    """
    Create flat storage directory for AWS data files
    
    Returns:
        str: Path to the created directory (storages/aws/)
    """
    full_path = "storages/aws"
    os.makedirs(full_path, exist_ok=True)
    return full_path


def get_output_filename(account_name, output_arg=None, file_extension=".json"):
    """
    Generate output filename based on account name and arguments (legacy function)
    
    Args:
        account_name (str): Account name
        output_arg (str, optional): User-provided output filename
        file_extension (str): File extension to use
        
    Returns:
        str: Generated filename
    """
    if output_arg:
        filename = output_arg if output_arg.endswith(file_extension) else f"{output_arg}{file_extension}"
    else:
        filename = f"{account_name}{file_extension}"
    
    return filename


def get_flat_storage_filename(data_type, date_str, account_name, account_id, output_arg=None):
    """
    Generate descriptive filename for flat storage structure
    
    Args:
        data_type (str): Type of data - "billing" or "infrastructure"
        date_str (str): Date in YYYY-MM format
        account_name (str): Account name
        account_id (str): AWS account ID
        output_arg (str, optional): User-provided output filename override
        
    Returns:
        str: Generated filename in format: {type}_{YYYY-MM}_{account_name}_{account_id}.json
    """
    if output_arg:
        return output_arg if output_arg.endswith(".json") else f"{output_arg}.json"
    
    # Clean account name for filename (replace spaces and special chars with underscores)
    clean_account_name = account_name.replace(" ", "_").replace("-", "_")
    
    return f"{data_type}_{date_str}_{clean_account_name}_{account_id}.json"