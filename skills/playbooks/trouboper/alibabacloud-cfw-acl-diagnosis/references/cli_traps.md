# 阿里云云防火墙 CLI 陷阱与注意事项

本文档记录在使用阿里云 CLI 诊断云防火墙时遇到的坑和解决方案。

> ⚠️ 本 Skill 为只读诊断工具，本文档仅覆盖查询类命令的陷阱，不包含写操作。

---

## 1. Region 问题

### 误区：需要询问 Region

**事实**：
- 云防火墙是**全局服务**，规则配置与 Region 无关
- 使用任意 Region（如 `cn-hangzhou`）调用 API 即可
- **不需要询问用户资产所在的 Region**

---

## 2. 资产防护状态诊断陷阱

### 陷阱：规则存在但不生效 → 忘记检查 ProtectStatus

**现象**：
- 规则列表中能查到对应 ACL 规则
- 但流量仍然没有被规则控制

**根因**：
- 资产的 `ProtectStatus` 为 `closed`（未开启防护）
- 防护未开启时规则不生效，这是最常见问题

**诊断方法**：
```bash
aliyun cloudfw describe-asset-list --CurrentPage 1 --PageSize 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cfw-acl-diagnosis
```

查看 `ProtectStatus` 字段：
- `open`：防护已开启 ✅
- `closed`：防护未开启 ❌ → 告知用户需在控制台手动开启

---

## 3. 引擎模式诊断陷阱

### 陷阱：域名规则在宽松模式下不生效 → 忘记检查 EngineMode/StrictMode

**现象**：
- 配置了 `DestinationType=domain` 的规则
- 但访问目标域名时规则不命中

**根因**：
- 互联网防火墙资产 `EngineMode=loose`，或 NAT 防火墙 `StrictMode=0`
- 宽松模式下域名**不参与匹配**，仅四元组（源IP+目的IP+端口+协议）匹配

**诊断方法**：
- 互联网防火墙：`describe-asset-list` → 查看目标资产的 `EngineMode` 字段
- NAT 防火墙：`describe-nat-firewall-list` → 查看 `StrictMode` 字段

**告知用户**：需在控制台将引擎模式切换为严格模式，才能让域名规则生效。

---

## 4. NAT 防火墙 SNAT 源 IP 陷阱

### 陷阱：规则源地址与实际流量源 IP 不匹配

**现象**：
- NAT 规则配置了内网 IP 段，但规则命中次数为 0

**根因**：
- NAT 防火墙检测的是 SNAT **转换后**的公网 IP，不是内网私网 IP
- 规则源地址必须配置 SNAT 后的实际出口 IP

**诊断方向**：
- 告知用户通过 NAT 网关控制台查看 SNAT 表，确认实际出口 IP
- 对比规则 Source 地址与 SNAT 出口 IP 是否匹配

---

## 5. 流量日志查询陷阱

### 陷阱：设置 FlowType 导致无结果

**现象**：查询流量日志返回空，但实际有流量

**根因**：`FlowType` 参数过滤掉了部分流量

**正确做法**：**不要设置 `FlowType` 参数**，保持为空即可查询所有流量。

### 陷阱：时间戳单位

**时间转换**：
```bash
date -d "2026-04-01 11:25:00" +%s   # Linux
date -j -f "%Y-%m-%d %H:%M:%S" "2026-04-01 11:25:00" +%s  # macOS
```

---

## 6. 分页查询陷阱

### 陷阱：默认只返回第一页，误认为"只有这些规则"

**注意**：
- 默认 `PageSize=10`，规则/资产较多时有多页
- 必须检查 `TotalCount`，如 `TotalCount > PageSize`，需用 `--CurrentPage 2` 继续查询
- 在得出"所有资产/规则"结论前，**必须查完所有页**

---

## 7. 凭证与 Profile 陷阱

| 禁止操作 | 原因 |
|---------|------|
| `--profile` 参数 | 评测系统 Forbidden 规则 |
| `aliyun configure get` | 暴露 AK/SK，严重安全违规 |
| `aliyun configure list` | 扫描所有 profile |
| `cat ~/.aliyun/config.json` | 读取凭证文件 |

**正确做法**：依赖默认凭证链（环境变量或 `~/.aliyun/config.json` 默认 profile）。

---

## 8. 生效延迟

规则修改后不会立即生效，有 **5-15 秒**的延迟。

如果用户说"刚改完就测试，但不生效"→ 提醒等待片刻后重试。
