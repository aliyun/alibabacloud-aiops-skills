# Related APIs and CLI Commands

## Command Summary

| Surface | Command | Purpose | Validation Status |
| --- | --- | --- | --- |
| `aliyun` CLI | `aliyun version` | Verify CLI availability and version | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun configure set --auto-plugin-install true` | Enable plugin auto-install | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun configure ai-mode enable` | Enable AI safety mode to block dangerous operations | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun configure ai-mode disable` | Disable AI safety mode after task completion | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun configure list` | Verify credential profile state safely | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun oss --help` | Discover OSS product command surface | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun ossutil --help` | Discover integrated ossutil command surface | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun ossutil api list-buckets --output-format json --read-timeout 60 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills` | Enumerate buckets for prerequisite verification | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun ossutil stat "oss://${BucketName}" --region "${RegionId}" --output-format json --read-timeout 60 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills` | Verify bucket metadata and region | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun ossutil cp --help` | Verify the integrated upload command surface | Not validated locally because `aliyun` was not installed in this repository |
| `aliyun` CLI | `aliyun ossutil cp "${LocalSourcePath}" "oss://${BucketName}/${TargetOssPrefix}" -r -u --max-age "${MaxAge}" --region "${RegionId}" --read-timeout 300 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills` | Canonical incremental upload command via integrated ossutil | Not validated locally because `aliyun` was not installed in this repository, and not executed against a live bucket here |
| `aliyun` CLI | `aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region "${RegionId}" --read-timeout 60 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills` | Verify uploaded objects under the target prefix | Not validated locally because `aliyun` was not installed in this repository, and not executed against a live bucket here |
| `aliyun` CLI | `aliyun ossutil rm "oss://${BucketName}/${TargetOssPrefix}test-object.txt" --region "${RegionId}" --read-timeout 60 --connect-timeout 30 --user-agent AlibabaCloud-Agent-Skills` | Optional cleanup for test artifacts | Not validated locally because `aliyun` was not installed in this repository |
| Local OS | `crontab -l` | Verify cron registration on Linux/macOS | Validated locally |
| Local OS | `schtasks /Query /TN "OSS Scheduled Sync" /V /FO LIST` | Verify Task Scheduler registration on Windows | Not validated locally in this macOS repository |

## OSS Capability Notes

These notes explain which OSS-side capability each `aliyun ossutil` command relies on. They are documentation-only reference data for the skill package, not `eval` assertion fields, and do not mean the user-facing answer must present OpenAPI or POP gateway actions.

| Command | Related OSS capability | Notes |
| --- | --- | --- |
| `aliyun ossutil api list-buckets --output-format json` | Service-level bucket inventory | Used to confirm the bucket exists in the current account |
| `aliyun ossutil stat "oss://${BucketName}" --region ... --output-format json` | Bucket metadata lookup | Used to verify bucket metadata and region |
| `aliyun ossutil cp ... -r -u --max-age ... --region ...` | Object upload plus object comparison/listing for incremental behavior | Official scenario command through integrated `aliyun ossutil`; permissions align with object upload, read, and list needs |
| `aliyun ossutil ls "oss://${BucketName}/${TargetOssPrefix}" --region ...` | Object listing under the target prefix | Post-upload verification under the target prefix |
| `aliyun ossutil rm "oss://${BucketName}/${TargetOssPrefix}test-object.txt" --region ...` | Object deletion | Optional cleanup for test artifacts only |

## RAM/IAM Notes

This skill references RAM policies for least-privilege guidance, but the default scenario does not require a validated `aliyun ram ...` command.

What is in scope:
- documenting the least-privilege policy actions needed for upload and verification
- attaching that policy through the user's existing IAM workflow or the RAM Console

What is out of scope for the default flow:
- inventing unvalidated `aliyun ram` automation commands in this repository
- assuming the operator wants policy creation or attachment automated

## Capability Split

| Task | Preferred Surface | Reason |
| --- | --- | --- |
| CLI installation checks | `aliyun` | Matches the creator skill contract and supports `--user-agent` tagging |
| Credential gate | `aliyun configure list` | Required by the creator skill contract |
| OSS-side bucket verification | `aliyun ossutil` | Best fit for CLI-first OSS verification where supported |
| Scheduled upload job | `aliyun ossutil` | Keeps the official `ossutil cp` workflow on the required `aliyun` CLI surface |
| Scheduler registration | Local OS tools | Cron and Task Scheduler are host-level, not Alibaba Cloud APIs |
| Visual bucket inspection | OSS Console | Optional manual verification |

## Important Limitations

1. The data-plane sync uses the integrated `aliyun ossutil` surface, but it still runs from the local host and is not an OSS-side scheduled service.
2. Bucket creation should follow the existing creation flow documented by this skill, while upload and verification stay on the integrated `aliyun ossutil` surface.
3. Scheduler configuration is OS-local and must be labeled separately from Alibaba Cloud CLI steps.
4. Any direct RAM API automation must be treated as optional follow-up work, not part of the default validated path.
5. Local authoring validation in this repository did not include a live upload or live object listing against a real OSS bucket.
6. Answers should not fill prerequisite gaps by inventing extra scripts, fake logs, sample local payloads, or standalone `ossutil` installation/configuration detours.
