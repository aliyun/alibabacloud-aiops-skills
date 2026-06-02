# Related Commands: alibabacloud-aes-sysom-pai-diagnosis

This skill uses the `aliyun` CLI to call SysOM and PAI EAS / DLC APIs. All **business commands** (SysOM, EAS, DLC API calls) **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis`. System commands (`version`, `configure`, `plugin`) do NOT use `--user-agent`.

---

## Diagnosis Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom initial-sysom --check-only false --source aes-skills` | Initialize SysOM role authorization |
| eas | `aliyun eas list-services --region <region> --filter <eas_service_id>` | Verify EAS service ID (`eas-m-xxx`) exists in the region (EAS only) |
| pai-dlc | `aliyun pai-dlc get-job --region <region> --job-id <dlc_job_id>` | Verify DLC job exists and check `ResourceType` is `Lingjun` (DLC only) |
| sysom | `aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '<JSON>'` | Invoke intelligent diagnosis (params keys use snake_case, must include `type: "ocd"` and `product: "EAS"` or `"DLC"`) |
| sysom | `aliyun sysom get-diagnosis-result --task-id <task_id>` | Get diagnosis result |

> **Note**: PAI EAS / DLC are fully managed services. There is **no** "Cloud Assistant online check" (`describe-cloud-assistant-status`) or "instance support check" (`check-instance-support`) step — these are ECS-only concepts. There is also **no** Agent install / uninstall and **no** alert configuration in this skill.

---

## Cleanup

Diagnosis is read-only — no cleanup commands are required.

After all CLI operations complete:

```bash
aliyun configure ai-mode disable
```

---

## Fixed Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--service-name` | `ocd` | Diagnosis type (intelligent diagnosis) |
| `--channel` | `ecs` | Diagnosis dispatch channel (fixed; engine routes by `product` field internally) |
| `--user-agent` | `AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis` | Must be appended to all business commands (SysOM, EAS, DLC API calls) |

---

## params JSON Field Reference

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `instance` | ✅ | string | EAS service ID (`eas-m-xxx`) or DLC job ID (`dlcxxxxxxxx`), passed as-is |
| `region` | ✅ | string | Region of the PAI resource |
| `product` | ✅ | string | `EAS` or `DLC` |
| `type` | ✅ | string | Fixed value `ocd` |
| `start_time` | ✅ | int | Unix timestamp (seconds), `0` for real-time |
| `end_time` | ✅ | int | Unix timestamp (seconds), `0` for real-time |
| `ai_roadmap` | ✅ | bool | Fixed value `true` |
| `enable_sysom_link` | ✅ | bool | Fixed value `false` |
| `uid` | ⬜ | int | Account ID owning the resource |
