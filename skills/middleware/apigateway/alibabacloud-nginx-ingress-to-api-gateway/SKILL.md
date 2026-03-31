---
name: alibabacloud-nginx-ingress-to-api-gateway
description: |
  Alibaba Cloud APIG Migration Skill. Migrate Kubernetes nginx Ingress resources to Alibaba Cloud API Gateway (APIG, ingressClass: apig).
  Users provide Ingress YAML (paste, file, or directory) — no cluster access required for analysis.
  Covers annotation compatibility classification, Higress native mapping, built-in plugin selection, custom WasmPlugin development, migrated Ingress YAML generation, and migration report with deployment guide.
  Triggers: "nginx ingress migration", "APIG compatibility", "gateway migration", "ingress-nginx to APIG", "nginx迁移", "网关迁移", "Ingress兼容性分析", "APIG迁移", "迁移评估", "annotation兼容性", "WasmPlugin开发".
---

# Nginx Ingress to APIG Migration

## Scenario Description

Migrate Kubernetes nginx Ingress resources to Alibaba Cloud API Gateway (APIG). APIG is an Envoy-based gateway (Higress) that uses `ingressClassName: apig`. This skill classifies every `nginx.ingress.kubernetes.io/*` annotation into Compatible / Ignorable / Unsupported, resolves unsupported annotations via a four-level decision tree (Higress native → safe-to-drop → built-in plugin → custom WasmPlugin), generates migrated Ingress YAML, and produces a deployment-ready migration report.

**Architecture**: `nginx Ingress Controller → APIG (Envoy/Higress) + optional WasmPlugin (Go, proxy-wasm-go-sdk)`

The core analysis workflow operates entirely offline on user-provided YAML — no cluster access, CLI tools, or cloud credentials required.

## Installation

This skill operates entirely offline on user-provided YAML. No CLI tools, SDKs, or cloud credentials are required.

On-demand tools (only when the workflow reaches a step that needs them):

| Tool | When needed | Check command | Minimum version |
|------|------------|---------------|-----------------|
| jq | Script-based offline analysis | `jq --version` | >= 1.6 |
| python3 + PyYAML | YAML parsing (alternative to yq) | `python3 -c "import yaml; print(yaml.__version__)"` | python3 >= 3.8, PyYAML >= 5.0 |
| yq | YAML parsing (alternative to python3+PyYAML) | `yq --version` | >= 4.0 |
| Go | Step 3 determines a custom WasmPlugin is needed | `go version` | >= 1.24 |
| Docker | Custom WasmPlugin needs to be built as OCI image | `docker version` | — |

> **Do NOT pre-check or prompt installation of any tool during analysis.**

## Environment Variables

No environment variables required. This skill does not invoke any cloud APIs or CLI tools.

## Authentication

Not applicable. This skill does not invoke Alibaba Cloud APIs or CLI. No credentials are needed.

## RAM Policy

Not applicable. This skill operates entirely on local YAML files and does not call any cloud APIs.

## Parameter Confirmation

> **This skill only performs analysis and code generation — it does NOT execute any deployment or cluster write operations.**
>
> When the user provides Ingress YAML, proceed immediately with the full workflow (Step 1→5) and output the complete result. Do NOT ask for RegionId, OCI registry, or any other parameter. Use `<REGION>` and `<YOUR_REGISTRY>` placeholders in the output.
>
> **请避免以下交互模式，直接执行对应操作即可：**
> - "是否需要我分析这个 Ingress？" — 建议直接分析
> - "是否需要生成迁移后的 YAML？" — 建议直接生成
> - "是否需要创建迁移配置文件/检查清单？" — 建议直接创建
> - "是否需要开发 WasmPlugin？" — 如果决策树判定需要，建议直接开发
> - "请确认 RegionId / OCI 地址" — 建议使用占位符

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|------------------|-------------|---------------|
| Ingress YAML | Required | nginx Ingress YAML to migrate (paste, file, or directory) | — |

