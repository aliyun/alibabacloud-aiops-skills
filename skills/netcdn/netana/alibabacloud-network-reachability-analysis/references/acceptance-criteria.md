# Acceptance Criteria: nis-reachability-analysis

**Scenario**: Network Reachability Analysis with NIS
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. NIS Product — verify `nis` exists as product

```bash
aliyun nis --help
# Must show available commands including create-and-analyze-network-path, get-network-reachable-analysis
```

### 2. create-and-analyze-network-path — verify command and parameters

#### CORRECT

```bash
aliyun nis create-and-analyze-network-path \
  --source-id i-bp1xxxxx \
  --source-type ecs \
  --target-id i-bp2xxxxx \
  --target-type ecs \
  --protocol tcp \
  --target-port 80 \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — Using API-style command name

```bash
# Wrong: API style, not plugin mode
aliyun nis CreateAndAnalyzeNetworkPath --SourceId i-bp1xxxxx ...
```

#### INCORRECT — Missing --user-agent

```bash
# Wrong: missing --user-agent AlibabaCloud-Agent-Skills
aliyun nis create-and-analyze-network-path --source-id i-bp1xxxxx --source-type ecs
```

### 3. get-network-reachable-analysis — verify command and parameters

#### CORRECT

```bash
aliyun nis get-network-reachable-analysis \
  --network-reachable-analysis-id nra-xxxxx \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — Wrong parameter name

```bash
# Wrong: --analysis-id does not exist
aliyun nis get-network-reachable-analysis --analysis-id nra-xxxxx
```

### 4. SourceType/TargetType enum values

#### CORRECT values

- `ecs`, `internetIp`, `vsw`, `vpn`, `vbr` (for source)
- `ecs`, `internetIp`, `vsw`, `vpn`, `vbr`, `clb` (for target)

#### INCORRECT — non-existent types

```bash
# Wrong: "slb" is not valid, use "clb"
--target-type slb
# Wrong: "eip" is not valid, use "internetIp"
--source-type eip
```

### 5. CMS DescribeMetricData — verify parameters

#### CORRECT

```bash
aliyun cms DescribeMetricData \
  --Namespace acs_ecs_dashboard \
  --MetricName CPUUtilization \
  --Dimensions '[{"instanceId":"i-bp1xxxxx"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### INCORRECT — CMS uses PascalCase parameters (NOT plugin mode)

```bash
# Wrong: CMS does not have a plugin, so it uses API-style PascalCase parameters
aliyun cms describe-metric-data --namespace acs_ecs_dashboard
```

---

## Workflow Logic Criteria

### Reverse Path Port Swap

#### CORRECT

Forward: `--source-port 12345 --target-port 80`
Reverse: `--source-port 80 --target-port 12345` (ports swapped along with source/target)

#### INCORRECT

Reverse: `--source-port 12345 --target-port 80` (ports NOT swapped)

### Result Interpretation

#### CORRECT

- Use only `topologyData.positive` from the **actively initiated** reverse analysis task
- Ignore `topologyData.reverse` in any response (unreliable)

#### INCORRECT

- Relying on `topologyData.reverse` from the forward analysis response

### VPN/VBR On-Premise IP

#### CORRECT

When source/target is `vpn` or `vbr`, MUST also set `--source-ip-address` / `--target-ip-address` for the On-Premise IP.

#### INCORRECT

Only setting `--source-id` for vpn/vbr without the On-Premise IP.
