# WAF 3.0 OpenAPI 参数规范

> 本文档是 WAF 只读诊断的**权威参数参考**。构造任何 API 请求时，必须严格按照本文档的字段定义和示例格式。
>
> **注意**: 本 Skill 为只读模式,所有 API 调用均使用 `--profile` 参数,不显式传入 AK/SK。

---

## 1. 通用约束

- **凭证使用**: 所有 CLI 命令使用 `--profile <profile-name>` 和 `--user-agent AlibabaCloud-Agent-Skills`
- **名称约束**: 所有规则名称和防护模版名称中**不能包含空格**
- **status 字段**: 所有 `status` 字段的值为 **整数** `0` 或 `1`

---

## 2. DescribeInstance

获取当前账号下的 WAF 实例信息。

### 请求参数

无必填参数。

### CLI 示例

```bash
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region <region> \
  --profile <profile-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

从返回 JSON 中提取 `InstanceId` 字段。

### 返回关键字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| InstanceId | string | WAF 实例 ID |

---

## 3. DescribeDefenseResourceTemplates

查询防护对象已绑定的防护模版。

### 请求参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| InstanceId | string | 是 | WAF 实例 ID |
| Resource | string | 是 | 防护对象名称 |

### 返回关键字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| Templates[].TemplateId | integer | 模版 ID |
| Templates[].TemplateName | string | 模版名称 |
| Templates[].DefenseScene | string | 防护场景 |
| Templates[].TemplateType | string | user_default / user_custom |
| Templates[].TemplateStatus | integer | 0=关闭, 1=开启 |

### CLI 示例

```bash
aliyun waf-openapi describe-defense-resource-templates \
  --version 2021-10-01 --force --region <region> \
  --profile <profile-name> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' --Resource '<resource>'
```

---

## 4. DescribeDefenseRules

查询防护规则配置。

### 请求参数

| 名称 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| InstanceId | string | 是 | WAF 实例 ID |
| Query | string | 是 | JSON 格式查询条件,如 `{"templateId":<id>}` 或 `{"ruleId":<id>}` |
| RuleType | string | 否 | 防护场景类型,白名单场景必须指定 `whitelist` |

### 返回关键字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| Rules[].RuleId | integer | 规则 ID |
| Rules[].RuleName | string | 规则名称 |
| Rules[].Status | integer | 0=关闭, 1=开启 |
| Rules[].Config | object | 规则配置详情 |

### CLI 示例

#### 4.1 查询模版下的规则

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --profile <profile-name> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' \
  --Query '{"templateId":<template_id>}' \
  --RuleType '<defense_scene>'
```

> **API 陷阱**: 白名单(whitelist)场景必须加 `--RuleType whitelist`,否则查询结果为 0 条。

#### 4.2 按 ruleId 查询规则

```bash
aliyun waf-openapi describe-defense-rules \
  --version 2021-10-01 --force --region <region> \
  --profile <profile-name> \
  --user-agent AlibabaCloud-Agent-Skills \
  --InstanceId '<instance_id>' \
  --Query '{"ruleId":<rule_id>}'
```

---

## 5. 防护场景 DefenseScene 取值

| 取值 | 含义 |
| --- | --- |
| waf_group | 基础防护 |
| waf_base | 新版 Web 核心防护 |
| antiscan | 扫描防护 |
| ip_blacklist | IP 黑名单 |
| custom_acl | 自定义规则 |
| whitelist | 白名单 |
| region_block | 区域封禁 |
| custom_response | 老版自定义响应 |
| cc | CC 防护 |
| tamperproof | 网页防篡改 |
| dlp | 信息泄露防护 |
| spike_throttle | 洪峰限流 |

---

## 6. 规则配置 Config 结构

### 6.1 通用结构

```json
{
  "name": "规则名称",
  "status": 1,
  "conditions": [...],
  "action": {...}
}
```

### 6.2 Condition 结构

```json
{
  "key": "字段名",
  "op": "操作符",
  "opValue": "匹配值"
}
```

**常用 key**:
- `ip`: 客户端IP
- `uri`: 请求URI
- `host`: 请求域名
- `user_agent`: User-Agent

**常用 op**:
- `contain`: 包含
- `not-contain`: 不包含
- `eq`: 等于
- `ne`: 不等于

### 6.3 Action 结构

```json
{
  "type": "动作类型",
  "value": "动作值"
}
```

**type 取值**:
- `block`: 拦截
- `pass`: 放行
- `captcha`: 滑块验证
- `js`: JS验证

---

## 7. SLS 日志字段参考

查询 WAF 日志时的关键字段:

| 字段 | 含义 |
|------|------|
| `matched_host` | **防护对象**（WAF 匹配的防护对象名称） |
| `host` | 请求域名 |
| `real_client_ip` | 客户端真实 IP |
| `request_path` | 请求路径 |
| `request_method` | 请求方法 |
| `status` | WAF 返回状态码 |
| `final_plugin` | 触发模块（waf/cc/customrule 等） |
| `final_rule_id` | 触发规则 ID |
| `waf_rule_type` | 触发规则类型 |
| `waf_action` | WAF 动作（block/pass） |
| `request_traceid` | 请求追踪 ID |

> **注意**: `waf_hit` 字段在部分日志中不存在,查询时请勿包含。

---

## 8. key 与 opValue 兼容性速查

| key | 支持的 op | opValue 示例 |
|-----|-----------|--------------|
| ip | contain, not-contain | `1.2.3.4`, `1.2.3.0/24` |
| uri | contain, not-contain, eq, ne | `/api/login` |
| host | contain, eq | `example.com` |
| user_agent | contain, not-contain | `Mozilla/5.0` |

**重要**:
- 白名单(whitelist)场景下 IP 只允许 `contain` 和 `not-contain`,**禁止使用 `eq`**
- **不要使用 `inl` 操作符**
