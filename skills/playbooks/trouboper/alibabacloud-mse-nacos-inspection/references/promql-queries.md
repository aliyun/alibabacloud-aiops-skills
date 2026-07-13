# PromQL Query Reference

This document contains all PromQL queries required for MSE Nacos inspection. When executing queries, replace `$clusterName` in all PromQL queries with the `ClusterName` value of the corresponding instance.

## Table of Contents

- [4.1 Configuration Count Usage](#41-configuration-count-usage)
- [4.2 Connection Count Usage](#42-connection-count-usage)
- [4.3 QPS Usage](#43-qps-usage)
- [4.4 TPS Usage](#44-tps-usage)

---

## 4.1 Configuration Count Usage

### Professional Edition (mse_pro)

```promql
(max(nacos_monitor{module="config",name="configCount",service_cluster_id="$clusterName"}))
/
(
  (max(nacos_control_limit_value{module="config",name="clusterConfig",type="COUNT",service_cluster_id="$clusterName"})) > -1
  or
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) == bool 1)*1000 +
    (max(system_cpu_count{service_cluster_id="$clusterName"}) == bool 2)*1000 +
    (max(system_cpu_count{service_cluster_id="$clusterName"}) == bool 4)*5000 +
    (max(system_cpu_count{service_cluster_id="$clusterName"}) == bool 8)*5000 +
    (max(system_cpu_count{service_cluster_id="$clusterName"}) == bool 16)*5000
  )
)
```

### Enterprise Edition (mse_platinum)

```promql
(max(nacos_monitor{module="config",name="configCount",service_cluster_id="$clusterName"}))
/
(
  (max(nacos_control_limit_value{module="config",name="clusterConfig",type="COUNT",service_cluster_id="$clusterName"})) > -1
  or
  vector(1000)
)
```

### Serverless Edition (mse_serverless)

```promql
max(nacos_monitor{module="config",name="configCount",service_cluster_id="$clusterName"}) by (service_cluster_id) / max(nacos_config_quota{name="clusterTotalConfigQuota",service_cluster_id="$clusterName"}) by (service_cluster_id)
```

---

## 4.2 Connection Count Usage (Professional and Enterprise only)

### Professional Edition (mse_pro)

```promql
( (max(instance_connection{name="clusterTotalCount",service_cluster_id="$clusterName"}) by (service_cluster_id) > -1)
or  ((sum(nacos_monitor{module="config",name="longPolling",service_cluster_id="$clusterName"}) by (service_cluster_id) + sum(nacos_connection_count{service_cluster_id="$clusterName"}) by (service_cluster_id)) > -1) or sum(nacos_monitor{module="config",name="longPolling",service_cluster_id="$clusterName"}) by (service_cluster_id)) / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 1) * 160
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 320
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 640
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 1280
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 2560
  )
)
```

### Enterprise Edition (mse_platinum)

```promql
( (max(instance_connection{name="clusterTotalCount",service_cluster_id="$clusterName"}) by (service_cluster_id) > -1)
or  ((sum(nacos_monitor{module="config",name="longPolling",service_cluster_id="$clusterName"}) by (service_cluster_id) + sum(nacos_connection_count{service_cluster_id="$clusterName"}) by (service_cluster_id)) > -1) or sum(nacos_monitor{module="config",name="longPolling",service_cluster_id="$clusterName"}) by (service_cluster_id))  / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 400
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 800
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 1600
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 3200
  )
)
```

---

## 4.3 QPS Usage (Professional and Enterprise only)

### Professional Edition (mse_pro)

```promql
(sum(rate(nacos_monitor_read_seconds_count{module="naming",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) + sum(rate(nacos_monitor{module="config",name="getConfig",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) ) / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 1) * 160
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 320
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 640
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 1280
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 2560
  )
)
```

### Enterprise Edition (mse_platinum)

```promql
(sum(rate(nacos_monitor_read_seconds_count{module="naming",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) + sum(rate(nacos_monitor{module="config",name="getConfig",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) ) / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 400
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 800
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 1600
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 3200
  )
)
```

---

## 4.4 TPS Usage (Professional and Enterprise only)

### Professional Edition (mse_pro)

```promql
(sum(rate(nacos_monitor_writer_seconds_count{module="naming",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) + sum(rate(nacos_monitor{module="config",name="publish",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) ) / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  ( (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 1) * 80
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 160
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 320
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 640
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 1280
  )
)
```

### Enterprise Edition (mse_platinum)

```promql
(sum(rate(nacos_monitor_writer_seconds_count{module="naming",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) + sum(rate(nacos_monitor{module="config",name="publish",service_cluster_id="$clusterName"}[1m])) by (service_cluster_id) ) / 
(
  (
    count(
      label_replace(
        container_spec_cpu_quota{pod_name=~"$clusterName.*",container="main"},
        "service_cluster_id",
        "$1",
        "pod_name",
        "(.+)-reg-center-0-\\d+"
      )
    ) by (service_cluster_id)
  )
  * 
  (
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 2) * 200
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 4) * 400
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 8) * 800
    + 
    (max(system_cpu_count{service_cluster_id="$clusterName"}) by (service_cluster_id) == bool 16) * 1600
  )
)
```
