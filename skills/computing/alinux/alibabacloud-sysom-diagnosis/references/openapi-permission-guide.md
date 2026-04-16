# SysOM OpenAPI：Agent 权限引导速查

供 Agent 按步骤引导用户完成身份、策略与开通配置；与 **`precheck` JSON**、**`diagnosis`** 命令配合使用。

## 1. 会话铁律

1. 用户每次会话中若要用 **远程 SysOM 能力**（`memory … --deep-diagnosis`），**第一步**在 **sysom-diagnosis（技能根）**执行：
   ```bash
   ./scripts/osops.sh precheck
   ```
   （或 `cd scripts && ./osops.sh precheck`。首次使用需先 `./scripts/init.sh`。）
2. **precheck 通过前**，不要反复调用会走 OpenAPI 的诊断命令。
3. precheck **失败**时：根据 JSON 中的 `error.code`、`data.guidance`、`agent.findings` 引导用户；**禁止**盲目重试同一远程接口。配置完成后**再跑 precheck**，通过后再执行诊断。

## 2. 远程 OpenAPI 成功的三要素（缺一不可）

| 要素 | 含义 | 典型操作入口 |
|------|------|----------------|
| **身份** | 可调 OpenAPI 的凭证 | **AK/SK**：RAM 用户 + AccessKey；**ECS RAM Role**（推荐在 ECS 上跑 Agent）：RAM 可信 ECS 的角色 + 绑定到实例 + `aliyun configure --mode EcsRamRole` |
| **策略** | `AliyunSysomFullAccess` | RAM → 对**用户**（AK 方案）或**角色**（ECS RAM Role 方案）授权 |
| **开通与 SLR** | 账号开通 SysOM；存在服务关联角色 `AliyunServiceRoleForSysom` | 通常 [Alinux 控制台](https://alinux.console.aliyun.com/?source=cosh) 开通，**开通流程会自动创建**该 SLR；子账号若在开通过程中报无 `ram:CreateServiceLinkedRole`，见 [service-linked-role-subaccount.md](./service-linked-role-subaccount.md) |

子账号仅负责开通时：见 [service-linked-role-subaccount.md](./service-linked-role-subaccount.md)（RAM 自定义策略与组织规范以控制台为准）。

详细步骤见 [authentication.md](./authentication.md)。InvokeDiagnosis 侧要求（云助手、控制台诊断授权等）见 [invoke-diagnosis.md](./invoke-diagnosis.md)。

### 2.1 第一次使用本 CLI（环境）

1. 将完整 **sysom-diagnosis** 目录纳入工作区（含 `scripts/`、`references/`、`SKILL.md`）。
2. 在 **sysom-diagnosis（技能根）**执行一次：`./scripts/init.sh`（安装/同步 `scripts` 下依赖；若已用 `uv`/`venv` 可跳过重复执行）。
3. 确认本机可执行：`./scripts/osops.sh --help` 或 `./scripts/osops.sh precheck`（不要求一次成功，仅确认入口可用）。

### 2.4 Agent / 多段 Bash 与凭证（重要）

**安全策略**：**禁止**在对话中向用户索要或粘贴 AccessKey / Secret。Agent 应引导用户在**本地终端**执行 **`./scripts/osops.sh configure`**，由用户在终端内交互输入，密钥**不进入聊天记录**。

在 **COSH** 中，**每次 `Bash` 工具调用往往是独立进程**；上一段的 `export` **不会**传给下一段 `./scripts/osops.sh precheck`。

| 方式 | 说明 |
|------|------|
| **唯一推荐（Agent 场景）** | 在 sysom-diagnosis（技能根）执行 **`./scripts/osops.sh configure`**，写入 `~/.aliyun/config.json`。完成后**再**执行 `./scripts/osops.sh precheck`。 |
| **进阶（自动化脚本，非聊天）** | 仅在**同一 shell 进程**内：`export ALIBABA_CLOUD_ACCESS_KEY_ID=... && export ALIBABA_CLOUD_ACCESS_KEY_SECRET=... && ./scripts/osops.sh precheck`。环境变量名亦支持 `ALICLOUD_ACCESS_KEY_*`。 |

**执行环境不支持交互式配置时**（例如 Agent 调用的 Bash 无 TTY，`configure` 无法提示输入）：在 **COSH** 中可通过 **`/settings`** 使能「**交互式Shell（PTY）**」，或使用 **`/bash`** 进入交互式 Bash，再在技能根执行 **`./scripts/osops.sh configure`**。precheck 失败信封中的 **`data.guidance.credential_policy`** 含同条说明。

**禁止**引导用户「在聊天里提供 AK/SK」或「分多条消息粘贴密钥」。

### 2.2 端到端检查清单（从预检到远程诊断）

| 序号 | 动作 | 说明 |
|------|------|------|
| 1 | `./scripts/osops.sh precheck` | 会话内首次远程能力前必做；记录 `ok` 与 `error.code`。 |
| 2 | 若 `ok: false` | 按下方「分支」与场景表处理，**不要**跳过配置直接发起深度诊断。 |
| 3 | 若 `ok: true` | 再执行深度诊断：`memory … --deep-diagnosis`（维护者 OpenAPI 直调见 [invoke-diagnosis.md](./invoke-diagnosis.md)）。 |
| 4 | 诊断仍失败 | 再跑一遍 precheck；读 JSON 中 `remediation`；对照 [invoke-diagnosis.md](./invoke-diagnosis.md) 核对目标 ECS（云助手、授权等）。 |

### 2.3 precheck 失败时的分支（Agent）

- **无任何有效凭证**（环境变量与 `~/.aliyun/config.json` 均不可用）：走 **A-K1** 或 **E-R1**，见 [authentication.md](./authentication.md) 完整配置步骤。
- **有 AK 但无 SysOM 策略**：**A-K2** → RAM 为用户附加 `AliyunSysomFullAccess` → 等待策略生效 → 再 precheck。
- **`error.code == service_not_activated`**：**A-K3 / E-R4** → Alinux 控制台开通 SysOM（及 SLR）→ 等待 1～3 分钟 → 再 precheck。
- **在 ECS 上且 `instance-id` 可访问，但 `ram/security-credentials/` 为 404**：多为**未绑定实例 RAM 角色** → ECS 控制台绑定角色 + 角色附加 `AliyunSysomFullAccess` → 实例内 `aliyun configure --mode EcsRamRole` → 再 precheck。
- **`ecs_role_name` 有值但仍失败**：**E-R3** 或策略未生效 → RAM 中为**该角色**附加 `AliyunSysomFullAccess`，等待数分钟 → 再 precheck。
- **`~/.aliyun/config.json` 解析失败**：修复 JSON（或删除空文件后在技能根执行 `./scripts/osops.sh configure` 重建）→ 再 precheck。

## 3. AK/SK 路径：场景与处置

| 场景 ID | 条件摘要 | Agent 引导要点 |
|---------|----------|----------------|
| **A-K1** | 无 AK / 未配置 | RAM 创建用户 → 生成 AK/SK → 授权 `AliyunSysomFullAccess` → 配置环境变量或 `~/.aliyun/config.json` → **precheck** |
| **A-K2** | 有 AK，无 SysOM 策略 | RAM 为用户附加 **AliyunSysomFullAccess** → **precheck** |
| **A-K3** | 有 AK 与策略，**未开通** SysOM | Alinux 控制台开通 → **precheck**（对应 `error_code: service_not_activated`） |
| **A-K4** | 全部具备 | **precheck** 应通过 → 可发起深度诊断（`memory … --deep-diagnosis` 等） |

### 3.1 AK 路径详细步骤（按场景执行，不必全做）

**A-K1（无 AK / 未配置）**

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)，创建或使用已有 **RAM 用户**（禁止使用主账号 AK）。
2. 为该用户 **创建 AccessKey**，安全保存 ID 与 Secret（仅展示一次）。
3. 为该用户 **新增授权** → 搜索并附加系统策略 **`AliyunSysomFullAccess`**。
4. 配置凭证（**勿在对话中传输密钥**）：在 sysom-diagnosis（技能根）执行 **`./scripts/osops.sh configure`**；或按 [authentication.md](./authentication.md) 编辑 `~/.aliyun/config.json`（`mode: AK`）。进阶用户可在**同一 shell** 内使用环境变量（见 §2.4）。  
5. 在 **sysom-diagnosis（技能根）**执行：`./scripts/osops.sh precheck`，确认 `ok: true`。

