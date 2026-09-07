# Aliyun CLI Installation Guide

## 1. Install / Upgrade the aliyun CLI

```bash
# Check the current version (requires >= 3.3.3; this skill is verified on 3.3.10)
aliyun version

# Install when missing or too old
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
exec $SHELL -l
aliyun version
```

## 2. Configure the default profile

```bash
aliyun configure list

# If empty, enter interactively:
aliyun configure
#   profile name [default]:
#   AccessKey Id:
#   AccessKey Secret:
#   Default Region Id [cn-hangzhou]:
#   Default Output Format [json]: json
#   Default Language [zh|en]: zh
```

> [WARN] AccessKeys must never be echoed in plaintext, recorded in logs, written into fixtures, or appear in test reports.

## 3. Install the plugin

This skill depends only on `eflo-controller`:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --name eflo-controller
aliyun plugin update
```

Verification:

```bash
aliyun eflo-controller 2>&1 | head -5
# Expected: lists subcommands such as list-clusters / describe-cluster / create-diagnostic-task
```

## 4. Verify the three diagnostic CLIs are available

```bash
aliyun eflo-controller create-diagnostic-task --help | head -10
aliyun eflo-controller describe-diagnostic-result --help | head -10
aliyun eflo-controller list-diagnostic-results --help | head -10
```

If any of the above returns `unknown command`, the plugin is not installed correctly or is too old; re-run section 3.

## 5. Observability (User-Agent tracking)

Every `aliyun` command that calls a cloud API must carry the skill User-Agent with a per-session session-id (see SKILL.md Section Observability). `lib/lj_init.sh` exports `ALIBABA_CLOUD_USER_AGENT=AlibabaCloud-Agent-Skills/alibabacloud-lingjun-node-diagnose/{session-id}` automatically; no manual setup is needed. Legacy configure-based User-Agent mechanisms are deprecated and must NOT be used.
