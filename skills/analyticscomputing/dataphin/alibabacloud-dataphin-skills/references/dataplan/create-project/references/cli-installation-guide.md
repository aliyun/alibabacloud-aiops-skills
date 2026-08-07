# CLI 安装指南

## 前置要求

- 操作系统：macOS / Linux / Windows
- aliyun CLI >= 3.4.8
- `aliyun-cli-dataphin-public` 插件

## 1. 安装 Aliyun CLI

> 官方项目页面：https://github.com/aliyun/aliyun-cli
>
> 实际安装包下载地址：https://aliyuncli.alicdn.com/

### macOS / Linux 一键安装

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

### 版本验证

```bash
aliyun version
```

## 2. 安装 Dataphin 插件

```bash
aliyun plugin install --names aliyun-cli-dataphin-public
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## 3. 凭证检查

```bash
aliyun configure list
```

只检查 profile 是否存在，不要输出或记录 AK/SK 明文。

## 4. 插件命令检查

```bash
aliyun dataphin-public --help
aliyun dataphin-public get-project-by-name --help
aliyun dataphin-public list-projects --help
```

当前版本中应能看到 `list-projects`、`get-project`、`get-project-by-name`、`check-project-has-dependency` 等项目查询命令；如果没有看到 `create-project`，说明当前公开 CLI 不支持直接创建项目。

## 5. 观测字段

所有调用云 API 的 `aliyun dataphin-public` 命令必须携带：

```bash
--user-agent AlibabaCloud-Agent-Skills/create-project/{session-id}
```

本地工具命令如 `aliyun version`、`aliyun configure list`、`aliyun plugin update` 不支持该参数，可不追加。
