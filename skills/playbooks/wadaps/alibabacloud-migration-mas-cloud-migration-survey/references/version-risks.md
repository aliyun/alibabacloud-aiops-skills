# Version Compatibility Risk Reference

> Last updated: 2026-05-28
> Purpose: used by the cloud-migration-survey skill when generating a survey report to identify compatibility risks between source component versions and the target Alibaba Cloud products.
> Rule: when the source version is below the minimum selectable version on Alibaba Cloud, the upgrade requirement and risk must be clearly stated in the report.

---

## 1. Database Version Risks

### RDS MySQL

| Check Item | Value | Notes |
|--------|---|------|
| Alibaba Cloud minimum selectable version | **5.6** | Below this version faces a mandatory upgrade |
| Alibaba Cloud recommended version | **8.0** | Default recommendation for new deployments |
| Alibaba Cloud selectable versions | 5.6 / 5.7 / 8.0 / 8.4 | — |

**Version risk matrix**:

| Source Version | Risk Level | Upgrade Target | Risk Notes |
|---------|---------|---------|---------|
| < 5.6 (e.g. 5.1 / 5.5) | 🔴 High | Upgrade to at least 5.6 | No corresponding version on Alibaba Cloud; upgrade is mandatory. 5.1→5.6 involves syntax changes (e.g. removal of implicit GROUP BY sorting), storage engine changes (MyISAM→InnoDB default), and optimizer behavior differences. **A traffic replay tool must be used to validate.** |
| 5.6 | 🟡 Medium | 5.6 or upgrade to 5.7+ | Alibaba Cloud still supports 5.6, but this version is in its end-of-maintenance phase; upgrading to 5.7 or 8.0 is recommended. |
| 5.7 | 🟢 Low | 5.7 or 8.0 | Compatible, smooth migration. Consider upgrading to 8.0 while at it. |
| 8.0 | 🟢 None | 8.0 | Fully compatible. |

### RDS PostgreSQL

| Check Item | Value |
|--------|---|
| Alibaba Cloud minimum selectable version | **10** |
| Alibaba Cloud recommended version | **15 / 16** |
| Alibaba Cloud selectable versions | 10 / 11 / 12 / 13 / 14 / 15 / 16 |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| < 10 (e.g. 9.4 / 9.5 / 9.6) | 🔴 High | No corresponding version on Alibaba Cloud. 9.x→10+ involves partition table syntax changes, JSONB function differences, and permission model changes. **pg_upgrade check + traffic replay is mandatory.** |
| 10-13 | 🟡 Medium | Supported by Alibaba Cloud, but the version is old; assess an upgrade. |
| 14+ | 🟢 Low | Fully compatible. |

### RDS SQL Server

| Check Item | Value |
|--------|---|
| Alibaba Cloud minimum selectable version | **2012** |
| Alibaba Cloud recommended version | **2019 / 2022** |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| < 2012 (e.g. 2008 / 2008 R2) | 🔴 High | No corresponding version on Alibaba Cloud; upgrade is mandatory. 2008→2012+ involves deprecated T-SQL functions and compatibility level changes. **Assessment with the ADAM tool is recommended.** |
| 2012-2016 | 🟡 Medium | Supported by Alibaba Cloud; assess an upgrade. |
| 2017+ | 🟢 Low | Fully compatible. |

### PolarDB for MySQL

| Check Item | Value |
|--------|---|
| Alibaba Cloud selectable versions | 5.6 / 5.7 / 8.0 |
| Recommended version | **8.0** |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| MySQL < 5.6 | 🔴 High | PolarDB supports 5.6 at minimum; upgrade first. |
| MySQL 5.6-5.7 | 🟢 Low | Can migrate directly to the corresponding PolarDB version. |
| MySQL 8.0 | 🟢 None | Fully compatible. |
| MariaDB 10.x | 🟡 Medium | PolarDB is not directly compatible with MariaDB-specific features (e.g. GTID implementation differences); assessment needed. |

### PolarDB-O (Oracle compatible)

| Source | Risk Level | Notes |
|------|---------|------|
| Oracle 10g | 🔴 High | Extensive syntax incompatibility; requires in-depth ADAM assessment. |
| Oracle 11g | 🟡 Medium | Some PL/SQL syntax needs refactoring; ADAM assessment determines the workload. |
| Oracle 12c+ | 🟡 Medium | Compatibility is good but ADAM assessment is still needed; pay special attention to CDB/PDB architecture differences. |
| DB2 | 🔴 High | PolarDB-O is not directly compatible with DB2; extensive SQL refactoring needed. |

### MongoDB

