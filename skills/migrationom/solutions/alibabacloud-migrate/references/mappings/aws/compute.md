# AWS Compute Services → Alibaba Cloud Mapping

## EC2 Instances

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_instance` | `alicloud_instance` | Low | Image ID format, security group attachment |
| `aws_launch_template` | `alicloud_ecs_launch_template` | Low | Similar structure |
| `aws_placement_group` | `alicloud_ecs_deployment_set` | Medium | Different grouping concept |
| `aws_key_pair` | `alicloud_ecs_key_pair` | Low | Same functionality |
| `aws_spot_instance_request` | `alicloud_instance` (spot_strategy) | Medium | Spot via `spot_strategy` attribute, not separate resource |
| `aws_spot_fleet_request` | `alicloud_ess_scaling_group` (spot) | Medium | Use scaling group with spot config |
| `aws_ec2_fleet` | `alicloud_ess_scaling_group` | Medium | Fleet → scaling group |
| `aws_ec2_capacity_reservation` | `alicloud_ecs_capacity_reservation` | Low | Similar concept |

### Key Attribute Differences

| Attribute | AWS EC2 (`aws_instance`) | Alibaba Cloud ECS (`alicloud_instance`) |
|-----------|---------|-------------------|
| Image | `ami` (`ami-xxxxxxxx` format) | `image_id` (name-based ID) |
| Security Groups | `vpc_security_group_ids` | `security_groups` |
| Subnet | `subnet_id` | `vswitch_id` |
| Key Pair | `key_name` | `key_name` (same) |
| User Data | `user_data` (base64) | `user_data` (base64, same) |
| Block Device | `ebs_block_device` | `data_disks` |
| Tags | `tags` | `tags` (same) |

### Instance Type Mapping

#### General Purpose

| AWS Instance Type | vCPU | Memory (GiB) | Alibaba Cloud Equivalent | Notes |
|-------------------|------|--------------|-------------------------|-------|
| `t3.micro` | 2 | 1 | `ecs.t5-small` | Burstable |
| `t3.small` | 2 | 2 | `ecs.t5-large` | Burstable |
| `t3.medium` | 2 | 4 | `ecs.t5-xlarge` or `ecs.c6.large` | Burstable or Compute |
| `t3.large` | 2 | 8 | `ecs.c6.large` | Compute optimized |
| `t3.xlarge` | 4 | 16 | `ecs.c6.xlarge` | Compute optimized |
| `m5.large` | 2 | 8 | `ecs.g6.large` | General purpose |
| `m5.xlarge` | 4 | 16 | `ecs.g6.xlarge` | General purpose |
| `m5.2xlarge` | 8 | 32 | `ecs.g6.2xlarge` | General purpose |
| `m5.4xlarge` | 16 | 64 | `ecs.g6.4xlarge` | General purpose |

#### Compute Optimized

| AWS Instance Type | vCPU | Memory (GiB) | Alibaba Cloud Equivalent | Notes |
|-------------------|------|--------------|-------------------------|-------|
| `c5.large` | 2 | 4 | `ecs.c6.large` | Compute optimized |
| `c5.xlarge` | 4 | 8 | `ecs.c6.xlarge` | Compute optimized |
| `c5.2xlarge` | 8 | 16 | `ecs.c6.2xlarge` | Compute optimized |
| `c5.4xlarge` | 16 | 32 | `ecs.c6.4xlarge` | Compute optimized |

#### Memory Optimized

| AWS Instance Type | vCPU | Memory (GiB) | Alibaba Cloud Equivalent | Notes |
|-------------------|------|--------------|-------------------------|-------|
| `r5.large` | 2 | 16 | `ecs.r6.large` | Memory optimized |
| `r5.xlarge` | 4 | 32 | `ecs.r6.xlarge` | Memory optimized |
| `r5.2xlarge` | 8 | 64 | `ecs.r6.2xlarge` | Memory optimized |
| `r5.4xlarge` | 16 | 128 | `ecs.r6.4xlarge` | Memory optimized |

---

## Block Storage (EBS / Disk)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_ebs_volume` | `alicloud_ecs_disk` | Low | `type` → `category` (cloud_essd, cloud_ssd, etc.) |
| `aws_volume_attachment` | `alicloud_ecs_disk_attachment` | Low | Similar attachment model |
| `aws_ebs_snapshot` | `alicloud_ecs_snapshot` | Low | Similar snapshot model |
| `aws_ebs_snapshot_copy` | `alicloud_snapshot` (cross-region) | Medium | Cross-region copy via API |
| `aws_ebs_encryption_by_default` | No equivalent | N/A | Alibaba encrypts per-disk via `encrypted` attribute |