> **When Ingress YAML is not provided**: If the user asks about migration but does not provide YAML,
> respond with: "请提供需要迁移的 nginx Ingress YAML（可以直接粘贴、提供文件路径或目录路径）。"
> Do NOT abort the conversation — guide the user to provide the required input.

## Core Workflow

> **建议：收到 YAML 后一次性完成全部分析步骤**
>
> **当用户提供 Ingress YAML 时，建议立即执行全部步骤（Step 1→5）并在一次响应中输出完整结果。**
> - 对于未指定的参数（如 RegionId、OCI registry），使用 `<REGION>` 等占位符
> - 收到 YAML 后直接进入分析流程，无需额外确认
> - 各步骤之间连续执行，无需中途暂停询问用户
> - 迁移配置文件和检查清单作为标准输出的一部分自动生成
> - 整个工作流是确定性的：YAML 输入 → 完整迁移报告输出，无需中间确认
> - 唯一必需的输入是 Ingress YAML 本身

### Step 1: Parse Ingress YAML

Accept YAML from any of the following input formats:
- Direct paste in conversation (with or without markdown code fences)
- File path (e.g., `ingress.yaml`, `./k8s/ingress.yaml`)
- Directory path (scan all `.yaml`/`.yml` files for Ingress resources)
- Multi-document YAML (separated by `---`)
- Partial YAML (missing `apiVersion`/`kind` — infer as Ingress if `annotations` with `nginx.ingress.kubernetes.io/*` are present)

For each Ingress found, extract all `nginx.ingress.kubernetes.io/*` annotations.

> **If the user's message mentions migration/analysis but does NOT include any YAML**, respond with:
> "请提供需要迁移的 nginx Ingress YAML（可以直接粘贴、提供文件路径或目录路径）。"
> Do NOT abort or error out — guide the user to provide input.

### Step 2: Classify Annotations

Classify each annotation into exactly one of three categories. See `references/annotation-mapping.md` for the complete 117-annotation lookup table.

| Category | Count | Action | Example |
|----------|-------|--------|---------|
| **Compatible** | 50 | Keep in migrated YAML | `rewrite-target`, `enable-cors`, `canary-weight`, `ssl-redirect` |
| **Ignorable** | 16 | Strip (Envoy handles natively) | `proxy-connect-timeout`, `proxy-buffering`, `proxy-body-size` |
| **Unsupported** | 51 | Strip → resolve via decision tree | `auth-url`, `server-snippet`, `limit-rps` |

**Inline Quick Lookup — High-Frequency Annotations:**

| Annotation | Category | Action |
|-----------|----------|--------|
| `rewrite-target` | ✅ Compatible | Keep |
| `enable-cors` | ✅ Compatible | Keep |
| `cors-allow-origin` | ✅ Compatible | Keep |
| `ssl-redirect` | ✅ Compatible | Keep |
| `canary` / `canary-weight` / `canary-by-header` | ✅ Compatible | Keep |
| `whitelist-source-range` | ✅ Compatible | Keep |
| `backend-protocol` | ✅ Compatible | Keep |
| `use-regex` | ✅ Compatible | Keep |
| `upstream-vhost` | ✅ Compatible | Keep |
| `proxy-connect-timeout` | ⚪ Ignorable | Strip |
| `proxy-read-timeout` | ⚪ Ignorable | Strip |
| `proxy-send-timeout` | ⚪ Ignorable | Strip |
| `proxy-body-size` | ⚪ Ignorable | Strip |
| `proxy-buffering` | ⚪ Ignorable | Strip |
| `client-body-buffer-size` | ⚪ Ignorable | Strip |
| `auth-url` | ❌ Unsupported | WasmPlugin (HTTP callout) |
| `server-snippet` | ❌ Unsupported | WasmPlugin (directive conversion) |
| `configuration-snippet` | ❌ Unsupported | WasmPlugin (directive conversion) |
| `limit-rps` | ❌ Unsupported | Built-in `key-rate-limit` plugin |
| `limit-connections` | ❌ Unsupported | Built-in `key-rate-limit` plugin |
| `enable-modsecurity` | ❌ Unsupported | Built-in `waf` plugin |
| `denylist-source-range` | ❌ Unsupported | Higress native `higress.io/blacklist-source-range` |
| `service-upstream` | ❌ Unsupported | Safe to drop (Envoy default behavior) |
| `ssl-ciphers` | ❌ Unsupported | Rename to `ssl-cipher` (compatible) |

