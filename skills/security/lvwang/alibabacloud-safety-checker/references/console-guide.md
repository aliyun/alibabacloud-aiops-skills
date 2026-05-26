# 控制台自动化操作指南

## 前置条件

1. 已安装 `agent-browser`（运行 `agent-browser install`）
2. 已配置阿里云默认凭证链（环境变量或 credentials 文件）
3. RAM 用户已授予 `AliyunYundunGreenWebFullAccess` 权限

## 操作流程

### 1. 登录控制台

```bash
agent-browser --session contentsec close 2>/dev/null
sleep 1
agent-browser --headed --session contentsec open "https://signin.aliyun.com"

# 等待用户在浏览器中完成登录（扫码/密码/短信）
# 登录成功后保存状态
agent-browser --session contentsec state save ~/.qoderwork/contentsec_console_state.json
```

### 2. 导航到规则配置

```bash
agent-browser --session contentsec open "https://yundun.console.aliyun.com/?p=contentsec#/green/textEnhanced"
agent-browser --session contentsec wait --load networkidle
```

### 3. 复制 Service

在 Service 列表中找到基础 Service（如 `ugc_moderation_byllm`），点击操作列的"复制"按钮，填写新服务名称（格式：`基础服务_场景名`，如 `ugc_moderation_byllm_game_chat`）。

### 4. 配置标签开关

1. 在新创建的 Service 行，点击"设置规则"
2. 进入规则详情页，点击"编辑"进入编辑模式
3. 逐个配置 30 个标签的开关状态（开启/关闭）
4. 点击"保存"，等待 2-5 分钟生效

### 5. 自动化方式

使用 `console_automator.py` 脚本自动完成以上所有步骤：

```bash
python3 console_automator.py --scenario <场景ID>
```

该脚本会：
- 自动打开控制台（如已有保存的登录状态则自动恢复）
- 引导用户完成首次登录
- 导航到规则配置页
- 复制 Service 并命名
- 按场景配置矩阵逐个设置标签开关
- 保存配置并提示生效时间

### 6. 验证配置

配置完成后，可通过以下 API 调用验证：

```bash
python3 verify_auth.py
```

或直接运行一次测试验证：

```bash
python3 main.py run --samples <样本文件> --text-services <自定义Service名>
```

## 注意事项

- 控制台页面结构可能变化，自动化脚本基于当前版本设计
- 如果自动化失败，生成 Markdown 操作指南引导用户手动完成
- 每次控制台配置前必须向用户确认
- 登录状态保存后，后续使用无需重新登录

---

## AI安全护栏控制台配置

> **重要**：AI安全护栏和内容安全是两个独立入口，不要混淆。

| 入口 | URL | 用途 |
|------|-----|------|
| 内容安全控制台 | https://yundunnext.console.aliyun.com/?p=cts | 机器审核增强版、文本/图片/视频审核配置 |
| AI安全护栏控制台 | https://yundun.console.aliyun.com/?p=guardrail | AI输入/输出内容检测、Agent日志检测 |

### 1. 开通与授权

1. 前往 [AI安全护栏产品页](https://www.aliyun.com/product/lvwang) 开通（按量后付费）
2. RAM 用户需要 `AliyunYundunGreenWebFullAccess` 权限（与内容安全共用同一权限策略）

### 2. 三大检测维度配置

| 维度 | 默认状态 | 开启路径 | 计费 |
|------|---------|---------|------|
| 内容合规 | 默认启用 | 无需配置 | 含基础调用 |
| 敏感内容检测 | 默认关闭 | 防护配置 → 检测项配置 → 开启"敏感内容检测" | 单独计费 |
| 提示词攻击检测 | 默认关闭 | 防护配置 → 检测项配置 → 开启"提示词攻击检测" | 单独计费 |

### 3. 验证配置生效

```bash
# 快速验证三维度是否开启
python3 ai_guardrail.py --service query

# 查看返回字段:
# - SensitiveLevel 不再为空 → 敏感内容检测已开启
# - AttackLevel 不再为空 → 攻击检测已开启
```

### 4. Pro版 Service 说明

| Service名 | 说明 |
|-----------|------|
| `query_security_check` | AI输入检测（标准版） |
| `response_security_check` | AI生成检测（标准版） |
| `query_guard_pro_ec` | AI输入检测（Pro版） |
| `response_guard_pro_ec` | AI生成检测（Pro版） |
| `agent_log_guard_ec` | Agent日志检测 |
| `query_security_check_cb` | AI输入检测（出海版） |
| `response_security_check_cb` | AI生成检测（出海版） |

---

## CLI 快速调试

> 适用场景：没有 Python 环境、或需要在终端快速验证单条内容的审核结果。
> CLI 与 Python SDK 调用同一组后端 API，不作为自动化链路的备用通道。

### 前置条件

1. 安装阿里云 CLI：`brew install aliyun-cli`（macOS）或参考 [官方文档](https://help.aliyun.com/zh/cli/install-cli)
2. 配置凭证（依赖默认凭证链，CLI 自动从环境获取凭证）：
   ```bash
   aliyun configure set \
     --profile content-sec \
     --mode ChainableRamRoleArn \
     --region cn-shanghai
   ```

### 文本审核

```bash
# 基础文本审核增强版
aliyun green text-moderation-plus \
  --region cn-shanghai \
  --Service ugc_moderation_byllm \
  --ServiceParameters '{"content":"待检测文本"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"

# 指定场景 Service（如自定义的游戏聊天场景）
aliyun green text-moderation-plus \
  --region cn-shanghai \
  --Service ugc_moderation_byllm_game_chat \
  --ServiceParameters '{"content":"测试内容","dataId":"debug_001"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"
```

### 图片审核

```bash
aliyun green image-moderation \
  --region cn-shanghai \
  --Service baselineCheck \
  --ServiceParameters '{"imageUrl":"https://cdn.pixabay.com/photo/xxx.jpg"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"
```

### AI安全护栏

```bash
# 输入检测（Pro版）
aliyun green text-moderation \
  --region cn-shanghai \
  --Service query_guard_pro_ec \
  --ServiceParameters '{"content":"用户输入的prompt内容"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"

# 输出检测（Pro版）
aliyun green text-moderation \
  --region cn-shanghai \
  --Service response_guard_pro_ec \
  --ServiceParameters '{"content":"模型生成的回复内容"}' \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-safety-checker"
```

### 返回结果解读

```json
{
  "Code": 200,
  "Data": {
    "Labels": "sexual_content",
    "RiskLevel": "high",
    "Reason": "{\"riskTips\":\"色情_低俗词\",\"riskWords\":\"xxx\"}"
  },
  "Message": "OK",
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

关键字段：`Labels`（命中标签）、`RiskLevel`（none/low/medium/high）、`Reason`（命中详情 JSON）。

### 常用调试技巧

- 加 `--output json` 强制 JSON 输出（默认即 JSON）
- 加 `--read-timeout 30` 处理大文本/图片时延长超时
- 多 Region 对比：将 `--region` 换成 `cn-beijing` 测试不同接入点
- 查看可用 API 列表：`aliyun green --help`
