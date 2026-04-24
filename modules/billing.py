#!/usr/bin/env python3
"""
AWS Billing Data Collection Module

This module collects AWS billing data from accounts using AWS Cost Explorer
and saves the data to JSON files organized by month and account.
"""

import calendar
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

    return logging.getLogger("aws_billing_module")


def execute_aws_command(command, command_name, error_logger=None):
    """Execute a single AWS command and return the result"""
    try:
        # Run the command and capture output
        result = subprocess.run(
            shlex.split(command), capture_output=True, text=True, timeout=120
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
                error_msg = f"Invalid JSON response for {command_name}: {e!s}"
                if error_logger:
                    error_logger.error(
                        f"JSON_DECODE_ERROR - Command: {command_name}, AWS_Command: {command}, Error: {error_msg}\nStdout: {result.stdout[:500]}..."
                    )
                return {"error": error_msg, "success": False}
        else:
            # Handle known "expected" errors more gracefully
            error_msg = result.stderr.strip()

            # Apply same error categorization as infra module
            if "InvalidParameterValue" in error_msg and "time period" in error_msg:
                # Cost Explorer time period issues are common
                return {
                    "data": {
                        "note": "No billing data available for specified time period"
                    },
                    "success": True,
                }
            elif "AccessDeniedException" in error_msg and "ce:" in error_msg:
                # Cost Explorer permissions missing
                return {
                    "data": {
                        "note": "Cost Explorer access not enabled (normal for many accounts)"
                    },
                    "success": True,
                }
            elif "ValidationException" in error_msg and "granularity" in error_msg:
                # Cost Explorer granularity validation issues
                return {
                    "data": {
                        "note": "Invalid granularity for time period (expected for short ranges)"
                    },
                    "success": True,
                }
            else:
                if error_logger:
                    error_logger.error(
                        f"AWS_BILLING_COMMAND_FAILED - Command: {command_name}, AWS_Command: {command}, ReturnCode: {result.returncode}, Error: {error_msg}"
                    )
                return {"error": error_msg, "success": False}

    except subprocess.TimeoutExpired:
        error_msg = "Command timeout after 120 seconds"
        if error_logger:
            error_logger.error(
                f"BILLING_TIMEOUT_ERROR - Command: {command_name}, AWS_Command: {command}, Error: {error_msg}"
            )
        return {"error": error_msg, "success": False}
    except Exception as e:
        error_msg = f"Failed to execute command: {e!s}"
        if error_logger:
            error_logger.error(
                f"BILLING_EXECUTION_ERROR - Command: {command_name}, AWS_Command: {command}, Error: {error_msg}\nTraceback: {traceback.format_exc()}"
            )
        return {"error": error_msg, "success": False}


def run_billing(account_info, args):
    """
    Main function to run billing data collection

    Args:
        account_info: Dictionary containing AWS account information
        args: Parsed command line arguments including month

    Returns:
        Dict containing results and status
    """
    # Setup error logging
    error_logger = setup_error_logging()

    # Load configuration
    accounts_config = aws_utils.load_config(include_commands=False)
    ACCOUNT_CONFIGS = accounts_config["account_configs"]

    # Determine the target month
    if hasattr(args, "month") and args.month:
        try:
            target_month = datetime.strptime(args.month, "%Y-%m")
        except ValueError:
            print("Error: Month format must be YYYY-MM (e.g., 2026-03)")
            return {"success": False, "error": "Invalid month format"}
    else:
        target_month = datetime.now().replace(day=1)  # First day of current month

    # Calculate start and end dates for the month
    start_date = target_month.strftime("%Y-%m-01")
    # Last day of the month
    _, last_day = calendar.monthrange(target_month.year, target_month.month)
    end_date = target_month.strftime(f"%Y-%m-{last_day:02d}")

    # Determine account name to use (auto-detect if not provided)
    account_to_lookup = args.account if args.account else account_info["account_id"]
    aws_utils.determine_account_name(
        account_info, args.account, ACCOUNT_CONFIGS
    )

    # Get account configuration using the determined account
    account_found, _account_config, found_account_id = aws_utils.find_account_config(
        account_to_lookup, ACCOUNT_CONFIGS
    )

    if not account_found:
        error_msg = f"Account '{account_to_lookup}' not found in configuration."
        print(f"Error: {error_msg}")

        # Get list of available account names
        account_names = [
            config.get("name")
            for config in ACCOUNT_CONFIGS.values()
            if config.get("name")
        ]
        print(f"Available account names: {', '.join(account_names)}")
        print(f"Available account IDs: {', '.join(ACCOUNT_CONFIGS.keys())}")
        return {"success": False, "error": error_msg}

    # Get the account name (not ID) for consistent filename
    account_name = aws_utils.get_account_name_by_id(ACCOUNT_CONFIGS, found_account_id)

    # Create flat storage directory: storages/aws/
    storage_dir = aws_utils.create_flat_storage_directory()

    # Generate descriptive filename: billing_{YYYY-MM}_{account_name}_{account_id}.json
    date_str = target_month.strftime("%Y-%m")
    filename = aws_utils.get_flat_storage_filename(
        "billing", date_str, account_name, found_account_id, args.output
    )
    output_path = os.path.join(storage_dir, filename)

    # Define billing commands
    billing_commands = {
        "monthly_cost_by_service": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE",
        "monthly_cost_by_region": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=REGION",
        "monthly_cost_by_service_and_region": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE Type=DIMENSION,Key=REGION",
        "daily_cost_trend": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity DAILY --metrics UnblendedCost",
        "cost_by_usage_type": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=USAGE_TYPE",
        "cost_by_instance_type": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=INSTANCE_TYPE",
        "rightsizing_recommendations": "aws ce get-rightsizing-recommendation --service AmazonEC2",
        "cost_by_linked_account": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=LINKED_ACCOUNT",
        "cost_by_operation": f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity MONTHLY --metrics UnblendedCost --group-by Type=DIMENSION,Key=OPERATION",
    }

    # Add conditional commands that depend on date ranges (only for past months)
    current_date = datetime.now()
    if target_month < current_date.replace(day=1):  # Only for past months
        billing_commands.update(
            {
                "ri_coverage": f"aws ce get-reservation-coverage --time-period Start={start_date},End={end_date}",
                "ri_utilization": f"aws ce get-reservation-utilization --time-period Start={start_date},End={end_date}",
                "savings_plans_coverage": f"aws ce get-savings-plans-coverage --time-period Start={start_date},End={end_date}",
                "savings_plans_utilization": f"aws ce get-savings-plans-utilization --time-period Start={start_date},End={end_date}",
            }
        )

    # Initialize output structure
    final_output = {
        "account": account_name,
        "billing_period": {
            "start_date": start_date,
            "end_date": end_date,
            "month": target_month.strftime("%Y-%m"),
        },
        "timestamp": datetime.now().isoformat(),
        "billing_data": {},
        "summary": {
            "total_commands": len(billing_commands),
            "successful_commands": 0,
            "failed_commands": 0,
        },
        "errors": {},
    }

    print(f"\n💰 Starting AWS Billing Collection for account: {account_name}")
    print(f"📅 Billing period: {start_date} to {end_date}")
    print(f"📁 Output file: {output_path}")
    print("-" * 60)

    # Execute billing commands
    successful_commands = 0
    failed_commands = 0

    for command_name, command in billing_commands.items():
        print(f"💳 Fetching billing data: {command_name}...")

        result = execute_aws_command(command, command_name, error_logger)

        if result["success"]:
            final_output["billing_data"][command_name] = result["data"]
            successful_commands += 1
            print(f"   ✅ {command_name}: Success")

            # Add some summary information for key metrics
            if (
                command_name == "monthly_cost_by_service"
                and "ResultsByTime" in result["data"]
            ):
                total_cost = 0
                for time_period in result["data"]["ResultsByTime"]:
                    if (
                        "Total" in time_period
                        and "UnblendedCost" in time_period["Total"]
                    ):
                        try:
                            cost = float(
                                time_period["Total"]["UnblendedCost"]["Amount"]
                            )
                            total_cost += cost
                        except (ValueError, KeyError):
                            pass
                final_output["billing_data"][command_name]["total_monthly_cost"] = (
                    total_cost
                )
                print(f"      💰 Total monthly cost: ${total_cost:.2f}")

        else:
            error_msg = result["error"]
            final_output["errors"][command_name] = error_msg
            failed_commands += 1

            # Handle common billing-specific errors gracefully
            if "AccessDenied" in error_msg or "UnauthorizedOperation" in error_msg:
                print(
                    f"   🔒 {command_name}: Access denied - check Cost Explorer permissions"
                )
            elif "InvalidParameterValue" in error_msg:
                print(f"   ⚠️  {command_name}: Invalid parameter - {error_msg}")
            elif "OptInRequired" in error_msg:
                print(f"   📝 {command_name}: Feature requires opt-in - {error_msg}")
            elif (
                "ValidationException" in error_msg
                and "end date past the beginning" in error_msg
            ):
                print(
                    f"   📅 {command_name}: Date range issue (future month data not available)"
                )
            elif "There is no available data" in error_msg:
                print(
                    f"   📊 {command_name}: No data available for the requested time period"
                )
            elif "the following arguments are required" in error_msg:
                print(f"   ⚙️  {command_name}: Command parameter issue - {error_msg}")
            else:
                print(f"   ❌ {command_name}: {error_msg}")

    # Update summary
    final_output["summary"]["successful_commands"] = successful_commands
    final_output["summary"]["failed_commands"] = failed_commands

    # Write to file
    try:
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=4)
    except Exception as e:
        error_msg = f"Failed to write output file: {e}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

    # Generate comprehensive summary
    print("-" * 60)
    print(f"✅ Done! Billing data for account '{account_name}' saved to {output_path}")
    print("📊 Overall Statistics:")
    print(f"   🎯 Total Commands: {final_output['summary']['total_commands']}")
    print(f"   ✅ Successful: {successful_commands}")
    print(f"   ❌ Failed: {failed_commands}")
    print(
        f"   📈 Success Rate: {(successful_commands / final_output['summary']['total_commands'] * 100):.1f}%"
    )

    print("\n📋 Billing Summary:")
    if successful_commands > 0:
        print(f"✅ Successfully collected {successful_commands} billing metrics")

        # Show top services by cost if data is available
        if "monthly_cost_by_service" in final_output["billing_data"]:
            billing_data = final_output["billing_data"]["monthly_cost_by_service"]
            if "ResultsByTime" in billing_data:
                print("\n💰 Cost Breakdown by Service (Top 5):")
                services_cost = []

                for time_period in billing_data["ResultsByTime"]:
                    for group in time_period.get("Groups", []):
                        service_name = group.get("Keys", ["Unknown"])[0]
                        try:
                            cost = float(
                                group.get("Metrics", {})
                                .get("UnblendedCost", {})
                                .get("Amount", 0)
                            )
                            services_cost.append((service_name, cost))
                        except (ValueError, KeyError):
                            pass

                # Sort by cost and show top 5
                services_cost.sort(key=lambda x: x[1], reverse=True)
                for service, cost in services_cost[:5]:
                    if cost > 0:
                        print(f"   💸 {service}: ${cost:.2f}")

    if failed_commands > 0:
        print(f"❌ Failed to collect {failed_commands} billing metrics")
        print("💡 Check AWS Cost Explorer permissions and service availability")

    print("\n📁 File Details:")
    print(f"   📄 Output: {output_path}")
    print(f"   📏 Size: {os.path.getsize(output_path):,} bytes")
    print(f"   🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return {
        "success": True,
        "output_path": output_path,
        "stats": {
            "total_commands": final_output["summary"]["total_commands"],
            "successful_commands": successful_commands,
            "failed_commands": failed_commands,
            "success_rate": (
                successful_commands / final_output["summary"]["total_commands"] * 100
            )
            if final_output["summary"]["total_commands"] > 0
            else 0,
        },
        "billing_period": {
            "start_date": start_date,
            "end_date": end_date,
            "month": target_month.strftime("%Y-%m"),
        },
    }
