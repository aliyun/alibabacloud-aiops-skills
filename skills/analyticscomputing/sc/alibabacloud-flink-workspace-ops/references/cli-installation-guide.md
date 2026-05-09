# CLI Installation Guide

This document provides instructions for installing required CLI tools for the alibabacloud-flink-workspace-ops skill.

## Prerequisites

The alibabacloud-flink-workspace-ops skill requires Python and pip to be installed on your system.

## Installation Steps

1. **Clone or download the project:**
   ```bash
   git clone <repository-url>
   cd alibabacloud-flink-workspace-ops
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python scripts/flink_ververica_ops.py --help
   ```

## Required Dependencies

The project requires the following Python packages:
- alibabacloud-ververica20220718>=1.0.0
- alibabacloud-tea-openapi>=0.4.3
- alibabacloud-tea-util>=0.3.14

## Alibaba Cloud CLI (Optional but Recommended)

While the skill uses direct Python SDK calls, you may also want to install the Alibaba Cloud CLI for other operations:

```bash
# Download and install the Alibaba Cloud CLI
curl -fsSL https://aliyuncli.alicdn.com/install.sh | bash

# Verify installation (version should be >= 3.3.1)
aliyun version
```

## Environment Setup

1. Set up your Alibaba Cloud credentials:
   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
   ```

2. You can add these to your shell profile (e.g., ~/.bashrc or ~/.zshrc) to persist across sessions:
   ```bash
   echo 'export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id' >> ~/.bashrc
   echo 'export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret' >> ~/.bashrc
   source ~/.bashrc
   ```

## Configuration for OAuth Mode (Alternative)

If you prefer to use OAuth mode instead of Access Keys:

```bash
aliyun configure --mode OAuth
```

## Troubleshooting

If you encounter issues:

1. **Missing dependencies:** Ensure all packages in requirements.txt are installed
2. **Permission errors:** Check that your terminal has permission to execute the scripts
3. **Credentials not recognized:** Verify that environment variables are properly set
4. **Python version compatibility:** The tool requires Python 3.6 or higher

## Verification

After installation, verify the setup with:

```bash
python scripts/flink_ververica_ops.py list_deployments -w <workspace> -n <namespace> -r <region> -o table
```