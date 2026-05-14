# Alibaba Cloud Compute Resource Selection Guide

## Product Overview

| Product | Full Name | Positioning | Billing Model | Startup Speed | Task Type |
|------|------|------|----------|----------|----------|
| ECS | Elastic Compute Service | General-purpose VM | Pay-as-you-go / Subscription | 1-3 minutes | One-shot + long-running |
| FC | Function Compute | Serverless function execution | Per invocation + execution duration | Sub-second cold start | **One-shot tasks only** |
| ACK | Container Service for Kubernetes | Container orchestration platform | Cluster management fee + node ECS fee | 5-15 minutes | One-shot + long-running |
| PAI | Platform for AI (DLC) | AI training / inference | Pay-as-you-go (public resource group) / Lingjun cluster | 1-5 minutes | **One-shot tasks only** |

> **Important**: FC and PAI-DLC are one-shot task engines and are not suitable for long-running scenarios such as website deployment or background services.
> Long-running services (e.g. nginx, databases, API services) can only run on ECS or ACK.

## Detailed Comparison

### ECS - Elastic Compute Service

**Pros:**
- The most general-purpose compute resource, suitable for all scenarios
- Rich instance families (general-purpose g, compute c, memory r, GPU, etc.)
- Full control over the operating system; can install any software
- Supports Cloud Assistant RunCommand to execute scripts remotely
- Mature pricing and inventory query APIs

**Cons:**
- Requires manual management of instance lifecycle
- Higher long-term cost than Serverless
- Requires manual configuration of network, security groups, and other infrastructure

**Use cases:**
- General compute tasks (compilation, data processing, web services)
- Tasks that need a full Linux environment
- Long-running background tasks
- Workloads that need a specific software environment (custom images)
- Default choice when the user does not specify a product

### FC - Function Compute

**Pros:**
- Serverless; no server management required
- Sub-second elastic scaling; billed only for actual usage
- Extremely cost-effective for short tasks (per invocation + vCPU-second + memory-second)
- Supports multiple runtimes (Python, Node.js, Go, Java, Custom Runtime)
- Supports GPU instances (fc.gpu.tesla.1, etc.)

**Cons:**
- Per-invocation execution time limits (synchronous up to 10 minutes, asynchronous up to 24 hours)
- Per-instance resource caps (vCPU <= 16, memory <= 32GB)
- Ephemeral filesystem; data is lost after restart
- Not suitable for workloads requiring persistent state
- ROA-style API; invocation pattern differs from ECS / VPC

**Use cases:**
- CPU-intensive short tasks (data transformation, image processing)
- Event-driven compute
- Budget-sensitive intermittent tasks
- Compute that does not require persistent storage
- Tasks with vCPU demand <= 16

**Not suitable for:**
- Website deployment (nginx, Apache, etc.)
- Long-resident background services (databases, message queues, etc.)
- Tasks that require a persistent filesystem

### ACK - Container Service for Kubernetes

**Pros:**
- Native Kubernetes orchestration capabilities
- Suitable for microservices and containerized workloads
- Elastic node pools support auto-scaling
- Rich ecosystem (Helm, Operator, Service Mesh)
- Supports GPU scheduling and heterogeneous compute

**Cons:**
- Cluster creation takes a long time (5-15 minutes)
- Cluster management fee applies (managed edition is free; pro edition is paid)
- Steep learning curve; requires Kubernetes knowledge
- Not suitable for one-shot short tasks
- Script execution requires kubectl exec or submitting a Job

**Use cases:**
- Containerized application deployment and orchestration
- Services that require auto-scaling
- Microservice architectures
- CI/CD pipelines
- Container workloads that need GPUs but are not AI training

### PAI (DLC) - Platform for AI

**Pros:**
- Designed specifically for AI training / inference
- Supports distributed training (TFJob, PyTorchJob, MPIJob, etc.)
- Lingjun clusters provide high-performance GPUs (A100, H100, etc.)
- Built-in data source mounting and code source management
- Automatically handles multi-node multi-GPU communication

**Cons:**
- Suitable only for AI / ML workloads
- Lingjun clusters require reserved resources, so cost is higher
- Public resource group GPUs may queue
- Does not support general-purpose compute tasks

**Use cases:**
- Large model training (LLM, CV, NLP)
- Distributed multi-node multi-GPU training
- GPU-intensive AI tasks
- Model fine-tuning
- Scenarios requiring high-end GPUs such as A100 / H100

**Not suitable for:**
- Website deployment, web services
- Non-AI/ML general-purpose compute tasks
- Long-running service processes

## Selection Decision Tree

