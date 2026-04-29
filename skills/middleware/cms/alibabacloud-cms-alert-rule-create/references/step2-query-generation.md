# Step 2: 查询生成

## 目的
发现并选择告警规则所需的正确指标。

---

## 动态指标发现（主要方法）

### 关键规则
> **必须调用 `describe-metric-meta-list` API 来发现指标。不要仅依赖硬编码的指标列表。**

### 第 1 步：查询可用指标

在 Step 1 确定 namespace 后，查询所有可用指标：

```bash
aliyun cms describe-metric-meta-list \
  --namespace "<namespace>" \
  --page-size 100
```

**示例输出：**
```json
{
  "Resources": {
    "Resource": [
      {
        "MetricName": "CPUUtilization",
        "Description": "CPU utilization rate",
        "Unit": "%",
        "Statistics": "Average,Minimum,Maximum",
        "Periods": "60,300,900",
        "Dimensions": "userId,instanceId"
      }
    ]
  }
}
```

### 第 2 步：将用户意图匹配到指标

根据用户的描述，匹配到相应的指标：

| 用户意图 | 常用 MetricName 关键词 |
|----------|----------------------|
| CPU 使用率 | `CPU`, `cpu` |
| 内存使用率 | `Memory`, `memory`, `Mem` |
| 磁盘空间/使用率 | `Disk`, `disk`, `Storage`, `storage` |
| 网络流量 | `Net`, `net`, `Traffic`, `Bandwidth`, `Rate` |
| 连接数 | `Connection`, `connection`, `Conn`, `conn` |
| IOPS | `IOPS`, `iops`, `IO` |
| 延迟 | `Latency`, `latency`, `Delay`, `delay` |
| 错误/故障 | `Error`, `error`, `Fail`, `fail`, `Drop` |
| 负载/队列 | `Load`, `Queue`, `queue` |

### 第 3 步：与用户确认

展示匹配到的指标并请用户确认：

```
根据您的需求，我找到了以下匹配的指标：

1. CPUUtilization
   - 描述：CPU 使用率
   - 单位：%
   - 统计方式：Average、Minimum、Maximum

您要使用此指标，还是选择其他指标？
```

### 第 4 步：提取关键参数

从选定指标的元数据中提取：
- **MetricName**：用于 `--metric-name` 参数
- **Statistics**：默认推荐 `Average`，除非用户另有指定；OSS/特殊指标使用 `Value`
- **Periods**：用于验证 `--interval` 参数
- **Dimensions**：了解所需的资源标识符

---

## CLI 帮助发现

如果不确定命令语法或参数：

```bash
# 列出所有 CMS 命令
aliyun cms --help

# 显示特定命令的详细用法
aliyun cms describe-metric-meta-list --help
```

这将显示可用参数、必填字段和使用示例。

---

## 静态参考（备选方案）

如果 `describe-metric-meta-list` API 调用失败（超时、认证错误等），回退到 `metrics.md` 中的常用指标参考。

详见 `metrics.md` 中的常用指标快速参考表。

---

## 下一步
→ `step3-detection-config.md`