---

## AMI / Image

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_ami` | `alicloud_image` | Medium | ID format differs; use `alicloud_image_import` for migration |
| `aws_ami_copy` | `alicloud_image_copy` | Low | Cross-region image copy |
| `aws_ami_from_instance` | `alicloud_image` (from instance) | Low | Create image from running instance |
| `aws_ami_launch_permission` | `alicloud_image_share_permission` | Low | Share image with other accounts |

---

## Auto Scaling

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Key Differences |
|--------------|----------------------|---------------------|----------------|
| `aws_autoscaling_group` | `alicloud_ess_scaling_group` | Medium | Different attachment model |
| `aws_autoscaling_policy` | `alicloud_ess_scaling_rule` | Low | Similar concepts |
| `aws_autoscaling_schedule` | `alicloud_ess_scheduled_task` | Low | Same functionality |
| `aws_autoscaling_lifecycle_hook` | `alicloud_ess_lifecycle_hook` | Low | Lifecycle hook |
| `aws_autoscaling_notification` | `alicloud_ess_notification` | Low | Scaling notification |
| `aws_autoscaling_attachment` | `alicloud_ess_attachment` | Low | Instance attachment |
| - | `alicloud_ess_scaling_configuration` | Medium | Launch config for scaling group (Alibaba-specific) |

---

## Container Services (ECS/EKS → ACK)

> **Note**: AWS ECS (Elastic Container Service) is a proprietary container orchestrator. Alibaba Cloud ACK is Kubernetes-based. Migrating from ECS requires re-architecting to Kubernetes manifests.

### Kubernetes (EKS → ACK)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_eks_cluster` | `alicloud_cs_managed_kubernetes` | Low | Managed Kubernetes |
| `aws_eks_node_group` | `alicloud_cs_kubernetes_node_pool` | Low | Worker node pool |
| `aws_eks_addon` | `alicloud_cs_kubernetes_addon` | Medium | Add-on management |
| `aws_eks_fargate_profile` | `alicloud_cs_serverless_kubernetes` | Medium | Serverless Kubernetes (separate cluster type) |

### Container Orchestration (ECS → ACK)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_ecs_cluster` | `alicloud_cs_managed_kubernetes` | High | ECS → Kubernetes migration |
| `aws_ecs_service` | Kubernetes Deployment/Service | High | Re-architect to K8s manifests |
| `aws_ecs_task_definition` | Kubernetes Pod spec | High | Re-architect to K8s manifests |
| `aws_ecs_capacity_provider` | `alicloud_cs_kubernetes_node_pool` | Medium | Capacity → node pool |

> **ACK Prerequisites**: `alicloud_cs_managed_kubernetes` requires:
> - `vswitch_ids` — at least 2 VSwitches in different AZs (for HA)
> - VPC + VSwitches must be created first; if source has no explicit network resources (e.g., network is inside a remote module), generate `alicloud_vpc` + `alicloud_vswitch` resources as dependencies
> - `pod_vswitch_ids` — required for Terway network plugin (optional for Flannel)

### Required Target Properties and Forbidden Mappings

When Phase 2 maps ECS/EKS-style container clusters to ACK, write cluster prerequisites directly into `target_resources[].properties`:

| Source Pattern | Target Resource | Required `target_resources[].properties` | Forbidden |
|----------------|----------------|-------------------------------------------|-----------|
| `aws_ecs_cluster` | `alicloud_cs_managed_kubernetes` | `vswitch_ids` with at least 2 VSwitch references in different zones; `cluster_spec`/version fields when selected; dependencies on generated VPC/VSwitches if source network is inside a remote module | `alicloud_cs_kubernetes`, single-zone `vswitch_ids` |
| `aws_eks_cluster` | `alicloud_cs_managed_kubernetes` | `vswitch_ids` with at least 2 VSwitch references in different zones; Kubernetes version when source specifies one | `alicloud_cs_kubernetes`, single-zone `vswitch_ids` |

Use `vswitch_ids` for managed ACK clusters. Do not emit legacy or unsupported cluster resources.

### Container Registry (ECR → CR)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_ecr_repository` | `alicloud_cr_ee_repo` | Low | Enterprise Edition recommended |
| `aws_ecr_lifecycle_policy` | No direct equivalent | Medium | Manual cleanup or custom rules |
| `aws_ecr_registry_scanning_configuration` | `alicloud_cr_scan_rule` | Low | Image scanning |
| - | `alicloud_cr_ee_instance` | N/A | CR EE requires instance creation (Alibaba-specific) |
| - | `alicloud_cr_ee_namespace` | N/A | Namespace under CR EE instance (Alibaba-specific) |

---

## Serverless Compute (Lambda → FC)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| `aws_lambda_function` | `alicloud_fcv3_function` | Medium | Runtime/handler differences |
| `aws_lambda_layer_version` | `alicloud_fcv3_layer_version` | Low | Layer packaging |
| `aws_lambda_alias` | `alicloud_fcv3_alias` | Low | Function alias |
| `aws_lambda_event_source_mapping` | `alicloud_fcv3_trigger` | Medium | Trigger model differs |
| `aws_lambda_permission` | No direct equivalent | Medium | Authorization via RAM |
| `aws_lambda_function_url` | `alicloud_fcv3_custom_domain` | Medium | HTTP endpoint for function |
| `aws_lambda_provisioned_concurrency_config` | `alicloud_fcv3_provision_config` | Low | Provisioned concurrency |

---

## Serverless Application (SAE)

| AWS Resource | Alibaba Cloud Resource | Migration Difficulty | Notes |
|--------------|----------------------|---------------------|-------|
| AWS App Runner | `alicloud_sae_application` | Medium | Serverless app hosting |
| - | `alicloud_sae_namespace` | N/A | SAE namespace (Alibaba-specific) |
| - | `alicloud_sae_ingress` | N/A | SAE ingress routing (Alibaba-specific) |

---

## Instance Selection Guide

### By Workload Type

| Workload | AWS Family | Alibaba Cloud Family |
|----------|------------|---------------------|
| Web servers | `t3`, `m5` | `ecs.t5`, `ecs.g6` |
| Compute intensive | `c5` | `ecs.c6` |
| Memory intensive | `r5` | `ecs.r6` |
| High frequency trading | `c5n` | `ecs.c6ne` |
| SAP HANA | `x1e` | `ecs.se1ne` |

### Cost Optimization Tips

1. **Use burstable instances** (`t5`) for development/test environments
2. **Reserved instances** for production workloads (up to 50% savings)
3. **Spot instances** for fault-tolerant workloads
4. **Right-size regularly** using CloudMonitor metrics

---

## Migration Checklist

### Pre-Migration
- [ ] Document current instance types and specifications
- [ ] Identify equivalent Alibaba Cloud instance types
- [ ] Check image/AMI availability in target region
- [ ] Plan for downtime or use migration tools

### During Migration
- [ ] Create ECS instances with mapped types
- [ ] Configure security groups and networking
- [ ] Attach data disks if needed
- [ ] Configure auto-scaling policies

### Post-Migration
- [ ] Verify instance performance
- [ ] Monitor resource utilization
- [ ] Adjust instance types if needed
- [ ] Update monitoring and alerting