| Check Item | Value |
|--------|---|
| Alibaba Cloud minimum selectable version | **4.0** |
| Alibaba Cloud recommended version | **5.0 / 6.0** |
| Alibaba Cloud selectable versions | 4.0 / 4.2 / 4.4 / 5.0 / 6.0 / 7.0 |

| Source Version | Risk Level | Upgrade Target | Risk Notes |
|---------|---------|---------|---------|
| < 4.0 (e.g. 3.2 / 3.4 / 3.6) | 🔴 High | Upgrade to at least 4.4 | No corresponding version on Alibaba Cloud. **Note in particular: upgrading a 3.x single-AZ deployment to 4.0+ requires a replica set architecture change.** 3.6→4.0 involves an FCV (Feature Compatibility Version) upgrade chain and cannot skip versions. Recommend a full mongodump export followed by mongorestore on the target. |
| 4.0 single-AZ | 🟡 Medium | 4.4+ replica set | Alibaba Cloud MongoDB 4.0 only supports replica set / sharded cluster architectures, not a single node. If the source is a single-AZ single-node deployment, it must be changed to a replica set after migration, and **the application connection string must be changed.** |
| 4.0 replica set+ | 🟢 Low | 4.0+ | Compatible; can be synced incrementally directly via DTS. |
| 4.4+ | 🟢 None | corresponding version | Fully compatible. |

> **Upgrade path constraint**: MongoDB does not support cross-major-version direct upgrades. 3.4→4.0 must go through the 3.4→3.6→4.0 path. Using mongodump/mongorestore directly is recommended to avoid upgrading on the source.

### Redis

| Check Item | Value |
|--------|---|
| Alibaba Cloud minimum selectable version | **5.0** |
| Alibaba Cloud recommended version | **6.0 / 7.0** |
| Alibaba Cloud selectable versions | 5.0 / 6.0 / 7.0 |

| Source Version | Risk Level | Upgrade Target | Risk Notes |
|---------|---------|---------|---------|
| **4.0 and below** | 🔴 High | At least 5.0 | **Alibaba Cloud no longer has a selectable 4.0 version.** Redis 4.0→5.0 involves introducing the Stream data type, cluster protocol changes, and RDB format incompatibility (a 4.0 RDB cannot be loaded directly by 5.0). **The Redis-Shake online sync method must be used for migration; direct RDB file restore is not allowed.** |
| 3.x (e.g. 3.0 / 3.2) | 🔴 High | 5.0+ | Crosses multiple major versions; large differences in Lua script compatibility and cluster commands. |
| 5.0 | 🟢 Low | 5.0+ | Compatible. |
| 6.0+ | 🟢 None | corresponding version | Fully compatible. |

> **Tair version note**: all Tair editions (memory/persistent memory/disk) are based on the Redis 6.0 protocol. If the source uses new Redis 7.0 features (e.g. Redis Functions), confirm whether Tair supports them.

### Lindorm (HBase migration)

| Source | Risk Level | Notes |
|------|---------|------|
| HBase 1.x | 🟡 Medium | Lindorm is compatible with the HBase 2.x API; some 1.x deprecated APIs need refactoring. Migration with the LTS tool is recommended. |
| HBase 2.x | 🟢 Low | Lindorm is compatible with the main HBase 2.x APIs. |
| HBase + Kerberos | 🔴 High | Lindorm does not support Kerberos authentication; remove the Kerberos dependency before migration. |
| HBase + Coprocessor | 🔴 High | Lindorm does not support custom Coprocessors; refactor into application-layer logic. |

---

## 2. Middleware Version Risks

### Kafka

| Check Item | Value |
|--------|---|
| Alibaba Cloud Kafka compatible versions | Apache Kafka 2.x / 3.x |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| Kafka 0.10 and below | 🔴 High | Incompatible with Alibaba Cloud Kafka; large Consumer Group protocol differences. Client upgrade needed. |
| Kafka 0.11 - 1.x | 🟡 Medium | Basically compatible, but some old-version APIs are deprecated; client SDK upgrade needed. |
| Kafka 2.x - 3.x | 🟢 Low | Fully compatible. |

### RocketMQ

| Check Item | Value |
|--------|---|
| Alibaba Cloud RocketMQ 5.x | Compatible with open-source RocketMQ 4.x / 5.x |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| RocketMQ 3.x | 🔴 High | Protocol incompatible; upgrade to a 4.x+ client. |
| RocketMQ 4.x | 🟢 Low | Alibaba Cloud RocketMQ 5.x is backward compatible with the 4.x protocol. |
| ActiveMQ | 🔴 High | Completely different protocol (JMS/OpenWire); refactor to the RocketMQ SDK or choose RabbitMQ (AMQP). |
| RabbitMQ (as an alternative) | 🟡 Medium | If you do not want to refactor code, you can choose the Alibaba Cloud RabbitMQ edition for a smooth migration. |

