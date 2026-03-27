# Alibaba Cloud Skills
阿里云官方 Agent Skills 集合，为 AI Agent 提供丰富的阿里云产品能力和通用工具集。

## 概述
本仓库包含了一系列官方维护的 Agent Skills，旨在帮助开发者更高效地使用阿里云产品和服务。每个 Skill 都经过精心设计和测试，确保稳定性和可靠性。

## Skills 列表
阿里云产品 Skills 待更新

## 安装

### 使用 npx 安装 Skills

```bash
# 安装单个 Skill
npx skills add aliyun/alibabacloud-aiops-skills --skill <skill-name>

# 安装所有阿里云 Skills
npx skills add aliyun/alibabacloud-aiops-skills

# 安装正式版（默认）
npx skills add aliyun/alibabacloud-aiops-skills --skill <skill-name>

# 安装最新 beta
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/preview --skill <skill-name>

# 安装指定历史版本（回退）
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/<skill-name>-<version> --skill <skill-name>

# 安装指定 beta 版本
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/<skill-name>-<beta-version> --skill <skill-name>

```

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/aliyun/alibabacloud-aiops-skills.git

# 进入 Skills 目录
npx skills add <path>/alibabacloud-aiops-skills/skills/<skill-name>

```

## 认证与配置
使用阿里云产品相关的 Skills 需要配置认证信息。支持以下认证方式：

AccessKey 认证

```bash
# 设置环境变量
export ALIBABACLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABACLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
```

Aliyun CLI 配置文件认证

```bash
# ~/.aliyun/config.json
aliyun configure [--profile <PROFILE_NAME>] [--mode <AUTHENTICATE_MODE>]
```

## 问题
[提交 Issue][issue] 不符合指南的问题可能会立即关闭。

## 相关

- [阿里云服务 Regions & Endpoints][endpoints]
- [阿里云官网][url]

## 许可证
[Apache-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Copyright (c) 2009-present, Alibaba Cloud All rights reserved.

[issue]: https://github.com/aliyun/alibabacloud-aiops-skills/issues/new
[url]: https://www.aliyun.com
[endpoints]: https://developer.aliyun.com/endpoints


