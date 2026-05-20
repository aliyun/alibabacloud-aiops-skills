---
name: alibabacloud-alinux-sysom-inspection
version: 0.1.0
description: 用于检查 ECS 实例的系统健康状况，识别内存、磁盘、CPU、负载与资源泄漏等异常，并在命中关键内存问题时自动补充深度诊断结果。适用于实例巡检、故障排查与风险预警场景。触发词：SysOM、巡检、实例诊断、memory_usage_rate、内存使用率。
layer: application
category: os-ops
lifecycle: operations
tags:
  - sysom
  - inspection
  - ecs
  - memory
  - diagnosis
status: beta
---

# SysOM 巡检（sysom-inspection）

在技能根目录执行 `./scripts/osops.sh`。

当前实现命令：
- `inspection`

## 快速开始

```bash
cd <alibabacloud-alinux-sysom-inspection>
./scripts/init.sh
./scripts/osops.sh inspection \
  --region-id cn-hangzhou \
  --instance-id i-xxx
```

## 执行逻辑

- 每次执行巡检前先调用 ROA 接口 `POST /api/v1/openapi/initial_sysom`（`source=skill_hub`），用于判断用户是否具备权限且 SysOM 已开通。
- 若未开通或角色未就绪，命令会交互式询问是否继续“开通+安装 SysOM”。
- 用户同意后先调用 `InitialSysom(check_only=false, source=skill_hub)` 执行开通，再调用 `InstallAgentWithType` 安装。
- 安装后会再次调用 `InitialSysom(check_only=true, source=skill_hub)` 复检，复检通过才继续巡检与诊断。
- 不再本地配置阈值/事件规则，异常判断由服务端巡检报告决定。
- 固定调用 ROA 巡检接口：`POST /api/v1/inspection/createInstanceInspection`，并固定传 `source=skill_hub`。
- 若需要巡检全部项目，可传 `items=[]`（CLI 中为显式传空 `--inspection-items`）。
- 若标准巡检 API 返回 `InvalidAction.NotFound`，CLI 会标记“当前版本不可用”并停止后续流程，避免无效重试。
- 报告查询调用 ROA 接口：`GET /api/v1/inspection/getInspectionReport`。
- 当创建接口不可用时，CLI 会补发一次 `GetInspectionReport` 探测调用并记录结果，确保日志中可观测到该动作。
- 巡检报告中若命中 `sysom:metric:memory_usage_rate` 异常，自动调用 `InvokeDiagnosis` 发起 `memgraph` 诊断。
- `InvokeDiagnosis` 的 `params` 会注入 `__sysom_diagnosis_source=skill_hub`，并校验业务 `code=Success`。
- 发起诊断后自动轮询 `GetDiagnosisResult`，直到 `success` / `fail` / 超时。
- 可通过 `--disable-memgraph-diagnosis` 关闭自动诊断。

## 可扩展性约定

- 巡检项可通过 `--inspection-items` 传入覆盖默认列表。
- 若 InitialSysom 返回未开通，CLI 会在终端进行交互式确认后再执行开通尝试+重检。
- 内存异常触发诊断的判定逻辑位于 `scripts/sysom_cli/inspection/command.py`。
- 如需新增“巡检命中后触发的专项诊断”，可复用 `InvokeDiagnosis` 调用方式扩展。