### RabbitMQ

| Check Item | Value |
|--------|---|
| Alibaba Cloud RabbitMQ compatible version | AMQP 0-9-1 protocol |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| RabbitMQ 3.x | 🟢 Low | Fully compatible; AMQP protocol is standardized. |
| RabbitMQ 4.x | 🟢 Low | Compatible. |
| self-hosted RabbitMQ + custom plugins | 🟡 Medium | The Alibaba Cloud managed edition does not support third-party plugins; assess the plugin dependencies. |

### MQTT

| Source | Risk Level | Notes |
|------|---------|------|
| EMQX (self-hosted) | 🟢 Low | Standard MQTT 3.1.1/5.0 protocol compatible. |
| Mosquitto (self-hosted) | 🟢 Low | Protocol compatible. |
| AWS IoT Core | 🟡 Medium | Thing model / shadow device needs to be redefined. |
| Azure IoT Hub | 🟡 Medium | Device twin / DPS mechanism differs; adaptation needed. |

---

## 3. Microservices Version Risks

### Nacos

| Source | Risk Level | Notes |
|------|---------|------|
| Nacos 1.x (self-hosted) | 🟡 Medium | MSE Nacos is compatible with the 1.x protocol, but upgrading the client to 2.x (gRPC long-connection mode) is recommended. |
| Nacos 2.x (self-hosted) | 🟢 Low | MSE Nacos is fully compatible. |
| Eureka | 🟡 Medium | Must switch to the Nacos SDK; change the spring.cloud.nacos config for Spring Cloud projects. |
| Consul | 🟡 Medium | Service registration interface differs; adaptation needed. |

### ZooKeeper

| Source Version | Risk Level | Notes |
|---------|---------|------|
| ZK 3.4.x | 🟡 Medium | MSE ZK is compatible with the 3.4 protocol, but some old-version APIs are deprecated. |
| ZK 3.5+ | 🟢 Low | Fully compatible. |

### XXL-Job

| Source Version | Risk Level | Notes |
|---------|---------|------|
| XXL-Job 2.x | 🟡 Medium | Migrating to SchedulerX requires: 1) deploying the SchedulerX Agent, 2) adapting the Job Handler code, 3) re-entering the scheduling config. A progressive migration (dual-scheduler parallel validation) is recommended. |

---

## 4. Container and K8s Version Risks

### Kubernetes

| Check Item | Value |
|--------|---|
| K8s versions supported by ACK | 1.24 / 1.26 / 1.28 / 1.30 (subject to official docs) |

| Source Version | Risk Level | Notes |
|---------|---------|------|
| K8s < 1.22 | 🔴 High | Not supported by ACK. APIs before 1.22 (e.g. extensions/v1beta1 Ingress, PodSecurityPolicy) are deprecated; YAML requires extensive modification. |
| K8s 1.22 - 1.24 | 🟡 Medium | Confirm whether some APIs have been migrated to the new versions (e.g. Ingress → networking.k8s.io/v1). |
| K8s 1.24+ | 🟢 Low | Fully compatible with ACK. |

> **API deprecation check**: when upgrading a K8s version, you must check whether the APIs in use are deprecated. Common deprecated APIs include:
> - `extensions/v1beta1` Ingress → `networking.k8s.io/v1`
> - `policy/v1beta1` PodDisruptionBudget → `policy/v1`
> - `autoscaling/v2beta2` HPA → `autoscaling/v2`
> - PodSecurityPolicy (removed) → Pod Security Standards

---

## 5. General Version Risk Detection Rules

When generating the report, perform the following checks for each component that involves a version change:

1. **Extract the source version**: identify the component name and version number from the survey materials.
2. **Query the Alibaba Cloud minimum version**: confirm against the tables above whether Alibaba Cloud supports that version.
3. **Mark the risk level**:
   - 🔴 High risk: the source version is below the minimum selectable version on Alibaba Cloud; **upgrade is mandatory**.
   - 🟡 Medium risk: supported by Alibaba Cloud but the version is old; **upgrade is recommended**.
   - 🟢 Low / no risk: version compatible.
4. **Record the upgrade path**: for components that need an upgrade, describe the upgrade path and considerations.
5. **Recommend validation tools**: recommend traffic replay (go-replay/tcpcopy) or a compatibility assessment tool (ADAM) for validation.

### Annotation format in the report

In the "Migration Notes" column of the "Resource Detail" table, every entry that involves a version change should be annotated as:

```
[Version upgrade] source version X.Y → target version A.B
Risk level: High/Medium/Low
Impact: (specific differences)
Validation plan: (recommended tools and methods)
```
