#!/usr/bin/env python3
"""
AWS Infrastructure Resource Inventory Module

This module collects AWS resources from accounts using account-specific
service configurations and AWS CLI profiles.
"""

import json
import logging
import os
import shlex
import subprocess
import sys
import traceback
from datetime import datetime

import aws_utils


def setup_error_logging():
    """Setup error logging to storages/logs/{date}.log"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "storages", "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Create log file with current date
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"{today_str}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(sys.stdout),  # Also log to console
        ],
    )

    return logging.getLogger("aws_infra_module")


def execute_aws_command(command, service_name, error_logger, command_index=None):
    """Execute a single AWS command and return the result"""
    try:
        # Run the command and capture output
        result = subprocess.run(
            shlex.split(command), capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            try:
                # Handle empty or whitespace-only responses
                output = result.stdout.strip()
                if not output:
                    return {
                        "data": {"note": "Empty response (no data available)"},
                        "success": True,
                    }
                return {"data": json.loads(output), "success": True}
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON response for {service_name}: {e!s}"
                error_logger.error(
                    f"JSON_DECODE_ERROR - Service: {service_name}, Command: {command}, Error: {error_msg}\nStdout: {result.stdout[:500]}..."
                )
                return {"error": error_msg, "success": False}
        else:
            # Handle known "expected" errors more gracefully for initial commands too
            error_msg = result.stderr.strip()

            if "NoSuchEntity" in error_msg and "Password Policy" in error_msg:
                # IAM password policy not existing is normal
                return {
                    "data": {"note": "No password policy configured (this is normal)"},
                    "success": True,
                }
            elif (
                "InvalidParameterValue" in error_msg
                and "cache security groups" in error_msg
            ):
                # Cache security groups deprecated in VPC - this is expected
                return {
                    "data": {
                        "note": "Cache security groups not available in VPC (expected)"
                    },
                    "success": True,
                }
            elif (
                "WAFInvalidParameterException" in error_msg
                and "CLOUDFRONT" in error_msg
            ):
                # CloudFront WAF only available in us-east-1
                return {
                    "data": {
                        "note": "CloudFront WAF scope only available in us-east-1"
                    },
                    "success": True,
                }
            elif "ClusterNotFoundException" in error_msg and service_name == "ecs":
                # No ECS clusters is normal for many accounts
                return {
                    "data": {
                        "note": "No ECS clusters found (normal if account doesn't use ECS)"
                    },
                    "success": True,
                }
            elif "NoSuchTagSet" in error_msg:
                # S3 bucket has no tags - this is normal
                return {
                    "data": {"note": "No tags configured for this resource (normal)"},
                    "success": True,
                }
            elif "NoSuchBucketPolicy" in error_msg:
                # S3 bucket has no policy - this is normal
                return {
                    "data": {"note": "No bucket policy configured (normal)"},
                    "success": True,
                }
            else:
                error_logger.error(
                    f"AWS_COMMAND_FAILED - Service: {service_name}, Command: {command}, ReturnCode: {result.returncode}, Error: {error_msg}"
                )
                return {"error": error_msg, "success": False}

    except subprocess.TimeoutExpired:
        error_msg = "Command timeout after 60 seconds"
        error_logger.error(
            f"TIMEOUT_ERROR - Service: {service_name}, Command: {command}, Error: {error_msg}"
        )
        return {"error": error_msg, "success": False}
    except Exception as e:
        error_msg = f"Failed to execute command: {e!s}"
        error_logger.error(
            f"EXECUTION_ERROR - Service: {service_name}, Command: {command}, Error: {error_msg}\nTraceback: {traceback.format_exc()}"
        )
        return {"error": error_msg, "success": False}


def get_dynamic_commands(service, initial_data, error_logger):
    """Generate additional dynamic commands based on discovered resources"""
    dynamic_commands = []

    try:
        if service == "ecs" and "list-clusters" in initial_data:
            # Get detailed info for each ECS cluster
            clusters_data = initial_data["list-clusters"]
            if "clusterArns" in clusters_data:
                for cluster_arn in clusters_data["clusterArns"]:
                    cluster_name = cluster_arn.split("/")[-1]
                    dynamic_commands.extend(
                        [
                            f"aws ecs describe-clusters --clusters {cluster_name}",
                            f"aws ecs list-services --cluster {cluster_name}",
                            f"aws ecs list-tasks --cluster {cluster_name}",
                        ]
                    )

        elif service == "elbv2" and "describe-load-balancers" in initial_data:
            # Get listeners for each load balancer
            lb_data = initial_data["describe-load-balancers"]
            if "LoadBalancers" in lb_data:
                for lb in lb_data["LoadBalancers"]:
                    lb_arn = lb["LoadBalancerArn"]
                    lb["LoadBalancerName"]
                    dynamic_commands.append(
                        f"aws elbv2 describe-listeners --load-balancer-arn {lb_arn}"
                    )

        elif service == "s3" and "list-buckets" in initial_data:
            # Get detailed info for each S3 bucket
            buckets_data = initial_data["list-buckets"]
            if "Buckets" in buckets_data:
                for bucket in buckets_data["Buckets"][
                    :10
                ]:  # Limit to first 10 buckets to avoid too many calls
                    bucket_name = bucket["Name"]
                    dynamic_commands.extend(
                        [
                            f"aws s3api get-bucket-versioning --bucket {bucket_name}",
                            f"aws s3api get-bucket-encryption --bucket {bucket_name}",
                            f"aws s3api get-bucket-policy --bucket {bucket_name}",
                            f"aws s3api get-bucket-tagging --bucket {bucket_name}",
                        ]
                    )

        elif service == "rds" and "describe-db-instances" in initial_data:
            # Get additional RDS details
            db_instances = initial_data["describe-db-instances"]
            if "DBInstances" in db_instances:
                for db in db_instances["DBInstances"]:
                    db_id = db["DBInstanceIdentifier"]
                    dynamic_commands.extend(
                        [
                            f"aws rds describe-db-log-files --db-instance-identifier {db_id}",
                            f"aws rds list-tags-for-resource --resource-name {db['DBInstanceArn']}",
                        ]
                    )

        elif service == "lambda" and "list-functions" in initial_data:
            # Get detailed Lambda function information
            functions_data = initial_data["list-functions"]
            if "Functions" in functions_data:
                for func in functions_data["Functions"][
                    :20
                ]:  # Limit to avoid too many calls
                    func_name = func["FunctionName"]
                    dynamic_commands.extend(
                        [
                            f"aws lambda get-function --function-name {func_name}",
                            f"aws lambda get-function-configuration --function-name {func_name}",
                            f"aws lambda list-tags --resource {func['FunctionArn']}",
                        ]
                    )

        elif service == "wafv2" and "list-web-acls" in initial_data:
            # Try to get CloudFront WAF ACLs if this account has CloudFront access
            # Note: CloudFront WAF is only available in us-east-1
            try:
                # Check current region first
                region_result = subprocess.run(
                    ["aws", "configure", "get", "region"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                current_region = (
                    region_result.stdout.strip()
                    if region_result.returncode == 0
                    else "us-east-1"
                )

                # Only try CloudFront WAF in us-east-1
                if current_region == "us-east-1":
                    dynamic_commands.append(
                        "aws wafv2 list-web-acls --scope CLOUDFRONT"
                    )

            except Exception:
                # Skip CloudFront WAF if we can't determine region or other issues
                pass

        elif service == "logs" and "describe-log-groups" in initial_data:
            # Get log streams for log groups (limit to first 5 log groups)
            log_groups_data = initial_data["describe-log-groups"]
            if "logGroups" in log_groups_data:
                for log_group in log_groups_data["logGroups"][:5]:
                    log_group_name = log_group["logGroupName"]
                    dynamic_commands.append(
                        f"aws logs describe-log-streams --log-group-name {log_group_name} --max-items 10"
                    )

        elif service == "ec2" and "describe-instances" in initial_data:
            # Get additional details for running instances
            instances_data = initial_data["describe-instances"]
            if "Reservations" in instances_data:
                running_instances = 0
                for reservation in instances_data["Reservations"]:
                    for instance in reservation.get("Instances", []):
                        instance_id = instance.get("InstanceId")
                        if (
                            instance_id
                            and instance.get("State", {}).get("Name") == "running"
                            and running_instances < 5
                        ):
                            dynamic_commands.append(
                                f"aws ec2 describe-instance-status --instance-ids {instance_id}"
                            )
                            running_instances += 1

    except Exception as e:
        error_msg = f"Error generating dynamic commands for {service}: {e}"
        error_logger.error(
            f"DYNAMIC_COMMAND_ERROR - Service: {service}, Error: {error_msg}\nTraceback: {traceback.format_exc()}"
        )
        print(f"      ⚠️  {error_msg}")

    return dynamic_commands


def handle_command_error(error_msg, service, operation):
    """Handle and format known command errors"""
    # Check for JSON decode errors which often indicate empty responses
    if (
        "Invalid JSON response" in error_msg
        and "Expecting value: line 1 column 1" in error_msg
    ):
        # Empty response - treat as informational
        return {
            "data": {"note": "Empty response from AWS (no data available)"},
            "display": "No data available",
            "is_error": False,
        }
    elif "NoSuchEntity" in error_msg and "Password Policy" in error_msg:
        # IAM password policy not existing is normal
        return {
            "data": {"note": "No password policy configured (this is normal)"},
            "display": "No password policy configured",
            "is_error": False,
        }
    elif "InvalidParameterValue" in error_msg and "cache security groups" in error_msg:
        # Cache security groups deprecated in VPC - this is expected
        return {
            "data": {"note": "Cache security groups not available in VPC (expected)"},
            "display": "Cache security groups not available in VPC",
            "is_error": False,
        }
    elif "WAFInvalidParameterException" in error_msg and "CLOUDFRONT" in error_msg:
        # CloudFront WAF only available in us-east-1
        return {
            "data": {"note": "CloudFront WAF scope only available in us-east-1"},
            "display": "CloudFront WAF scope not available in this region",
            "is_error": False,
        }
    elif "NoSuchTagSet" in error_msg:
        # S3 bucket has no tags - this is normal
        return {
            "data": {"note": "No tags configured for this bucket (normal)"},
            "display": "No bucket tags configured",
            "is_error": False,
        }
    elif "NoSuchBucketPolicy" in error_msg:
        # S3 bucket has no policy - this is normal
        return {
            "data": {"note": "No bucket policy configured (normal)"},
            "display": "No bucket policy configured",
            "is_error": False,
        }
    elif "ClusterNotFoundException" in error_msg and service == "ecs":
        # No ECS clusters is normal for many accounts
        return {
            "data": {
                "note": "No ECS clusters found (normal if account doesn't use ECS)"
            },
            "display": "No ECS clusters found",
            "is_error": False,
        }
    elif "ValidationError" in error_msg and (
        "listener ARNs" in error_msg or "load balancer ARN" in error_msg
    ):
        # This error should be handled by moving to dynamic commands
        return {
            "data": {
                "note": "Listeners require load balancer ARN - moved to dynamic discovery"
            },
            "display": "Moved to dynamic discovery",
            "is_error": False,
        }
    else:
        return {"data": None, "display": error_msg, "is_error": True}


def run_infra(account_info, args):
    """
    Main function to run infrastructure resource collection

    Args:
        account_info: Dictionary containing AWS account information
        args: Parsed command line arguments

    Returns:
        Dict containing results and status
    """
    # Setup error logging
    error_logger = setup_error_logging()

    # Create flat storage directory
    storage_dir = aws_utils.create_flat_storage_directory()

    # Load configurations
    accounts_config, commands_config = aws_utils.load_config(include_commands=True)
    ACCOUNT_CONFIGS = accounts_config["account_configs"]
    ALL_COMMANDS = commands_config["commands"]

    # Determine account name to use
    try:
        account_name = aws_utils.determine_account_name(
            account_info, args.account, ACCOUNT_CONFIGS
        )
        if not account_name:
            error_logger.error(
                f"Could not determine account name for account_info: {account_info}, args.account: {args.account}"
            )
            print("❌ Could not determine account name.")
            return {"success": False, "error": "Could not determine account name"}
    except Exception as e:
        error_logger.error(
            f"Failed to determine account name: {e!s}\nTraceback: {traceback.format_exc()}"
        )
        return {"success": False, "error": f"Failed to determine account name: {e!s}"}

    print(f"🎯 Using account name: {account_name}")

    # Get account ID for filename generation
    account_id = account_info["account_id"]

    # Generate descriptive filename: infrastructure_{YYYY-MM}_{account_name}_{account_id}.json
    date_str = datetime.now().strftime("%Y-%m")
    filename = aws_utils.get_flat_storage_filename(
        "infrastructure", date_str, account_name, account_id, args.output
    )
    output_path = os.path.join(storage_dir, filename)

    # Get account configuration using account ID
    if account_id in ACCOUNT_CONFIGS:
        account_config = ACCOUNT_CONFIGS[account_id]
        services_to_query = account_config["services"]
        print(f"✅ Found configuration for account '{account_name}' (ID: {account_id})")
    else:
        print(f"⚠️  Account ID '{account_id}' not found in configuration.")
        print(f"Available account IDs: {', '.join(ACCOUNT_CONFIGS.keys())}")
        print("💡 Using default service set: ec2, s3, iam, lambda, rds")
        print(
            "💡 Please add this account ID to configs/accounts.yaml for full configuration"
        )

        # Use a default set of common services
        services_to_query = ["ec2", "s3", "iam", "lambda", "rds"]
        account_config = {"services": services_to_query}

    # Build the commands map for this account
    commands_map = {}
    for service in services_to_query:
        if service in ALL_COMMANDS:
            commands_map[service] = ALL_COMMANDS[service]
        else:
            print(f"⚠️  Warning: Service '{service}' not found in command definitions")

    final_output = {
        "account": account_name,
        "account_info": account_info,
        "timestamp": datetime.now().isoformat(),
        "services": {},
    }

    print(f"\n🚀 Starting AWS Resource Collection for account: {account_name}")
    print(f"🔧 Services to query: {', '.join(services_to_query)}")
    print(f"📁 Output file: {output_path}")
    print("-" * 60)

    # Process each service
    for service, commands in commands_map.items():
        print(f"📊 Fetching detailed data for: {service}...")

        # Initialize service data structure
        final_output["services"][service] = {
            "summary": {
                "total_commands": 0,
                "successful_commands": 0,
                "failed_commands": 0,
            },
            "data": {},
            "errors": {},
        }

        # Handle both single command (string) and multiple commands (list)
        if isinstance(commands, str):
            commands = [commands]

        # Execute initial commands
        initial_data = {}
        for i, command in enumerate(commands):
            # Extract the operation name from the command for better organization
            command_parts = command.split()
            if len(command_parts) >= 3:
                operation = command_parts[
                    2
                ]  # e.g., "describe-instances" from "aws ec2 describe-instances"
            else:
                operation = f"command_{i + 1}"

            print(f"   🔍 Executing: {operation}...")

            result = execute_aws_command(command, service, error_logger, i)

            if result["success"]:
                final_output["services"][service]["data"][operation] = result["data"]
                initial_data[operation] = result["data"]
                print(f"      ✅ {operation}: Success")
            else:
                # Handle known "expected" errors more gracefully for initial commands too
                error_handling = handle_command_error(
                    result["error"], service, operation
                )

                if error_handling["is_error"]:
                    final_output["services"][service]["errors"][operation] = result[
                        "error"
                    ]
                    error_logger.error(
                        f"OPERATION_FAILED - Service: {service}, Operation: {operation}, Error: {result['error']}"
                    )
                    print(f"      ❌ {operation}: {error_handling['display']}")
                else:
                    final_output["services"][service]["data"][operation] = (
                        error_handling["data"]
                    )
                    print(f"      ℹ️  {operation}: {error_handling['display']}")

        # Generate and execute dynamic commands based on initial results
        dynamic_commands = get_dynamic_commands(service, initial_data, error_logger)
        if dynamic_commands:
            print(
                f"   🔄 Executing {len(dynamic_commands)} dynamic discovery commands..."
            )

            for dynamic_command in dynamic_commands:
                # Extract operation name for dynamic commands
                command_parts = dynamic_command.split()
                if len(command_parts) >= 3:
                    operation = f"{command_parts[2]}-dynamic"
                    if len(command_parts) > 3:
                        # Add resource identifier for better naming
                        resource_id = command_parts[-1].split("/")[
                            -1
                        ]  # Get last part after any slashes
                        operation = f"{command_parts[2]}-{resource_id}"
                else:
                    operation = "dynamic-command"

                result = execute_aws_command(dynamic_command, service, error_logger)

                if result["success"]:
                    final_output["services"][service]["data"][operation] = result[
                        "data"
                    ]
                    print(f"      ✅ {operation}: Success")
                else:
                    # Handle known "expected" errors more gracefully
                    error_handling = handle_command_error(
                        result["error"], service, operation
                    )

                    if error_handling["is_error"]:
                        final_output["services"][service]["errors"][operation] = result[
                            "error"
                        ]
                        error_logger.error(
                            f"DYNAMIC_OPERATION_FAILED - Service: {service}, Operation: {operation}, Command: {dynamic_command}, Error: {result['error']}"
                        )
                        print(f"      ⚠️  {operation}: {error_handling['display']}")
                    else:
                        final_output["services"][service]["data"][operation] = (
                            error_handling["data"]
                        )
                        print(f"      ℹ️  {operation}: {error_handling['display']}")

        # Calculate totals including dynamic commands
        all_operations = len(final_output["services"][service]["data"]) + len(
            final_output["services"][service]["errors"]
        )
        successful_operations = len(final_output["services"][service]["data"])
        failed_operations = len(final_output["services"][service]["errors"])

        final_output["services"][service]["summary"] = {
            "total_commands": all_operations,
            "successful_commands": successful_operations,
            "failed_commands": failed_operations,
        }

        # Service summary
        if successful_operations > 0:
            print(
                f"   📈 {service}: {successful_operations}/{all_operations} operations successful"
            )
            if dynamic_commands:
                print(
                    f"      🔄 Included {len(dynamic_commands)} dynamic discovery operations"
                )
        else:
            print(f"   💥 {service}: All operations failed")

    # Generate comprehensive summary
    total_commands = 0
    successful_commands = 0
    failed_commands = 0
    fully_successful_services = []
    partially_successful_services = []
    failed_services = []

    for service_name, service_data in final_output["services"].items():
        if "summary" in service_data:
            summary = service_data["summary"]
            total_commands += summary["total_commands"]
            successful_commands += summary["successful_commands"]
            failed_commands += summary["failed_commands"]

            if summary["failed_commands"] == 0:
                fully_successful_services.append(service_name)
            elif summary["successful_commands"] > 0:
                partially_successful_services.append(
                    f"{service_name} ({summary['successful_commands']}/{summary['total_commands']})"
                )
            else:
                failed_services.append(service_name)

    # Write to file
    try:
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=4)

        # Log successful completion
        error_logger.info(
            f"Successfully completed AWS resource collection for account: {account_name}"
        )
        error_logger.info(f"Output written to: {output_path}")
        error_logger.info(
            f"Total commands: {total_commands}, Successful: {successful_commands}, Failed: {failed_commands}"
        )
    except Exception as e:
        error_logger.error(
            f"WRITE_ERROR - Failed to write output file {output_path}: {e!s}\nTraceback: {traceback.format_exc()}"
        )
        print(f"❌ Failed to write output file: {e}")
        return {"success": False, "error": f"Failed to write output file: {e}"}

    print("-" * 60)
    print(f"✅ Done! Detailed data for account '{account_name}' saved to {output_path}")
    print("📊 Overall Statistics:")
    print(f"   🎯 Total Commands: {total_commands}")
    print(f"   ✅ Successful: {successful_commands}")
    print(f"   ❌ Failed: {failed_commands}")
    print(f"   📈 Success Rate: {(successful_commands / total_commands * 100):.1f}%")

    print("\n📋 Service Summary:")
    if fully_successful_services:
        print(
            f"✅ Fully successful services ({len(fully_successful_services)}): {', '.join(fully_successful_services)}"
        )

    if partially_successful_services:
        print(
            f"⚠️  Partially successful services ({len(partially_successful_services)}): {', '.join(partially_successful_services)}"
        )

    if failed_services:
        print(
            f"❌ Failed services ({len(failed_services)}): {', '.join(failed_services)}"
        )
        print("💡 Check AWS permissions and service availability")

    # Write error summary to log for AI analysis
    if failed_commands > 0:
        error_logger.info(
            f"ERROR_SUMMARY_START - Account: {account_name}, Failed Commands: {failed_commands}"
        )
        for service_name, service_data in final_output["services"].items():
            if "errors" in service_data:
                for operation, error in service_data["errors"].items():
                    error_logger.info(
                        f"ERROR_DETAIL - Service: {service_name}, Operation: {operation}, Error: {error}"
                    )
        error_logger.info(f"END_ERROR_SUMMARY - Account: {account_name}")

    print("\n📁 File Details:")
    print(f"   📄 Output: {output_path}")
    print(f"   📏 Size: {os.path.getsize(output_path):,} bytes")
    print(f"   🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Print log file location
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "storages", "logs")
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(logs_dir, f"{today_str}.log")
    print("\n📋 Error Log:")
    print(f"   📝 Log file: {log_file}")
    if failed_commands > 0:
        print(f"   ⚠️  {failed_commands} errors logged for AI analysis")
    else:
        print("   ✅ No errors to log")

    return {
        "success": True,
        "output_path": output_path,
        "stats": {
            "total_commands": total_commands,
            "successful_commands": successful_commands,
            "failed_commands": failed_commands,
            "success_rate": (successful_commands / total_commands * 100)
            if total_commands > 0
            else 0,
        },
    }
