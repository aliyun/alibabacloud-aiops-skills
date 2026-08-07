# CLI 安装指南

## 前置要求

- 操作系统：macOS / Linux / Windows
- aliyun CLI >= 3.4.8

## 1. 安装 Aliyun CLI

> 官方下载地址：https://github.com/aliyun/aliyun-cli
>
> 以下脚本均从 GitHub Releases 拉取最新版本，复制对应系统的代码块直接执行即可。

### macOS

**Apple Silicon（arm64）**

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-macosx-arm64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

**Intel（amd64）**

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-macosx-amd64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

> 如果你使用 Homebrew，也可以执行：`brew install aliyun-cli`

### Linux

**x86_64（amd64）**

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-linux-amd64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

**ARM64**

```bash
# 下载最新版 aliyun CLI
curl -fsSL -o aliyun-cli.tgz \
  https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-linux-arm64.tgz

# 解压并安装到 /usr/local/bin
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# 验证
aliyun version
```

### Windows

**PowerShell（amd64）**

```powershell
# 下载最新版 aliyun CLI
$Url = "https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-windows-amd64.zip"
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
  --region cn-hangzhou
```

> **配置方式说明**
> - 公共云 SaaS 环境：支持交互式 `aliyun configure` 和非交互式 `aliyun configure set ...`。仅须指定 `--region`，无须配置 `--endpoint`。AccessKey 从 [RAM 控制台](https://ram.console.aliyun.com/manage/ak) 获取。建议使用 RAM 子账号的 AK/SK，避免使用主账号。
> - 独立部署环境：**仅支持非交互式** `aliyun configure set ...`（需带 `--endpoint` 指定管理面 OpenAPI 地址，`--region` 设置为 cn-hangzhou）；使用交互式 `aliyun configure` 会报错 `Specified access key is not found`。AccessKey 从 Dataphin 右上角 个人账号 -> AccessKey 管理中获取。

或通过环境变量（推荐用于 CI/CD 与自动化场景）：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-ak-secret>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

详见父 skill [alibabacloud-dataphin-skills](../SKILL.md) 的 Authentication 章节。
