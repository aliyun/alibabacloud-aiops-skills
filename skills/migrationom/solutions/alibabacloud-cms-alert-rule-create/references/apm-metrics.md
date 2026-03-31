# APM Metrics Reference

本文档包含 ARMS APM 告警的指标分组和常用指标参考。

## 指标分组概览

| 分组 | 英文标识 | 适用场景 |
|------|----------|----------|
| 应用提供服务统计 | `APP_STAT` | 接口性能、QPS、错误率监控 |
| JVM 监控 | `JVM` | Java 应用堆内存、GC、线程监控 |
| 异常统计 | `EXCEPTION` | 应用异常数、异常类型分布 |
| 数据库调用 | `DB` | SQL 响应时间、慢查询监控 |
| 主机监控 | `HOST` | 应用所在主机资源监控 |
| NoSQL 调用 | `NOSQL` | Redis/MongoDB 调用监控 |
| 外部服务调用 | `EXTERNAL` | 外部 HTTP 调用监控 |
| MQ 消费/生产 | `MQ` | 消息队列性能监控 |

## 应用提供服务统计 (APP_STAT)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| 响应时间 | `rt` | ms | > 500ms Warn, > 1000ms Critical | 接口平均响应时间 |
| 请求数 | `count` | 次/分 | 业务相关 | 接口调用量 |
| 错误数 | `error` | 次/分 | > 10 Warn, > 50 Critical | 接口错误次数 |
| 错误率 | `errorRate` | % | > 1% Warn, > 5% Critical | 错误请求占比 |
| 慢调用数 | `slowCount` | 次/分 | > 10 Warn | 响应时间超阈值的请求数 |
| HTTP 状态码 | `httpCode` | - | 5xx > 0 | 按状态码统计 |

**示例告警规则:**
```json
{
  "alert-type": "APP_STAT",
  "alert-rule-content": {
    "condition": "OR",
    "rules": [{
      "aggregates": "AVG",
      "alias": "rt",
      "nValue": 3,
      "operator": "CURRENT_GTE",
      "value": 800
    }]
  }
}
```

## JVM 监控 (JVM)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| 堆内存使用量 | `heapUsed` | MB | > 80% Warn | JVM 堆内存已使用 |
| 堆内存使用率 | `heapUsedPercent` | % | > 80% Warn, > 90% Critical | 堆内存使用百分比 |
| 非堆内存使用量 | `nonHeapUsed` | MB | > 500MB Warn | 非堆内存使用 |
| GC 次数 | `gcCount` | 次/分 | FullGC > 1 Critical | 垃圾回收次数 |
| GC 耗时 | `gcTime` | ms | > 500ms Warn | 垃圾回收耗时 |
| 线程数 | `threadCount` | 个 | > 500 Warn | 活跃线程数量 |
| 死锁线程数 | `deadlockedThreads` | 个 | > 0 Critical | 死锁线程检测 |

**关键约束：**
- JVM 指标仅适用于 Java 应用
- `heapUsedPercent` 是最常用的 JVM 健康指标
- FullGC 频繁（> 1次/分钟）通常表示内存泄漏

## 异常统计 (EXCEPTION)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| 异常数 | `exceptionCount` | 次/分 | > 10 Warn, > 50 Critical | 应用抛出异常次数 |
| 异常接口数 | `exceptionInterface` | 个 | > 5 Warn | 产生异常的接口数量 |
| 特定异常类型 | `exceptionType` | 次/分 | > 0 (Critical类) | 按异常类型统计 |

**常见需要监控的异常类型:**
- `NullPointerException`
- `OutOfMemoryError`
- `SQLException`
- `TimeoutException`
- `ConnectionRefusedException`

## 数据库调用 (DB)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| SQL 响应时间 | `sqlRt` | ms | > 200ms Warn, > 1000ms Critical | SQL 执行平均耗时 |
| SQL 调用量 | `sqlCount` | 次/分 | 业务相关 | SQL 执行次数 |
| 慢 SQL 数 | `slowSqlCount` | 次/分 | > 10 Warn | 超过阈值的慢查询数 |
| SQL 错误数 | `sqlError` | 次/分 | > 0 Warn | SQL 执行错误次数 |

