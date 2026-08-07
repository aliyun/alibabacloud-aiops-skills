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
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz

tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

> 如果使用 Homebrew，也可以执行：`brew install aliyun-cli`

### Linux（x86_64 / AMD64）

```bash
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

### Linux（ARM64）

```bash
curl -fsSL -o aliyun-cli.tgz \
  https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

### Windows（64 位）

```powershell
$Url = "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip"
$Zip = "$env:TEMP\aliyun-cli.zip"
$Dest = "C:\aliyun-cli"

Invoke-WebRequest -Uri $Url -OutFile $Zip
Expand-Archive -Path $Zip -DestinationPath $Dest -Force

$env:Path += ";$Dest"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User)

aliyun version
```

## 2. 安装 Dataphin 插件

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
```

启用自动插件安装与更新：

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## 3. 验证

```bash
# 版本须 >= 3.4.8
aliyun version

# 验证本 Skill 使用的公开命令
aliyun dataphin-public list-security-identify-results --help
aliyun dataphin-public get-security-identify-result --help
aliyun dataphin-public list-security-identify-records --help
aliyun dataphin-public get-security-classify --help
```

当前公开 CLI 和版本索引未包含脱敏规则 CRUD 命令；本 Skill 仅使用上述公开命令完成字段标签前置检查。

## 4. 配置凭证

Dataphin 插件复用 aliyun-cli 的凭证体系。凭证必须在会话外配置，Skill 仅通过以下命令检查 profile 状态：

```bash
aliyun configure list
```

不得读取、回显或记录 AccessKey 明文。完整环境判定和配置规则由父 Skill 统一处理。

## 5. 观测字段

所有调用云 API 的命令必须携带：

```bash
--user-agent AlibabaCloud-Agent-Skills/manage-data-masking/{session-id}
```

本地工具命令如 `aliyun version`、`aliyun configure list`、`aliyun plugin update` 不追加该参数。

详见父 Skill [alibabacloud-dataphin-skills](../../../../SKILL.md) 的 Authentication 章节。