```
User intent
│
├─ Did the user explicitly specify a product (e.g. "use ECS", "use FC")?
│  └─ Yes -> Use the specified product directly; skip the selection comparison
│
├─ Is the task a long-running service (website, database, API service, etc.)?
│  ├─ Yes -> Only ECS or ACK (FC / PAI-DLC are not supported)
│  │       ├─ Need Kubernetes / container orchestration? -> ACK
│  │       └─ No -> ECS
│  └─ No (one-shot task)
│
├─ Does it involve AI/ML training or inference?
│  ├─ Yes -> Need multi-node multi-GPU / high-end GPU (A100+)?
│  │       ├─ Yes -> PAI (DLC)
│  │       └─ No -> Is a single GPU enough?
│  │               ├─ Yes, and the task is short -> FC (GPU instance)
│  │               └─ No -> PAI (DLC) or ECS (GPU family)
│  └─ No
│
├─ Is the task containerized / does it require Kubernetes?
│  ├─ Yes -> ACK
│  └─ No
│
├─ No clear rule restricts the choice; multiple options are viable?
│  └─ Yes -> Compare candidate options in parallel (see "Multi-option Comparison" below)
│
└─ Default -> ECS
```

## Multi-option Comparison — MANDATORY PARALLEL SUB-AGENT DISPATCH

When no clear rule narrows the choice to a single product (e.g. "run a simple shell script" could fit either ECS or FC),
you **MUST launch parallel sub-agents** (one per candidate product) to evaluate them. **Do NOT compare options in the main agent thread using documentation knowledge or heuristic judgment — each sub-agent must call real APIs (DescribeInstanceTypes, DescribePrice, etc.) to collect data.** Compare on the dimensions below:

| Dimension | Description |
|----------|------|
| Estimated end-to-end duration | End-to-end time from resource creation to script completion (including startup, configuration, network preparation, etc.) |
| Estimated cost | Estimated total cost under pay-as-you-go billing |
| Complexity | Number of resources to create and the number of configuration steps |
| Resource cleanup | Whether manual release is required and whether residual charges may occur |

**Implementation (mandatory)**: you MUST use sub-agents to evaluate each candidate option in parallel; each sub-agent independently calls the corresponding product's APIs (instance lookup, pricing, inventory, etc.),
then results are aggregated and compared. Performing this comparison in the main agent thread without sub-agents is strictly forbidden. Benefits:
1. **Faster** - multi-product research runs in parallel
2. **Context isolation** - per-product API calls and intermediate results do not pollute the main agent

Sub-agent task template:
```
Evaluate the feasibility of using {product} to run the following task:
Task description: {user intent}
Script content: {script}

Please complete:
1. Look up a suitable instance type (recommendation or list)
2. Confirm inventory availability
3. Estimate cost (via pricing API or formula)
4. Estimate end-to-end duration (creation + execution + cleanup)
5. List the resources that need to be created

Return format:
- Recommended instance type: ...
- Estimated cost: CNY ...
- End-to-end duration: ~... minutes
- Resources to create: ...
- Feasible: yes / no (explain the reason if not feasible)
```

Comparison result presentation template:
```
Option comparison:

| Dimension | ECS | FC |
|------|-----|-----|
| Instance type | ecs.t6-c1m2.large (2c4g) | 0.35vCPU, 512MB |
| Estimated cost | CNY 0.002 | CNY 0.00013 |
| End-to-end duration | ~3 minutes | ~15 seconds |
| Resources to create | VPC + VSwitch + security group + instance | Function |
| Resource cleanup | Must release 4 resources in reverse order | Cleaned up automatically |

Recommendation: FC (lower cost, faster, no infrastructure to manage)

Proceed with the recommended option?
```

## Budget Estimation Reference

| Product | Billing Unit | Approximate Price (cn-hangzhou) |
|------|----------|------------------------|
| ECS (ecs.c7.xlarge, 4c8g) | Pay-as-you-go / hour | ~CNY 0.5 / hour |
| ECS (ecs.g7.2xlarge, 8c32g) | Pay-as-you-go / hour | ~CNY 1.5 / hour |
| ECS (ecs.gn6i-c4g1.xlarge, T4 GPU) | Pay-as-you-go / hour | ~CNY 8 / hour |
| FC (1vCPU, 2GB) | vCPU-second + memory-second | ~CNY 0.0001 / second |
| FC (16vCPU, 32GB) | vCPU-second + memory-second | ~CNY 0.002 / second |
| ACK (managed cluster) | Cluster management fee | Free |
| ACK (pro cluster) | Cluster management fee | ~CNY 0.64 / hour |
| PAI DLC (public resource group, V100) | Pay-as-you-go | ~CNY 20 / hour |
| PAI DLC (Lingjun, A100x8) | Pay-as-you-go | ~CNY 150 / hour |

> Note: prices are reference values; actual prices depend on DescribePrice / the official website. When using this skill, fetch real-time prices via the pricing API.
