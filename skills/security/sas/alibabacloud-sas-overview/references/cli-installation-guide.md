# CLI installation and command compatibility

Before API examples, initialize and reuse the manifest-derived `USER_AGENT` as
described in [SKILL.md](../SKILL.md#observability).

Use Alibaba Cloud CLI >= 3.3.1. This Skill's API command/flag checks were run with
CLI 3.4.11; verify the local plugin contract rather than assuming CLI version alone
establishes compatibility.

```bash
aliyun version
# Install/update the CLI if needed:
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
```

## Credentials

Check profile availability with `aliyun configure list`. Never read credential
files, print AK/SK values, or paste keys into chat or generated command lines.
If no valid profile exists, configure credentials outside this session using the
CLI's interactive configuration or your organization's identity workflow, then
repeat the status check. See [console-sites.md](console-sites.md) for account-site
navigation. Resource region and language do not determine the account site.

## Plugins

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun plugin list
```

These local maintenance commands do not use the cloud API User-Agent option;
`configure` and `plugin update` reject that option on CLI 3.4.11. Every cloud query
must carry the full session UA from SKILL.md.

Use plugin commands and kebab-case flags consistently. Before querying data, verify
that help includes Usage, API Version and the complete parameter descriptions:

```bash
aliyun sas describe-cloud-center-instances --help --user-agent "$USER_AGENT"
aliyun waf-openapi describe-flow-chart --help --user-agent "$USER_AGENT"
aliyun bssopenapi query-bill --help --user-agent "$USER_AGENT"
```

A zero exit code or version banner alone is insufficient. If help is missing or
parameters differ, update the affected plugin and check again. Do not guess PascalCase
flags or mix legacy API-style commands with plugin syntax. If a plugin still cannot
expose the required command, mark that module unavailable and preserve other results.

## Regression checks

From the Skill directory, run `python3 scripts/check_cli_contract.py`. It only invokes
help, checks every documented active API command/flag and rejects empty help or the
wrong API version. It does not call cloud APIs or validate live permissions/data.
Manually check full parameter descriptions for enums, units and formats. The host
helper uses page numbers (20 per page), not NextToken mode, because it validates
PageInfo.TotalCount. WAF interval is a multiple of 60 seconds; SAS chart times use ms.

Sources: [CLI documentation](https://help.aliyun.com/zh/cli/),
[CLI source](https://github.com/aliyun/aliyun-cli).

Current validation and BSS plugin recovery are recorded in
[cli-validation.md](cli-validation.md). Help checks do not replace live business-data
and permission verification.
