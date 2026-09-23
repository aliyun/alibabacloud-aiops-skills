# Aliyun CLI Installation

This skill requires Alibaba Cloud CLI 3.3.3 or later.

For a first installation or major upgrade:

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
```

For routine upgrades on CLI 3.3.5 or later:

```bash
aliyun upgrade
aliyun version
```

Use `aliyun configure list` only to verify that a profile is available. Configure an identity outside the skill session if the profile is invalid.

## CSAS plugin

The script checks for the CSAS plugin immediately before its first cloud call. If it is absent, it installs the local dependency non-interactively:

```bash
aliyun plugin install --name aliyun-cli-csas < /dev/null
```

This is local CLI setup only. It does not create, update, or delete any Alibaba Cloud resource, and it does not change the global CLI configuration.
