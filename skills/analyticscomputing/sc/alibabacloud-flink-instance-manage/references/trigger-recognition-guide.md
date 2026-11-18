# Trigger Recognition Guide

This guide helps identify when to use the alibabacloud-flink-instance-manage skill.

## Quick Rule

Use this skill to create or query Flink VVP instances and namespaces, or to manage regional Flink AI Service.

## Positive Triggers (Use Skill)

### Instance Operations
| User Request | Skill Action |
|-------------|--------------|
| "Create a Flink instance" | create command |
| "Query my Flink instances" | describe command |
| "创建Flink实例" | create command |
| "查询Flink实例信息" | describe command |
| "List Flink VVP instances" | describe command |
| "What regions support Flink" | describe_regions command |
| "Flink可用区有哪些" | describe_zones command |
| "查询 Flink 实例标签" | list_tags command |

### Namespace Operations
| User Request | Skill Action |
|-------------|--------------|
| "Create a Flink namespace" | create_namespace command |
| "List namespaces for Flink instance X" | describe_namespaces command |
| "创建Flink命名空间" | create_namespace command |
| "查询实例下的命名空间" | describe_namespaces command |

### Flink AI Service

| User request | Command |
|---|---|
| "杭州的 Flink AI 服务开通了吗" | `get_flink_ai_service` |
| "查一下 Flink AI 服务免费额度和用量" | `get_flink_ai_service_free_quota` |
| "在北京开通 Flink AI 服务" | `open_flink_ai_service` |
| "关闭深圳的 Flink AI 服务" | `close_flink_ai_service` |
| "开启北京 Flink AI 服务的关闭保护" | `modify_ai_service_protection` with `true` |

## Negative Triggers (Do Not Use Skill)

### Different Service Domain
| User Request | Reason | Correct Action |
|-------------|--------|----------------|
| "Create an ECS instance" | Wrong service | Use ECS skill or reject |
| "Create Kafka topic" | Wrong service | Use Kafka skill or reject |
| "Upload to OSS" | Wrong service | Use OSS skill or reject |
| "Create a DataWorks workflow" | Wrong service | Use DataWorks workflow skill or reject |
| "创建ECS实例" | Wrong service | Not Flink related |
| "今天天气怎么样" | Generic question | Do not trigger this skill |

### Different Flink Domain
| User Request | Reason | Correct Action |
|-------------|--------|----------------|
| "Run Flink SQL query" | Flink SQL, not instance | Use Flink SQL skill |
| "Submit Flink job" | Job management | Different skill |
| "运行Flink SQL" | Flink SQL, not instance | Use Flink SQL skill |
| "用云端 AI 助手诊断作业", "配置智能巡检" | Intelligent Assistant and intelligent inspection | Use the Flink AI operations skill |

### In-Domain but Rejected (Trigger + Reject)
| User Request | Reason | Correct Action |
|-------------|--------|----------------|
| "Update Flink instance config" | Update not supported by command scope | Trigger skill, then reject with scope explanation |
| "Delete Flink instance" | Delete not supported by command scope | Trigger skill, then reject with scope explanation |
| "修改Flink实例配置" | Update not supported by command scope | Trigger skill, then reject with scope explanation |
| "删除Flink实例" | Delete not supported by command scope | Trigger skill, then reject with scope explanation |

## Ambiguous Cases

When request intent is unclear, ask one clarifying question:

- "Do you need Flink instance/namespace management, or Flink SQL/job operations?"
- "开启 Flink AI" can mean activating regional AI Service or using an AI feature. Clarify which the user wants.

## Decision Tree

```
User request about Flink
    │
    ├─ Regional AI service status, quota, activation, deactivation, or closure protection → Use this skill
    ├─ Intelligent Assistant or intelligent inspection → Use the Flink AI operations skill
    │
    ├─ Mentions "instance" or "namespace" or "VVP"?
    │   ├─ YES → USE THIS SKILL
    │   │   ├─ create/query → Execute
    │   │   └─ update/delete → Reject with explanation
    │   │
    │   └─ NO → Check further
    │       ├─ Mentions "SQL" or "job" → Different Flink skill
    │       └─ Unclear → Ask user to clarify
    │
    └─ Request about other service (ECS, Kafka, OSS)?
        └─ YES → Do NOT use this skill
```
