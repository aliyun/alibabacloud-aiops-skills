# Tablestore CLI Installation Guide

Official Documentation: https://help.aliyun.com/zh/tablestore/developer-reference/tablestore-cli

Tablestore CLI is the official command-line tool for Alibaba Cloud Tablestore, providing simple and convenient management commands. It supports Windows, Linux, and macOS platforms.

---

## Download

Select the appropriate installation package based on your operating system and architecture:

| Platform | Architecture | Download Link |
|----------|-------------|----------------|
| Windows | x86_64 | [Download Page](https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli) |
| Linux | AMD64 | [Download Page](https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli) |
| Linux | ARM64 | [Download Page](https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli) |
| macOS | AMD64 | [Download Page](https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli) |
| macOS | ARM64 | [Download Page](https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli) |

> Visit the official download page to get the direct download link for the latest version:
> https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli

---

## Installation

### Linux / macOS

```bash
# Extract after download (using Linux AMD64 as an example, filename may vary)
tar xzvf tablestore-cli-linux-amd64.tar.gz

# Move to PATH directory
sudo mv ./ts /usr/local/bin/

# Verify installation
ts --version
```

### macOS (ARM64)

```bash
tar xzvf tablestore-cli-darwin-arm64.tar.gz
sudo mv ./ts /usr/local/bin/
ts --version
```

### Windows

Extract the downloaded `.zip` file, add the directory containing `ts.exe` to the system `PATH` environment variable, then run in Command Prompt:

```cmd
ts --version
```

---

## Configure Access Information

After starting Tablestore CLI, configure the OTS instance access information:

```bash
ts
```

After entering interactive mode, execute the configuration command:

```
# Configure endpoint
config --endpoint https://<instance-name>.<region>.ots.aliyuncs.com
# or
config --endpoint https://ots-<region>-inner.aliyuncs.com

# Configure AccessKey
config --id <access-key-id> --key <access-key-secret>

# Configure instance name
config --instance <instance-name>
```

Or specify directly via startup parameters:

```bash
ts --endpoint https://ots-<region>-inner.aliyuncs.com \
   --instance <instance-name> \
   --id <access-key-id> \
   --key <access-key-secret>
```

> **Security Tip:** Do not save AK/SK in plain text in command history or scripts. It is recommended to use environment variables or configuration files.

---

## Common Commands Quick Reference

After entering Tablestore CLI interactive mode, you can use the following commands:

### Instance and Table Operations

```bash
# List all tables
list

# View table structure
describe -t <table-name>

# Create table
create -t <table-name> -p <primary-key-schema>
```

### Data Operations

```bash
# Write data
put -t <table-name> -r <row-data>

# Read data
get -t <table-name> -r <primary-key>

# Scan data
scan -t <table-name> -n <count>
```

### View Help

```bash
# View all commands
help

# View help for specific command
help <command>
```

---

## Reference Links

- Official Documentation: https://help.aliyun.com/zh/tablestore/developer-reference/tablestore-cli
- Download Page: https://help.aliyun.com/zh/tablestore/developer-reference/download-the-tablestore-cli
- Startup Configuration: https://help.aliyun.com/zh/tablestore/developer-reference/tablestore-cli/start-and-configure-access-information
