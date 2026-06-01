# PTS Related APIs and CLI Commands

This document lists all APIs and CLI commands related to Alibaba Cloud Performance Testing Service (PTS).

## Product Information

| Property | Value |
|----------|-------|
| Product Code | PTS |
| API Version | 2020-10-20 |
| Endpoint | pts.cn-hangzhou.aliyuncs.com |

## PTS Native Stress Testing APIs

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun pts create-pts-scene` | CreatePtsScene | **Create a NEW** PTS stress testing scenario |
| `aliyun pts save-pts-scene` | SavePtsScene | **Update** an existing PTS scenario (must include `SceneId` in payload) |
| `aliyun pts get-pts-scene` | GetPtsScene | Get PTS scenario details |
| `aliyun pts list-pts-scene` | ListPtsScene | List PTS scenarios |
| `aliyun pts start-pts-scene` | StartPtsScene | Start a PTS stress testing task |
| `aliyun pts stop-pts-scene` | StopPtsScene | Stop a running regular PTS stress testing task |
| `aliyun pts delete-pts-scene` | DeletePtsScene | Delete a PTS scenario |
| `aliyun pts start-debug-pts-scene` | StartDebugPtsScene | Start a debug-mode run of a PTS scenario |
| `aliyun pts stop-debug-pts-scene` | StopDebugPtsScene | Stop a debug-mode PTS run (use this, NOT stop-pts-scene, when started via start-debug-pts-scene) |
| `aliyun pts get-pts-report-details` | GetPtsReportDetails | Get PTS stress testing report details |

## JMeter Stress Testing APIs

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun pts save-open-jmeter-scene` | SaveOpenJMeterScene | Create or update a JMeter scenario |
| `aliyun pts get-open-jmeter-scene` | GetOpenJMeterScene | Get JMeter scenario details |
| `aliyun pts list-open-jmeter-scenes` | ListOpenJMeterScenes | List JMeter scenarios |
| `aliyun pts start-testing-jmeter-scene` | StartTestingJMeterScene | Start a JMeter stress testing task |
| `aliyun pts stop-testing-jmeter-scene` | StopTestingJMeterScene | Stop a running JMeter stress testing task |
| `aliyun pts remove-open-jmeter-scene` | RemoveOpenJMeterScene | Delete a JMeter scenario |
| `aliyun pts get-jmeter-report-details` | GetJMeterReportDetails | Get JMeter stress testing report details |

## File Management APIs

| CLI Command | API Action | Description |
|-------------|------------|-------------|
| `aliyun pts get-pts-scene-base-line` | GetPtsSceneBaseLine | Get PTS scenario baseline |
| `aliyun pts get-pts-scene-running-data` | GetPtsSceneRunningData | Get PTS scenario running data |
| `aliyun pts get-pts-scene-running-status` | GetPtsSceneRunningStatus | Get PTS scenario running status |

## Common Parameters

All CLI commands support the following common parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--region` | No | Region ID (default: cn-hangzhou) |
| `--user-agent` | Yes | Must be `AlibabaCloud-Agent-Skills` |

## Example CLI Commands

### Create PTS Scenario

```bash
aliyun pts create-pts-scene \
  --scene '{"SceneName":"test-scene","RelationList":[{"RelationName":"link-1","ApiList":[{"ApiName":"api-1","Url":"https://example.com","Method":"GET","TimeoutInSecond":10}]}],"LoadConfig":{"TestMode":"concurrency_mode","MaxRunningTime":1,"Configuration":{"AllConcurrencyBegin":10,"AllConcurrencyLimit":10}}}'
```

### Update an Existing PTS Scenario

```bash
# Must include SceneId in the JSON payload to update; otherwise a duplicate scene is created
aliyun pts save-pts-scene \
  --scene '{"SceneId":"<EXISTING_SCENE_ID>","SceneName":"updated-name", ...}'
```

### Start PTS Stress Testing

```bash
aliyun pts start-pts-scene \
  --scene-id <SceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create JMeter Scenario

```bash
aliyun pts save-open-jmeter-scene \
  --open-jmeter-scene '{"scene_name":"MyJMeterTest","test_file":"example.jmx","duration":300,"concurrency":100,"mode":"CONCURRENCY"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Start JMeter Stress Testing

```bash
aliyun pts start-testing-jmeter-scene \
  --scene-id <SceneId> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Common CLI Errors

| Error Message | Root Cause | Fix |
|---|---|---|
| `场景名不能为空` / `SceneName is required` | JSON parse failed; `--scene` value not correctly read | Write JSON to a file, then `--scene "$(cat scene.json)"` (bash) or `--scene (Get-Content scene.json -Raw)` (PowerShell) |
| `SceneId is required` | Missing `--scene-id` parameter | Ensure command includes `--scene-id` with the ID returned from create step |
| `Invalid JSON format` | Nested quotes corrupted by shell escaping | Use file-based approach instead of inline JSON |
| `scene is already running` | Duplicate start attempt | Run `get-pts-scene-running-status` first; if RUNNING/SYNCING, skip start |
| `scene not found` | SceneId does not exist or was deleted | Re-run `list-pts-scene` to verify available scenes |
| `Throttling.User` (HTTP 400) | API rate limit exceeded | Wait 3–5 seconds and retry once (max 2 retries per command) |
| `Timeout` / no response | CLI read-timeout too short | Add `--read-timeout 60 --connect-timeout 10` |

## References

- [PTS API Documentation](https://help.aliyun.com/zh/pts/developer-reference/api-pts-2020-10-20-overview)
- [Create PTS Scenario](https://help.aliyun.com/zh/pts/performance-test-pts-2-0/user-guide/create-a-stress-testing-scenario-6)
- [Create JMeter Scenario](https://help.aliyun.com/zh/pts/performance-test-pts-2-0/user-guide/create-a-jmeter-scenario)