**A-K2（有 AK，无 SysOM 策略）**

1. RAM → 用户 → 找到该用户 → **添加权限** → 附加 **`AliyunSysomFullAccess`**。  
2. 等待约 **2～5 分钟** 策略生效。  
3. 再执行 `./scripts/osops.sh precheck`。

**A-K3（有 AK 与策略，未开通 SysOM）**

1. 使用有权限的账号打开 [Alinux / SysOM 开通入口](https://alinux.console.aliyun.com/?source=cosh)，按页面完成 **SysOM 开通**；开通向导通常会**自动**创建服务关联角色 **AliyunServiceRoleForSysom**，一般无需在控制台外单独创建。  
2. 子账号若在开通步骤报无 `CreateServiceLinkedRole` 等权限，见 [service-linked-role-subaccount.md](./service-linked-role-subaccount.md)。  
3. 开通后等待 **1～3 分钟**，再 `./scripts/osops.sh precheck`。

**A-K4**

1. 直接 `./scripts/osops.sh precheck` 应通过；若仍失败，对照 `error.code` 与 `agent.findings` 是否账号不一致或区域/API 异常。

## 4. ECS RAM Role 路径：场景与处置

| 场景 ID | 条件摘要 | Agent 引导要点 |
|---------|----------|----------------|
| **E-R1** | 无角色 / 未绑 ECS | RAM 创建 ECS 信任角色 → 授权 **AliyunSysomFullAccess** → ECS 绑定实例（可 OOS 批量）→ `aliyun configure --mode EcsRamRole --ram-role-name <角色名>` → **precheck** |
| **E-R2** | 有角色，**未关联**实例 | ECS 控制台绑定 RAM 角色 → **precheck** |
| **E-R3** | 已绑 ECS，角色**无** `AliyunSysomFullAccess` | RAM 为**角色**授权 → **precheck** |
| **E-R4** | 身份与策略齐，**未开通** SysOM | Alinux 开通 → **precheck** |

### 4.1 ECS RAM Role 详细步骤（按场景）

**E-R1（无角色 / 未绑 ECS）**

1. RAM → **创建角色** → 可信服务类型选 **云服务器 ECS** → 记录角色名。  
2. 为该角色附加 **`AliyunSysomFullAccess`**。  
3. [ECS 控制台](https://ecs.console.aliyun.com/) → 目标实例 → **更多** → **绑定 RAM 角色** → 选择上述角色。  
4. SSH 登录实例，执行：  
   `aliyun configure --mode EcsRamRole --ram-role-name <角色名>`  
   （或按 [authentication.md](./authentication.md) 手写 `~/.aliyun/config.json` 的 `EcsRamRole` 段。）  
5. 验证：`curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/` 应返回**一行角色名**。  
6. 在 **sysom-diagnosis（技能根）**执行 `./scripts/osops.sh precheck`。

**E-R2（有角色，未关联当前实例）**

1. ECS 控制台 → 实例详情 → 绑定 RAM 角色（或更换为正确角色）。  
2. 若需，在实例内重跑 `aliyun configure --mode EcsRamRole --ram-role-name <角色名>`。  
3. `./scripts/osops.sh precheck`。

**E-R3（已绑 ECS，角色无 AliyunSysomFullAccess）**

1. RAM → **角色** → 选中该角色 → **新增授权** → `AliyunSysomFullAccess`。  
2. 等待策略生效后 `./scripts/osops.sh precheck`。

**E-R4（与 A-K3 类似，开通 SysOM）**

1. Alinux 控制台完成 SysOM 开通（SLR 通常随开通流程自动创建）。  
2. `./scripts/osops.sh precheck`。

## 5. precheck 输出如何读（给 Agent）

- `ok: true`：可继续发起深度诊断（`memory … --deep-diagnosis`）；仍须满足 InvokeDiagnosis 侧：**云助手、控制台诊断授权** 等，见 [invoke-diagnosis.md](./invoke-diagnosis.md)）。
- `ok: false`：
  - `error.code == service_not_activated` → 对齐 **A-K3 / E-R4**：引导 Alinux 开通后再 **precheck**。
  - 无有效凭证 / API 失败 → 对齐 **A-K1 / A-K2 / E-R1–E-R3**：读 `agent.findings`、`data.suggestion`，并打开 [authentication.md](./authentication.md)。
  - `data.ecs_role_name` 有值但失败 → 重点检查角色是否附加 **AliyunSysomFullAccess** 及 CLI 是否为 EcsRamRole 模式。

## 6. 远程诊断命令失败时

若深度诊断（`memory … --deep-diagnosis` 等）返回失败：

1. 先让用户重新执行 **`./scripts/osops.sh precheck`**。
2. 若仍为 OpenAPI/权限类错误，对照本节与 [authentication.md](./authentication.md)。
3. 若提示实例未授权或诊断无法下发：在 **SysOM/ECS 控制台** 对目标实例完成诊断授权（勿使用已废弃的 OpenAPI 授权接口）；参数与前置见 [invoke-diagnosis.md](./invoke-diagnosis.md)。

## 7. CLI 失败时的常见字段

CLI 在失败时尽量附带：

- `error.code`：机器可读
- `data.guidance` 或 `data.remediation`：有序步骤或文档指针（含 **`credential_policy`**、**`configure_command`**、**`guided_steps`**）
- `data.precheck_command`：建议复跑的预检命令

## 8. `error.code` 与处置速查

| `error.code`（示例） | 含义倾向 | 建议操作顺序 |
|---------------------|----------|--------------|
| `auth_failed` | 无有效凭证或 InitialSysom 未通过 | 先 A-K* / E-R* 与 [authentication.md](./authentication.md)，再 precheck |
| `service_not_activated` | SysOM 未开通或账号侧未就绪 | Alinux 开通 → 等待 → precheck |
| （diagnosis 返回）权限类 | 三要素缺一或实例侧未授权 | precheck → openapi 本页 → invoke-diagnosis |

具体文案以当次 JSON 的 `agent.findings`、`data.remediation` 为准。

## 9. SysOM 开通与服务关联角色（摘要）

1. **主账号或有权限的 RAM 用户**登录 [Alinux 控制台](https://alinux.console.aliyun.com/?source=cosh)，完成 **SysOM 产品开通**；开通流程通常会**自动**创建服务关联角色 **`AliyunServiceRoleForSysom`**。  
2. 子账号若在开通向导中报无 `ram:CreateServiceLinkedRole` 等权限，详见 [service-linked-role-subaccount.md](./service-linked-role-subaccount.md)。  
3. 开通完成后 **等待 1～3 分钟**，再执行 `./scripts/osops.sh precheck`。  
4. 仍报未开通时：确认当前使用的 **AK 或 RAM 角色所属账号**与开通控制台登录账号一致（避免跨账号）。

## 10. 远程深度诊断命令失败时的补充步骤

1. **再次** `./scripts/osops.sh precheck`，排除凭证与开通问题。  
2. 阅读本次 **stdout JSON** 全文：`error`、`data`、`agent.summary`。  
3. 对照 [invoke-diagnosis.md](./invoke-diagnosis.md)：地域、实例 ID、`service_name`、`channel`、目标机云助手与 **控制台诊断授权** 等前置条件。  
4. 若 API 明确提示授权类错误，在控制台对目标 ECS 完成 SysOM/诊断相关授权后重试。  
5. 避免在相同错误信息下仅重复相同参数调用。
