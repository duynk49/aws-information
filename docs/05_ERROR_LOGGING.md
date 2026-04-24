# AWS Error Logging System

## Overview

The AWS error logging system captures, categorizes, and structures all errors from the `aws.py` script into daily log files for easy analysis and AI-assisted troubleshooting.

## Log File Structure

### Location
```
storages/logs/YYYY-MM-DD.log
```

### Examples
```
storages/logs/2026-04-20.log  # Today's errors
storages/logs/2026-04-21.log  # Tomorrow's errors
```

## Error Categories

The logging system categorizes errors to help identify root causes:

| Category | Description | Common Causes |
|----------|-------------|---------------|
| `AWS_COMMAND_FAILED` | AWS CLI command returned non-zero exit code | Missing permissions, invalid parameters, service unavailable |
| `JSON_DECODE_ERROR` | Failed to parse AWS CLI JSON response | Malformed output, encoding issues, unexpected response format |
| `TIMEOUT_ERROR` | Command exceeded 60-second timeout | Network issues, large data sets, slow AWS API responses |
| `EXECUTION_ERROR` | General command execution failure | System errors, missing dependencies, process issues |
| `DYNAMIC_COMMAND_ERROR` | Failed to generate dynamic commands | Logic errors, missing resource data, API changes |
| `OPERATION_FAILED` | AWS API operation failure | Service-specific errors, resource constraints |
| `WRITE_ERROR` | Failed to write output files | Disk space, permissions, file system issues |

## Log Format

### Standard Entry Format
```
2026-04-20 10:30:45,123 - ERROR - aws_script - CATEGORY - Details
```

### Example Entries
```
2026-04-20 10:30:45,123 - ERROR - aws_script - AWS_COMMAND_FAILED - Service: wafv2, Command: aws wafv2 list-web-acls --scope CLOUDFRONT, ReturnCode: 254, Error: WAFInvalidParameterException: CLOUDFRONT scope is only valid in us-east-1

2026-04-20 10:31:02,456 - ERROR - aws_script - JSON_DECODE_ERROR - Service: ec2, Command: aws ec2 describe-instances, Error: Invalid JSON response for ec2: Expecting ',' delimiter: line 1 column 43 (char 42)

2026-04-20 10:31:15,789 - ERROR - aws_script - TIMEOUT_ERROR - Service: s3, Command: aws s3api list-buckets, Error: Command timeout after 60 seconds
```

## AI Analysis Summary

At the end of each run, the system generates a structured summary specifically designed for AI analysis:

```
================================================================================
ERROR SUMMARY FOR AI ANALYSIS:
================================================================================
Account: demo-company-prod
Total Failed Commands: 8/67
Failed Services: wafv2, elasticache
Partially Failed Services: s3 (4/6), lambda (12/15)

SERVICE_ERRORS - wafv2:
  - list-web-acls: WAFInvalidParameterException: CLOUDFRONT scope only available in us-east-1
  - describe-web-acl: InvalidParameterValue: Invalid scope value

SERVICE_ERRORS - elasticache:
  - describe-cache-security-groups: InvalidParameterValue: Use of cache security groups is not permitted in this API version for your account
  - describe-cache-subnet-groups: AccessDenied: User is not authorized to perform this operation

SERVICE_ERRORS - s3:
  - get-bucket-policy-dynamic-bucket1: NoSuchBucketPolicy: The bucket policy does not exist
  - get-bucket-encryption-dynamic-bucket2: ServerSideEncryptionConfigurationNotFoundError: The server side encryption configuration was not found
================================================================================
END ERROR SUMMARY
================================================================================
```

## Common Error Patterns & Solutions

### Permission Issues
**Pattern**: `AccessDenied`, `UnauthorizedOperation`, `Forbidden`
**Solution**: Check IAM policies and ensure proper permissions for the service

### Regional Service Limitations
**Pattern**: `CLOUDFRONT scope only available in us-east-1`
**Solution**: Switch to us-east-1 region or skip CloudFront-specific operations

### Deprecated Features
**Pattern**: `Use of cache security groups is not permitted`
**Solution**: Update to VPC-based security groups for ElastiCache

### Missing Resources
**Pattern**: `NoSuchBucketPolicy`, `NoSuchEntity`
**Solution**: Handle as expected behavior (resources may not exist)

## Usage Workflow

### 1. Run AWS Script
```bash
./aws.py --account your-account --skip-login
```

### 2. Check for Errors
If errors occur, the script will:
- Display errors in console
- Write structured logs to `storages/logs/YYYY-MM-DD.log`
- Generate AI analysis summary

### 3. Review Log File
```bash
# View today's errors
cat storages/logs/$(date +%Y-%m-%d).log

# Search for specific error types
grep "AWS_COMMAND_FAILED" storages/logs/$(date +%Y-%m-%d).log
grep "SERVICE_ERRORS" storages/logs/$(date +%Y-%m-%d).log
```

### 4. AI Analysis
Share the log file or specific error summary section with AI for:
- Root cause analysis
- Specific fix recommendations
- Permission troubleshooting
- Configuration improvements

## Integration with AI Tools

### Log File Sharing
```bash
# Get today's log file path
echo "storages/logs/$(date +%Y-%m-%d).log"

# Copy error summary for AI
grep -A 100 "ERROR SUMMARY FOR AI ANALYSIS" storages/logs/$(date +%Y-%m-%d).log
```

### Prompt Templates for AI

**For General Error Analysis:**
```
Please analyze these AWS script errors and suggest fixes:

[Paste log contents or error summary]
```

**For Permission Issues:**
```
I'm getting AWS permission errors. Please help me identify the missing IAM permissions:

[Paste relevant log entries]
```

**For Service-Specific Issues:**
```
I'm having issues with [SERVICE_NAME]. Please help troubleshoot:

[Paste service-specific errors from log]
```

## Configuration Options

### Log Level
Currently set to `ERROR` level. To change:

```python
logging.basicConfig(
    level=logging.INFO,  # Change to INFO, DEBUG, WARNING as needed
    # ... other config
)
```

### Log Retention
Logs are kept indefinitely. To implement rotation:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## Troubleshooting the Logging System

### Log File Not Created
- Check directory permissions for `storages/logs/`
- Verify disk space availability
- Ensure script has write permissions

### Missing Error Information
- Check that error_logger is properly initialized
- Verify exception handling blocks are catching errors
- Review log level configuration

### Log File Too Large
- Implement log rotation (see Configuration Options)
- Filter out verbose errors if needed
- Consider separate log files per service

## Best Practices

1. **Regular Review**: Check logs daily for patterns
2. **AI Integration**: Use structured summaries for efficient AI analysis
3. **Permission Audits**: Use access denied errors to improve IAM policies
4. **Service Monitoring**: Track which services consistently fail
5. **Historical Analysis**: Compare logs across dates to identify trends

## File Integration

The error logging system is integrated into:
- `aws.py` - Main script with logging calls
- `storages/logs/` - Daily log files
- This documentation file

For modifications, update the `setup_error_logging()` function and related error handling blocks in `aws.py`.
