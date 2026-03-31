# ossutil Installation Guide

## Overview

ossutil is a command-line tool for managing Alibaba Cloud OSS resources. This guide provides installation instructions for ossutil v2.2.1.

## Download Links

Current latest version: **2.2.1**

### Linux

| System Architecture | Download Link | SHA256 Checksum |
|---------|---------|--------------|
| x86_32 | [ossutil-2.2.1-linux-386.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-386.zip) | `09726a85eb35f863fc584f4fa1ca5e6a8805729083bc29ec91e803f0eb64bcc7` |
| x86_64 | [ossutil-2.2.1-linux-amd64.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-amd64.zip) | `fbf1026bd383a5d9bee051cd64a6226c730357ba569491f7c7b91af66560ef1d` |
| arm32 | [ossutil-2.2.1-linux-arm.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-arm.zip) | `30fed1691d774a3d1872cae0fc266122b8f9c68c990199361d974406f7d2ef5a` |
| arm64 | [ossutil-2.2.1-linux-arm64.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-arm64.zip) | `b7680e79aec0adc9d42a12b795612680a58efec1fad24b0ceb9e13b2390c6652` |

### macOS

| System Architecture | Download Link | SHA256 Checksum |
|---------|---------|--------------|
| x86_64 | [ossutil-2.2.1-mac-amd64.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-mac-amd64.zip) | `a1bf1491037e138e52b0b92cdfd620decdc9e22d8dd1d8699226a8f2596b0cc2` |
| arm64 | [ossutil-2.2.1-mac-arm64.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-mac-arm64.zip) | `326bff983e8e02142fc4e68d07f129475f9cbafb9777ed57cd7b6640edd8595c` |

### Windows

| System Architecture | Download Link | SHA256 Checksum |
|---------|---------|--------------|
| x86_32 | [ossutil-2.2.1-windows-386.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-windows-386.zip) | `36043ddeed88188f36b41b631fae3c6909ffffb661d34bc1d5405863f9064d0c` |
| x86_64 | [ossutil-2.2.1-windows-amd64.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-windows-amd64.zip) | `a7c22a0172fdca0e54cb8366f1ae8a869bc6bb64c1899352eb62d8eb9a1a9af0` |
| amd64 (Go 1.20) | [ossutil-2.2.1-windows-amd64-go1.20.zip](https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-windows-amd64-go1.20.zip) | `8670b88437be62053aa4b3d2da7695fa410f451693833534faa7b20e39c8eded` |

## Installation Steps

### Linux/macOS

```bash
# 1. Download (example for Linux x86_64)
wget https://gosspublic.alicdn.com/ossutil/v2/2.2.1/ossutil-2.2.1-linux-amd64.zip

# 2. Extract
unzip ossutil-2.2.1-linux-amd64.zip

# 3. Move to PATH directory
chmod +x ossutil
sudo mv ossutil /usr/local/bin/

# 4. Verify installation
ossutil version
```

### Windows

1. Download the appropriate version from the links above
2. Extract the zip archive
3. Add the extracted directory to your system PATH
4. Or copy the ossutil.exe file to a directory that's already in your PATH
5. Verify installation by running `ossutil version` in Command Prompt

## Configuration

After installation, ossutil automatically obtains authentication information through the default credential chain without manual AK/SK configuration. The default credential chain looks for credentials in the following order:

1. Environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`)
2. Credentials in configuration file (set via `aliyun configure`)
3. ECS instance RAM role (automatically obtained in ECS environments)

It is recommended to use instance RAM roles in cloud environments such as ECS, and use environment variables or `aliyun configure` for local development environments.

Configure endpoint information:

```bash
ossutil config --endpoint oss-cn-hangzhou.aliyuncs.com
```
