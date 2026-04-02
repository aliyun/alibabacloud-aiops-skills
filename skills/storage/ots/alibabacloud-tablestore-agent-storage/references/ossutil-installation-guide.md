# ossutil Installation Guide

Official documentation: https://help.aliyun.com/zh/oss/developer-reference/ossutil-overview/

ossutil is the official command-line management tool for Alibaba Cloud Object Storage Service (OSS). It supports file upload, download, sync, and other operations. **ossutil 2.0** (current version 2.2.1) is recommended.

---

## Installation

### Linux

**Step 1: Install unzip utility**

```bash
# Alibaba Cloud Linux / CentOS
sudo yum install -y unzip

# Ubuntu / Debian
sudo apt install -y unzip
```

**Step 2: Download and install ossutil**

```bash
# Linux x86_64 (recommended)
curl -o ossutil-linux-amd64.zip https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-amd64.zip
unzip ossutil-linux-amd64.zip
cd ossutil-2.2.1-linux-amd64
chmod 755 ossutil
sudo mv ossutil /usr/local/bin/ && sudo ln -s /usr/local/bin/ossutil /usr/bin/ossutil
```

```bash
# Linux ARM64
curl -o ossutil-linux-arm64.zip https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-arm64.zip
unzip ossutil-linux-arm64.zip
cd ossutil-2.2.1-linux-arm64
chmod 755 ossutil
sudo mv ossutil /usr/local/bin/
```

Or use the one-click installation script (ossutil 1.x):

```bash
sudo -v ; curl https://gosspublic.alicdn.com/ossutil/install.sh | sudo bash
```

**Step 3: Verify installation**

```bash
ossutil
```

If the help information is displayed, the installation was successful.

---

### macOS

```bash
# macOS ARM64 (Apple Silicon)
curl -o ossutil-mac-arm64.zip https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-mac-arm64.zip
unzip ossutil-mac-arm64.zip
cd ossutil-2.2.1-mac-arm64
chmod 755 ossutil
sudo mv ossutil /usr/local/bin/
```

```bash
# macOS x86_64 (Intel)
curl -o ossutil-mac-amd64.zip https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-mac-amd64.zip
unzip ossutil-mac-amd64.zip
cd ossutil-2.2.1-mac-amd64
chmod 755 ossutil
sudo mv ossutil /usr/local/bin/
```

Verify:

```bash
ossutil
```

---

### Windows

1. Download the installation package for your system architecture:
   - x86_64: `ossutil-2.2.1-windows-amd64.zip`
   - x86_32: `ossutil-2.2.1-windows-386.zip`

   Download URL: https://help.aliyun.com/zh/oss/developer-reference/ossutil-overview/

2. Extract the `.zip` file to a target folder (e.g., `C:\ossutil`)
3. Copy the extracted folder path and add it to the system `PATH` environment variable
4. Open Command Prompt to verify:

```cmd
ossutil
```

---

## Configure Credentials

```bash
ossutil config
```

Follow the prompts to enter:

| Parameter | Description | Example |
|-----------|-------------|---------|
| Config file path | Default `~/.ossutilconfig`, press Enter to use default | |
| Language | `CH` (Chinese) or `EN` (English) | `CH` |
| Endpoint | The endpoint of the region where the Bucket is located | `https://oss-cn-hangzhou.aliyuncs.com` |
| AccessKey ID | Alibaba Cloud AccessKey ID | |
| AccessKey Secret | Alibaba Cloud AccessKey Secret | |
| STSToken | STS temporary credential token (optional, leave empty if not using STS) | |

> **Security tip:** Do not pass plaintext AK/SK directly in the command line. Use `ossutil config` for interactive configuration or environment variables.

---

## Common Commands Quick Reference

### File Upload

```bash
# Upload a single file
ossutil cp /local/path/file.pdf oss://your-bucket/remote/path/

# Upload an entire directory (recursive)
ossutil cp -r /local/dir/ oss://your-bucket/remote/dir/

# Incremental upload (only upload changed files)
ossutil sync /local/dir/ oss://your-bucket/remote/dir/
```

### File Download

```bash
# Download a single file
ossutil cp oss://your-bucket/remote/file.pdf /local/path/

# Download an entire directory
ossutil cp -r oss://your-bucket/remote/dir/ /local/dir/
```

### File Listing

```bash
# List Bucket root directory
ossutil ls oss://your-bucket/

# List a specific directory
ossutil ls oss://your-bucket/remote/dir/

# Recursively list all files
ossutil ls -r oss://your-bucket/
```

### Directory Sync

```bash
# Sync local directory to OSS (incremental, only upload new/changed files)
ossutil sync /local/dir/ oss://your-bucket/remote/dir/

# Sync and delete files in OSS that have been deleted locally
ossutil sync /local/dir/ oss://your-bucket/remote/dir/ --delete
```

---

## Endpoint Reference

| Region | Public Endpoint | Internal Endpoint |
|--------|----------------|-------------------|
| China East 1 (Hangzhou) | `oss-cn-hangzhou.aliyuncs.com` | `oss-cn-hangzhou-internal.aliyuncs.com` |
| China East 2 (Shanghai) | `oss-cn-shanghai.aliyuncs.com` | `oss-cn-shanghai-internal.aliyuncs.com` |
| China North 2 (Beijing) | `oss-cn-beijing.aliyuncs.com` | `oss-cn-beijing-internal.aliyuncs.com` |
| China South 1 (Shenzhen) | `oss-cn-shenzhen.aliyuncs.com` | `oss-cn-shenzhen-internal.aliyuncs.com` |

> **Note:** The OSS Bucket must be in the same region as the OTS instance to work with `tablestore-agent-storage`.

---

## Reference Links

- ossutil 2.0 Overview: https://help.aliyun.com/zh/oss/developer-reference/ossutil-overview/
- Install ossutil: https://help.aliyun.com/zh/oss/developer-reference/install-ossutil
- Configure ossutil: https://help.aliyun.com/zh/oss/developer-reference/configure-ossutil
- Command Reference: https://help.aliyun.com/zh/oss/developer-reference/ossutil
