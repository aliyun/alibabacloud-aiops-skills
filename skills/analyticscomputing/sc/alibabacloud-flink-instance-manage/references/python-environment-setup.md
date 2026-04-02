# Python Environment Setup Guide

Complete guide for setting up the Python environment for Flink instance operations.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Verify Python Installation](#step-1-verify-python-installation)
- [Step 2: Install Dependencies](#step-2-install-dependencies)
- [Step 3: Configure Authentication](#step-3-configure-authentication)
- [Step 4: Verify Setup](#step-4-verify-setup)
- [Troubleshooting](#troubleshooting)
- [Virtual Environment (Optional)](#virtual-environment-optional)
- [Prepare RAM Identity](#prepare-ram-identity)
- [Security Best Practices](#security-best-practices)
- [Next Steps](#next-steps)

## Prerequisites

- Python 3.6 or higher
- pip (Python package manager)
- Alibaba Cloud credentials available from the default credential chain

---

## Step 1: Verify Python Installation

```bash
# Check Python version (must be 3.6+)
python3 --version
```

**Expected Output:**
```
Python 3.6.0 or higher
```

**If Python is not installed:**

### macOS
```bash
# Using Homebrew
brew install python@3.9
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip
```

### Linux (CentOS/RHEL)
```bash
sudo yum install python3 python3-pip
```

### Windows
Download from https://www.python.org/downloads/

---

## Step 2: Install Dependencies

```bash
# Navigate to the project directory
cd alibabacloud-flink-instance-manage

# Install required packages
pip install -r assets/requirements.txt
```

This installs:
- `alibabacloud-foasconsole20211028>=2.2.1` - Flink OpenAPI SDK
- `alibabacloud-tea-openapi>=0.4.3` - OpenAPI client
- `alibabacloud-tea-util>=0.3.14` - Utility library

**Verify installation:**
```bash
pip show alibabacloud-foasconsole20211028
```

---

## Step 3: Configure Authentication

### Method 1: Default Aliyun CLI Profile

Use the default profile once, then let the SDK resolve credentials from the
default credential chain automatically:

```bash
aliyun configure
aliyun configure list
```

### Method 2: RAM Role (Recommended on Alibaba Cloud runtime)

When running on ECS/ACK/FC/SAE with a RAM role attached, credentials are
automatically retrieved from role metadata. No AK/SK export is needed.

---

## Step 4: Verify Setup

```bash
# Test the script
python scripts/instance_ops.py describe_regions
```

**Expected Output:**
```json
{
  "success": true,
  "operation": "describe_regions",
  "data": {
    "Regions": {
      "Region": [
        {
          "RegionId": "cn-hangzhou",
          ...
        }
      ]
    }
  },
  "request_id": "..."
}
```

---

## Troubleshooting

### Issue: Python version too low

**Symptom:**
```
Python 3.5.2
# or lower
```

**Solution:**
Upgrade Python to 3.6 or higher using your system's package manager.

### Issue: Module not found

**Symptom:**
```
ModuleNotFoundError: No module named 'alibabacloud_foasconsole20211028'
```

**Solution:**
```bash
pip install -r assets/requirements.txt
```

### Issue: Missing credentials

**Symptom:**
```
NoCredentialError: unable to resolve credentials from default credential chain
```

**Solution:**
```bash
aliyun configure
aliyun configure list
```

### Issue: Permission denied

**Symptom:**
```
Forbidden.RAM: Insufficient permissions
```

**Solution:**
1. Check RAM user permissions according to the RAM policy document
2. Attach required policies to the RAM user
3. Verify the RAM identity is active and authorized

### Issue: pip not found

**Symptom:**
```
bash: pip: command not found
```

**Solution:**
```bash
# Use pip3 instead
pip3 install -r assets/requirements.txt

# Or install pip
sudo apt-get install python3-pip  # Ubuntu/Debian
sudo yum install python3-pip      # CentOS/RHEL
```

---

## Virtual Environment (Optional)

For isolated dependencies, use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r assets/requirements.txt

# Deactivate when done
deactivate
```

---

## Prepare RAM Identity

1. Log in to Alibaba Cloud Console: https://ram.console.aliyun.com/
2. Create or select a RAM identity (user/role) with required policies
3. Prefer temporary credentials via RAM role when possible
4. If using a local profile, configure it once with `aliyun configure`
5. Verify permissions with the RAM policy document

---

## Security Best Practices

1. **Never commit credentials** - Never hardcode AK/SK in code or scripts
2. **Use RAM users** - Don't use the root account for daily operations
3. **Rotate AccessKeys regularly** - Every 90 days recommended
4. **Principle of least privilege** - Grant only necessary permissions
5. **Use RAM roles/default chain** - Prefer temporary credentials over explicit AK/SK handling

---

## Next Steps

After setup:
1. Read `SKILL.md` in the project root for usage documentation
2. Try the quick start examples in the quick-start document
3. Review RAM policy requirements before production use