> **If an annotation is NOT in the above table**, look it up in `references/annotation-mapping.md`. If still not found, classify as Unsupported and resolve via the decision tree in Step 3.

**Special value changes** (compatible but value must change):
- `load-balance: ewma` → `round_robin` (APIG does not support EWMA)
- `ssl-ciphers` → rename to `ssl-cipher` (singular form)
- `affinity-mode: persistent` → `balanced` (APIG only supports balanced)

### Step 3: Resolve Unsupported Annotations

For each unsupported annotation, follow this decision tree in order:

```
1. Higress native annotation?  → Use native equivalent (no WasmPlugin needed)
2. Safe to drop?               → Remove without replacement
3. Built-in platform plugin?   → Use built-in OCI image via higress.io/wasmplugin annotation
4. None of the above?          → Develop custom WasmPlugin
```

See `references/migration-patterns.md` for the complete decision tree, and `references/builtin-plugins.md` for the built-in plugin catalog.

**Higress native mappings:**

| nginx annotation | Higress equivalent |
|-----------------|-------------------|
| `denylist-source-range` | `higress.io/blacklist-source-range` |
| `mirror-target` | `higress.io/mirror-target-service` + `higress.io/mirror-percentage` |

**Safe-to-drop:** `service-upstream`, `enable-access-log`, `proxy-request-buffering: off`, `connection-proxy-header`

**Built-in plugins:** `limit-rps`/`limit-connections` → `key-rate-limit`, `enable-modsecurity` → `waf`. See `references/builtin-plugins.md`.

**Custom WasmPlugin (last resort):** `auth-url`, `server-snippet`, `configuration-snippet`, etc. See `references/wasm-plugin-sdk.md` for SDK reference, `references/snippet-patterns.md` for conversion patterns.

### Step 4: Generate Migrated Ingress YAML

For each input Ingress, generate a migrated copy:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: <original-name>-apig
  namespace: <original-namespace>
  annotations:
    # Compatible annotations preserved
    # Unsupported annotations replaced with higress.io/wasmplugin if needed
spec:
  ingressClassName: apig    # MUST be hardcoded to apig
  rules: ...                # Preserved from original
  tls: ...                  # Preserved from original
```

### Step 5: Output Migration Report

> 所有输出建议使用中文（中文）。包括分析表、迁移总结、后续操作指南及所有说明性文字。代码块（YAML、Go、bash）保持原始语法。
>
> 以下所有内容均为标准输出项，建议在一次响应中完整输出，无需逐项询问用户。

Output ALL of the following for each Ingress:

1. **兼容性分析表** — annotation, value, category (兼容/可忽略/不支持), action
2. **迁移后的 Ingress YAML** — ready for user to apply
3. **自定义 WasmPlugin 源码** — if Step 3 determined custom plugins are needed (skip only if no custom plugin is needed)
4. **迁移总结** — what changed, value changes, plugins needed
5. **后续操作指南** — 根据兼容性分析结果，分场景告知用户完整的迁移操作路径：
   - **完全兼容（无不兼容注解）**：所有注解均为兼容或可忽略类型，用户可直接参考 [Nginx Ingress 迁移到云原生 API 网关](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway) 完成迁移。
   - **不完全兼容（存在不兼容注解）**：按以下顺序操作：
     1. 构建并推送自定义 WasmPlugin OCI 镜像
     2. 将迁移后 Ingress YAML 中的 OCI URL 占位符替换为真实的 WasmPlugin 镜像地址
     3. 将替换后的 Ingress YAML 部署到集群中
     4. 参考 [Nginx Ingress 迁移到云原生 API 网关](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway) 继续后续操作，在步骤一「指定 IngressClass」处需指定为 `apig`
     5. **网关版本要求**：使用 WasmPlugin 需确保云原生 API 网关版本在 **2.1.16 及以上**，否则需要升级版本或创建新网关

See `references/deployment-guide-template.md` for the guide template.

> **Scope boundary**: This skill generates all artifacts and instructions. It does NOT execute `kubectl apply`, `docker push`, or any cluster/registry write operations. Those are left to the user.
> **No confirmation needed**: Every item above is always generated. Never ask "是否需要生成迁移文件/检查清单/部署指南？"

## Success Verification Method

See `references/verification-method.md` for verification steps to include in the migration report.

The migration report should instruct the user to verify with:
```bash
# Validate migrated YAML syntax (user runs this)
kubectl apply --dry-run=client -f <migrated-ingress>.yaml