## 主机监控 (HOST)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| CPU 使用率 | `cpuUsage` | % | > 70% Warn, > 85% Critical | 主机 CPU 使用率 |
| 内存使用率 | `memoryUsage` | % | > 75% Warn, > 90% Critical | 主机内存使用率 |
| 磁盘使用率 | `diskUsage` | % | > 80% Warn, > 90% Critical | 磁盘空间使用率 |
| 网络入流量 | `networkIn` | KB/s | 业务相关 | 网络入方向流量 |
| 网络出流量 | `networkOut` | KB/s | 业务相关 | 网络出方向流量 |

## 外部服务调用 (EXTERNAL)

| 指标 | 英文名 | 单位 | 推荐阈值 | 说明 |
|------|--------|------|----------|------|
| 调用响应时间 | `externalRt` | ms | > 500ms Warn | 外部服务调用耗时 |
| 调用错误数 | `externalError` | 次/分 | > 5 Warn | 外部调用失败次数 |
| 调用量 | `externalCount` | 次/分 | 业务相关 | 外部服务调用次数 |

## 告警规则操作符

| 操作符 | 英文标识 | 说明 |
|--------|----------|------|
| 当前值 >= | `CURRENT_GTE` | 当前值大于等于阈值 |
| 当前值 > | `CURRENT_GT` | 当前值大于阈值 |
| 当前值 <= | `CURRENT_LTE` | 当前值小于等于阈值 |
| 当前值 < | `CURRENT_LT` | 当前值小于阈值 |
| 环比上涨 >= | `HOH_GTE` | 环比上涨百分比 |
| 环比下跌 >= | `HOH_LTE` | 环比下跌百分比 |
| 同比上涨 >= | `YOY_GTE` | 同比上涨百分比 |
| 同比下跌 >= | `YOY_LTE` | 同比下跌百分比 |

## 聚合方式

| 聚合方式 | 英文标识 | 说明 |
|----------|----------|------|
| 平均值 | `AVG` | 统计周期内的平均值 |
| 求和 | `SUM` | 统计周期内的总和 |
| 最大值 | `MAX` | 统计周期内的最大值 |
| 最小值 | `MIN` | 统计周期内的最小值 |

## 指标分组归属约束

**创建 APM 告警时，必须确保指标与分组的正确对应：**

| 指标 | ✅ 正确分组 | ❌ 禁止分组 |
|------|-------------|-------------|
| `rt`, `errorRate` | APP_STAT | JVM, EXCEPTION |
| `heapUsed`, `gcCount` | JVM | APP_STAT, DB |
| `exceptionCount` | EXCEPTION | APP_STAT, JVM |
| `sqlRt`, `slowSqlCount` | DB | APP_STAT, EXCEPTION |
| `cpuUsage`, `memoryUsage` | HOST | JVM, APP_STAT |

## CLI 参数映射

| 配置项 | CLI 参数 | 示例值 |
|--------|----------|--------|
| 应用 PID | `--pids` | `"atc889zkcf@xxx"` |
| 指标分组 | `--alert-type` | `APP_STAT` |
| 告警名称 | `--alert-name` | `"order-service-rt-alert"` |
| 地域 | `--region-id` | `cn-hangzhou` |
| 通知策略 | `--notification-policy-id` | `"np-xxx"` |

## 完整示例

### 接口 RT 告警
```bash
aliyun arms CreateOrUpdateAlertRule \
  --region-id "cn-hangzhou" \
  --alert-name "order-service-rt-critical" \
  --metrics-type "APM" \
  --pids "atc889zkcf@9781f3c4e12xxx" \
  --alert-type "APP_STAT" \
  --alert-rule-content '{"condition":"OR","rules":[{"aggregates":"AVG","alias":"rt","nValue":3,"operator":"CURRENT_GTE","value":800}]}' \
  --notification-policy-id "np-xxxx"
```

### JVM 堆内存告警
```bash
aliyun arms CreateOrUpdateAlertRule \
  --region-id "cn-hangzhou" \
  --alert-name "order-service-heap-critical" \
  --metrics-type "APM" \
  --pids "atc889zkcf@9781f3c4e12xxx" \
  --alert-type "JVM" \
  --alert-rule-content '{"condition":"OR","rules":[{"aggregates":"AVG","alias":"heapUsedPercent","nValue":3,"operator":"CURRENT_GTE","value":85}]}' \
  --notification-policy-id "np-xxxx"
```
