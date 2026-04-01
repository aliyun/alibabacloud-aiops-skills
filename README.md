# Alibaba Cloud Skills

**English** | [简体中文](README-CN.md)

Official Alibaba Cloud Agent Skills collection, providing AI agents with rich Alibaba Cloud product capabilities and general-purpose tooling.

## Overview

This repository contains a set of officially maintained Agent Skills to help developers use Alibaba Cloud products and services more efficiently. Each Skill is designed and tested for stability and reliability.

## Skills list

Alibaba Cloud product Skills — to be updated.

## Installation

### Install Skills with npx

```bash
# Install a single Skill
npx skills add aliyun/alibabacloud-aiops-skills --skill <skill-name>

# Install all Alibaba Cloud Skills
npx skills add aliyun/alibabacloud-aiops-skills

# Install stable release (default)
npx skills add aliyun/alibabacloud-aiops-skills --skill <skill-name>

# Install latest beta
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/preview --skill <skill-name>

# Install a specific historical version (rollback)
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/<skill-name>-<version> --skill <skill-name>

# Install a specific beta version
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills/tree/<skill-name>-<beta-version> --skill <skill-name>

```

### Manual installation

```bash
# Clone the repository
git clone https://github.com/aliyun/alibabacloud-aiops-skills.git

# Point npx skills at the Skill directory
npx skills add <path>/alibabacloud-aiops-skills/skills/<skill-name>

```

## Authentication and configuration

Skills related to Alibaba Cloud products require credentials. The following methods are supported:

**AccessKey authentication**

```bash
# Set environment variables
export ALIBABACLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABACLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
```

**Aliyun CLI profile authentication**

```bash
# ~/.aliyun/config.json
aliyun configure [--profile <PROFILE_NAME>] [--mode <AUTHENTICATE_MODE>]
```

## Issues

[Open an issue][issue]. Issues that do not follow the guidelines may be closed immediately.

## Related

- [Alibaba Cloud website][url]

## License

[Apache-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Copyright (c) 2009-present, Alibaba Cloud All rights reserved.

## Legal

All Skills provided in this repository are open-source projects intended to give developers rich Agent capability extensions and help you manage cloud resources more efficiently. They are governed by the [MIT License](https://spdx.org/licenses/MIT.html). Before you use any Skills from this platform, read the [legal terms](https://terms.alicdn.com/legal-agreement/terms/b_platform_service_agreement/20260330114515787/20260330114515787.html?spm=2263e3e9.11c91e34.0.0.64924106EfoiZy) carefully and understand the risks. By downloading, installing, or running any Skills from this platform in any way, you acknowledge that you have read and agree to bear all operational risks and that you are solely responsible for any consequences arising from use of this code.

[issue]: https://github.com/aliyun/alibabacloud-aiops-skills/issues/new
[url]: https://www.alibabacloud.com
