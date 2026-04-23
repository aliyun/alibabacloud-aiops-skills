# MaxFrame Installation Guide

This guide provides step-by-step instructions for installing and configuring MaxFrame for distributed data processing on MaxCompute.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Dependencies](#dependencies)
- [Environment Configuration](#environment-config)
  - [Required Environment Variables](#required-environment-variables)
  - [Setting Environment Variables](#setting-environment-variables)
  - [Find Your MaxCompute Endpoint](#find-your-maxcompute-endpoint)
- [Installation Verification](#installation-verification)
- [Session Setup](#session-setup)
  - [Manual Session Creation](#manual-session-creation)
  - [Auto-Detect from Environment](#auto-detect-from-environment)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Getting Help](#getting-help)
- [Next Steps](#next-steps)
- [Cleanup](#cleanup)

## Prerequisites

- Python 3.7 or higher
- MaxCompute (ODPS) account with valid credentials
- Access to a MaxCompute project

## Dependencies

Install the required Python packages:

```bash
pip install maxframe -U
```

The required packages are:

- **maxframe** - MaxFrame SDK for distributed data processing
- **pyodps** - ODPS Python SDK for MaxCompute access
- **pandas** - Data manipulation library (for pandas-compatible APIs)

## Environment Configuration

### Required Environment Variables

Configure the following environment variables to authenticate with MaxCompute:

| Variable | Description |
|----------|-------------|
| `ODPS_ACCESS_ID` | MaxCompute access ID (username) |
| `ODPS_ACCESS_KEY` | MaxCompute access key (password) |
| `ODPS_PROJECT` | MaxCompute project name |
| `ODPS_ENDPOINT` | MaxCompute endpoint URL |

### Setting Environment Variables

#### Option 1: Set in Shell

```bash
export ODPS_ACCESS_ID="your_access_id"
export ODPS_ACCESS_KEY="your_access_key"
export ODPS_PROJECT="your_project_name"
export ODPS_ENDPOINT="your_endpoint"
```

#### Option 2: Use .env File

Create a `.env` file in your project directory:

```env
ODPS_ACCESS_ID=your_access_id
ODPS_ACCESS_KEY=your_access_key
ODPS_PROJECT=your_project_name
ODPS_ENDPOINT=your_endpoint
```

Then load the environment variables in Python:

```python
from dotenv import load_dotenv

load_dotenv()
```

### Find Your MaxCompute Endpoint

MaxCompute endpoints vary by region, check the [MaxCompute documentation](https://www.alibabacloud.com/help/zh/maxcompute/user-guide/endpoints?spm=a2c63.p38356.help-menu-search-27797.d_0) for the correct endpoint for your region.

## Installation Verification

Verify your installation by running the following Python script:

```python
import os
from dotenv import load_dotenv
from odps import ODPS
from maxframe.session import new_session

# Load environment variables
load_dotenv()

# Create ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Create MaxFrame session
session = new_session(o)

print("MaxFrame installation verified successfully!")
print(f"Connected to project: {o.project}")

# Destroy session when done
session.destroy()
```

## Session Setup

### Manual Session Creation

Create a session with explicit credentials:

```python
import os
import maxframe.dataframe as md
from maxframe.session import new_session
from odps import ODPS

# Create ODPS connection
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Create MaxFrame session
session = new_session(o)
```

### Auto-Detect from Environment

In environments like DataWorks or MaxCompute Notebook, ODPS credentials are automatically available:

```python
from maxframe.session import new_session

# Auto-detects ODPS from environment
session = new_session()
```


## Troubleshooting

### Common Issues

#### Issue: Connection Authentication Failed

**Symptoms**: Error message indicating invalid credentials or authentication failure.

**Solutions**:
- Verify all environment variables are set correctly
- Check that your access key has not expired
- Ensure you have the correct endpoint for your region
- Verify your project name is accurate

```bash
# Test environment variables
echo $ODPS_ACCESS_ID
echo $ODPS_PROJECT
echo $ODPS_ENDPOINT
```

#### Issue: Package Installation Fails

**Symptoms**: `pip install` fails with dependency conflicts or permission errors.

**Solutions**:
- Use a virtual environment to isolate dependencies:

```bash
python -m venv maxframe_env
source maxframe_env/bin/activate  # On Windows: maxframe_env\Scripts\activate
pip install maxframe pyodps pandas --prefer-binary
```

- Upgrade pip before installing:

```bash
pip install --upgrade pip
pip install maxframe pyodps pandas --prefer-binary
```

#### Issue: Session Creation Fails

**Symptoms**: `new_session()` raises an exception.

**Solutions**:
- Verify network connectivity to the MaxCompute endpoint
- Check firewall rules allow outbound connections
- Ensure your MaxCompute account has the necessary permissions
- Try the auto-detect method if available in your environment
- Use VPC endpoint if you are in vpc networking

#### Issue: Lazy Execution Not Working

**Symptoms**: Operations appear to do nothing until `.execute()` is called.

**Note**: This is expected behavior. MaxFrame uses lazy execution. Always call `.execute()` to trigger computation:

```python
# This does not execute immediately
result = df.groupby('category').sum()

# Execute the computation
result.execute()
```

### Getting Help

If you encounter issues not covered here:

1. Check the [MaxFrame Documentation](https://maxframe.readthedocs.io/en/latest/)
2. Review the [MaxFrame Client Repository](https://github.com/aliyun/alibabacloud-odps-maxframe-client.git)
3. Consult the sample code in `assets/examples/` for working examples
4. Contact your MaxCompute administrator for account-specific issues

## Next Steps

After successful installation:

1. Review the [MaxFrame Context Guide](maxframe-context.md) for comprehensive feature documentation
2. Explore the [sample code](../assets/examples/) for working examples
3. Start building your first MaxFrame program using the [Common Workflow](../SKILL.md#common-workflow)

## Cleanup

Destroy your session when done to free resources:

```python
session.destroy()
```