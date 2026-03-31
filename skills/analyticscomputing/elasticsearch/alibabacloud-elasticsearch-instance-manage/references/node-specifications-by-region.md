# Elasticsearch Node Specifications and Region Support

This document describes the specification types supported by different node roles in Alibaba Cloud Elasticsearch, as well as regional support information, for reference when creating instances.

> **Important Note**: Different regions support different specifications. Please refer to the purchase page for specific details. The following specification information is for reference only. When actually creating instances, please refer to the available specifications on the Alibaba Cloud console purchase page or those returned by the API.

## Table of Contents

- [Node Role Description](#node-role-description)
- [Data Node Specifications](#data-node-specifications)
- [Dedicated Master Node Specifications](#dedicated-master-node-specifications)
- [Kibana Node Specifications](#kibana-node-specifications)
- [Coordinating Node Specifications](#coordinating-node-specifications)
- [Cold Data Node (Warm Node) Specifications](#cold-data-node-warm-node-specifications)
- [Specification Selection Recommendations for Creating Instances](#specification-selection-recommendations-for-creating-instances)
- [Related Documentation](#related-documentation)

---

## Node Role Description

| Node Role | Description | Required |
|---------|------|--------|
| Data Node | Stores index data, executes CRUD operations, aggregations, etc. | Yes |
| Dedicated Master Node | Manages cluster operations such as creating/deleting indices, allocating shards, etc. | Recommended for production |
| Kibana Node | Provides Kibana visualization interface | Yes (default 1 core 2G included) |
| Coordinating Node | Offloads CPU overhead from data nodes, suitable for CPU-intensive workloads | Optional |
| Cold Data Node (Warm Node) | Stores infrequently accessed historical data, enables hot-cold separation | Optional |

---

## Data Node Specifications


### New Generation Cloud Disk Specifications -- Recommended
Beijing, Shanghai, Hangzhou, Shenzhen, Zhangjiakou do not support cloud disk specifications, use new generation cloud disk specifications instead
| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large.new` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge.new` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge.new` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge.new` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge.new` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large.new` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge.new` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge.new` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge.new` | 16 cores 64 GiB |
| `elasticsearch.turbo1.ga.large` | 2 cores 8 GiB |
| `elasticsearch.turbo1.ga.xlarge` | 4 cores 16 GiB |
| `elasticsearch.turbo1.ga.2xlarge` | 8 cores 32 GiB |
| `elasticsearch.turbo1.ga.4xlarge` | 16 cores 64 GiB |
| `elasticsearch.turbo1.ga.8xlarge` | 32 cores 128 GiB |
| `elasticsearch.turbo1.ca.large` | 2 cores 4 GiB |
| `elasticsearch.turbo1.ca.xlarge` | 4 cores 8 GiB |
| `elasticsearch.turbo1.ca.2xlarge` | 8 cores 16 GiB |
| `elasticsearch.turbo1.ca.4xlarge` | 16 cores 32 GiB |
| `elasticsearch.turbo1.ca.8xlarge` | 32 cores 64 GiB |
| `elasticsearch.turbo1.ca.16xlarge` | 64 cores 128 GiB |


### Cloud Disk Specifications
Beijing, Shanghai, Hangzhou, Shenzhen, Zhangjiakou do not support cloud disk specifications

| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge` | 16 cores 64 GiB |
| `elasticsearch.sn2ne.8xlarge` | 32 cores 128 GiB |


---

## Dedicated Master Node Specifications

Dedicated master nodes are used for cluster management operations, recommended for production environments.

### Specification Features
- Default count is 3, cannot be changed
- Default storage space is 20 GiB, cannot be changed

### New Generation Cloud Disk Specifications

Applicable to Beijing, Shanghai, Hangzhou, Shenzhen regions

| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large.new` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge.new` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge.new` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge.new` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge.new` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large.new` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge.new` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge.new` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge.new` | 16 cores 64 GiB |

### Cloud Disk Specifications

Applicable to Zhangjiakou, Chengdu, Guangzhou, Ulanqab, Qingdao, Hong Kong, and other regions

| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge` | 16 cores 64 GiB |

### Storage Type Support
- ESSD Cloud Disk (default)
- SSD Cloud Disk

---

## Kibana Node Specifications

Kibana nodes are used to provide the visualization interface.

### Specification Features
- Enabled by default, cannot be disabled
- Production environments recommend 2 cores 4 GiB or higher

### Common Specification Reference

| Spec Code | CPU and Memory | Use Case |
|---------|----------|--------|
| `elasticsearch.sn1ne.large` | 2 cores 4 GiB | Production recommended |
| `elasticsearch.sn1ne.xlarge` | 4 cores 8 GiB | Large-scale clusters |
| `elasticsearch.sn2ne.large` | 2 cores 8 GiB | Production recommended |
| `elasticsearch.sn2ne.xlarge` | 4 cores 16 GiB | Large-scale clusters |
| `elasticsearch.sn2ne.2xlarge` | 8 cores 32 GiB | Large-scale clusters |

---

## Coordinating Node Specifications

Coordinating nodes are used to offload CPU overhead from data nodes, suitable for CPU-intensive workloads (such as large aggregation queries).

### Specification Features
- Optional node type
- Storage space defaults to 20 GiB, cannot be changed
- Currently only supports Ultra Cloud Disk
- The number of nodes purchased must be a multiple of the number of availability zones

### Common Specification Reference

| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge` | 16 cores 64 GiB |

---

## Cold Data Node (Warm Node) Specifications

Cold data nodes are used to store infrequently accessed historical data, enabling hot-cold data separation.

### Specification Features
- Optional node type
- Minimum storage space is 500 GiB
- Supports Ultra Cloud Disk
- The number of nodes purchased must be a multiple of the number of availability zones

### Common Specification Reference

| Spec Code | CPU and Memory |
|---------|----------|
| `elasticsearch.sn1ne.large` | 2 cores 4 GiB |
| `elasticsearch.sn1ne.xlarge` | 4 cores 8 GiB |
| `elasticsearch.sn1ne.2xlarge` | 8 cores 16 GiB |
| `elasticsearch.sn1ne.4xlarge` | 16 cores 32 GiB |
| `elasticsearch.sn1ne.8xlarge` | 32 cores 64 GiB |
| `elasticsearch.sn2ne.large` | 2 cores 8 GiB |
| `elasticsearch.sn2ne.xlarge` | 4 cores 16 GiB |
| `elasticsearch.sn2ne.2xlarge` | 8 cores 32 GiB |
| `elasticsearch.sn2ne.4xlarge` | 16 cores 64 GiB |

---


## Specification Selection Recommendations for Creating Instances

### Data Node Selection

| Scenario | Recommended Spec Family | Recommended Specification |
|------|-----------|--------|
| Small Application | Cloud Disk 1:2 | `elasticsearch.sn1ne.xlarge.new` (4 cores 8 GiB) |
| Medium Application | Cloud Disk 1:4 | `elasticsearch.sn2ne.xlarge.new` (4 cores 16 GiB) |
| Large Application | Cloud Disk 1:4/1:8 | `elasticsearch.sn2ne.2xlarge.new` (8 cores 32 GiB) and above |
| Memory-intensive | Cloud Disk 1:8 | `elasticsearch.r5.2xlarge` (8 cores 64 GiB) and above |

### Dedicated Master Node Selection

- Data nodes ≤ 10: 2 cores 4 GiB or 2 cores 8 GiB
- Data nodes > 10: Recommend 4 cores 16 GiB and above

### Kibana Node Selection

- Production environment: Recommend 2 cores 4 GiB and above

---


## Related Documentation

- [Elasticsearch Node Specifications Official Documentation](https://help.aliyun.com/zh/es/product-overview/node-specifications)
- [ES Instance Node Configuration Instructions](https://help.aliyun.com/zh/es/user-guide/purchase-page-parameters)
- [Create Elasticsearch Instance API](https://next.api.aliyun.com/api/elasticsearch/2017-06-13/createinstance)
