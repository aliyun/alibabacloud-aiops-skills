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
| `aliyun pts create-pts-scene` | CreatePtsScene | Create a PTS stress testing scenario |
| `aliyun pts get-pts-scene` | GetPtsScene | Get PTS scenario details |
| `aliyun pts list-pts-scene` | ListPtsScene | List PTS scenarios |
| `aliyun pts start-pts-scene` | StartPtsScene | Start a PTS stress testing task |
| `aliyun pts stop-pts-scene` | StopPtsScene | Stop a running PTS stress testing task |
| `aliyun pts delete-pts-scene` | DeletePtsScene | Delete a PTS scenario |
| `aliyun pts start-debug-pts-scene` | StartDebugPtsScene | Debug a PTS scenario |
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
  --scene '{"name":"test-scene","type":"HTTP","requests":[{"url":"https://example.com","method":"GET"}]}' \
  --user-agent AlibabaCloud-Agent-Skills
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

## References

- [PTS API Documentation](https://help.aliyun.com/zh/pts/developer-reference/api-pts-2020-10-20-overview)
- [Create PTS Scenario](https://help.aliyun.com/zh/pts/performance-test-pts-2-0/user-guide/create-a-stress-testing-scenario-6)
- [Create JMeter Scenario](https://help.aliyun.com/zh/pts/performance-test-pts-2-0/user-guide/create-a-jmeter-scenario)
