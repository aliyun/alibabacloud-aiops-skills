# CLI 安装指南

## 前置要求

- 操作系统：macOS / Linux / Windows
- aliyun CLI >= 3.4.8

## 1. 安装 Aliyun CLI

> 官方项目页面：https://github.com/aliyun/aliyun-cli
>
> 实际安装包下载地址：https://aliyuncli.alicdn.com/（与 [README Installation](https://github.com/aliyun/aliyun-cli/blob/master/README.md#installation) 一致）
>
> 以下脚本均使用 aliyuncli.alicdn.com 上的最新稳定版，复制对应系统的代码块直接执行即可。

### macOS / Linux 一键安装（推荐）

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

### macOS（Universal 二进制，Intel / Apple Silicon 通用）

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

> 如果你使用 Homebrew，也可以执行：`brew install aliyun-cli`

### Linux（x86_64 / AMD64）

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

### Linux（ARM64）

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

### Windows（64 位）

```powershell
# 下载最新版 aliyun CLI
$Url = "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip"
$Zip = "$env:TEMP\aliyun-cli.zip"
$Dest = "C:\aliyun-cli"

Invoke-WebRequest -Uri $Url -OutFile $Zip
Expand-Archive -Path $Zip -DestinationPath $Dest -Force

# 添加到当前用户 PATH
$env:Path += ";$Dest"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User)

# 验证
aliyun version
```

## 2. 安装 Dataphin 插件

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

启用自动插件安装与更新（推荐）：

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## 3. 验证

```bash
# 版本须 >= 3.4.8
aliyun version

# 应输出 dataphin-public 命令列表
aliyun dataphin-public --help
```

## 4. 配置凭证

Dataphin 插件复用 aliyun-cli 的凭证体系：**AccessKey/Endpoint 由 aliyun-cli 主 profile 提供，tenant/project 由插件自身的本地 profile 提供**。

交互式配置（仅公共云 SaaS 环境支持）：

```bash
aliyun configure --profile <profile-name>
```

非交互式配置（公共云 SaaS 与独立部署均支持，独立部署必须使用此方式）：

```bash
aliyun configure set \
  --profile <profile-name> \
  --mode AK \
  --access-key-id <YOUR_AK_ID> \
  --access-key-secret <YOUR_AK_SECRET> \
  --region cn-hangzhou # 公共云指定所属region，独立部署保持 cn-hangzhou 即可\
  --endpoint <DATAPHIN_OPENAPI_ENDPOINT>  # 独立部署必填，公共云无须指定
```

> **可能遇到的问题**
> - 报错 `Specified access key is not found`。
>   - 原因: 独立部署使用交互式配置方式
>   - 解决方案: 独立部署修改为非交互式配置方式

或通过环境变量（推荐用于 CI/CD 与自动化场景）：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-ak-secret>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

详见父 skill [alibabacloud-dataphin-skills](../../../../SKILL.md) 的 Authentication 章节。