# Confirm ingressClassName is apig
grep "ingressClassName: apig" <migrated-ingress>.yaml
```

> This skill outputs verification instructions for the user. It does NOT execute these commands.

## Cleanup

Not applicable. This skill only generates text output (YAML, Go source code, migration report). No cloud resources or cluster objects are created by this skill.

## API and Command Tables

This skill does not execute any CLI commands or API calls. All output is text-based (YAML, Go source code, migration report with instructions for the user).

## Best Practices

1. Always classify ALL annotations before generating migrated YAML — never skip annotations
2. Use placeholders (`<REGION>`, `<YOUR_REGISTRY>`) for unspecified parameters; never hardcode user-specific values
3. Preserve original `rules`, `tls`, and `namespace` in migrated YAML
4. Add `-apig` suffix to migrated Ingress name for easy identification
5. Prefer built-in plugins over custom WasmPlugin — check `references/builtin-plugins.md` first
6. For custom WasmPlugin, use `github.com/higress-group/wasm-go/pkg/wrapper` SDK exclusively
7. Track annotation value changes (e.g., `ewma` → `round_robin`) explicitly in the report
8. For `server-snippet`/`configuration-snippet`, enumerate every directive and verify 1:1 conversion completeness
9. Never execute cluster write operations (`kubectl apply`, `docker push`, etc.) — only output instructions for the user

## Reference Links

| Reference | Contents |
|-----------|----------|
| `references/annotation-mapping.md` | Complete 117-annotation compatibility lookup table |
| `references/migration-patterns.md` | Decision tree, Higress native mappings, safe-to-drop list, special handling |
| `references/builtin-plugins.md` | APIG built-in platform plugins catalog with OCI URLs |
| `references/platform-oci-registry.md` | Region-specific OCI registry addresses for built-in plugins |
| `references/snippet-patterns.md` | server-snippet / configuration-snippet → WasmPlugin conversion patterns |
| `references/wasm-plugin-sdk.md` | Higress WASM Go Plugin SDK reference (core API) |
| `references/wasm-http-client.md` | WasmPlugin HTTP client patterns (external auth, callouts) |
| `references/wasm-redis-client.md` | WasmPlugin Redis client patterns (rate limiting, session) |
| `references/wasm-advanced-patterns.md` | Advanced WasmPlugin patterns (streaming, tick, leader election) |
| `references/wasm-local-testing.md` | Local WasmPlugin testing with Docker Compose |
| `references/plugin-deployment.md` | WasmPlugin build, OCI push, and Ingress annotation binding |
| `references/deployment-guide-template.md` | Migration report deployment guide template |
| `references/acceptance-criteria.md` | Testing acceptance criteria with correct/incorrect patterns |
| `references/verification-method.md` | Success verification steps and commands |
| `references/security-review-policy.md` | 定期安全复审策略与检查项 |
| `references/security-impact-assessment.md` | 安全影响评估与数据处理流程 |
| `references/ram-policies.md` | RAM 权限声明（本 Skill 无需任何权限） |
