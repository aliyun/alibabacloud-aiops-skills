# Supported Environments

## Control Host OS

The host running `sysom-osops` (the control host) can be:

| OS | Architecture | Notes |
|----|--------------|-------|
| Linux | x86_64, aarch64 | Recommended control host |
| macOS | x86_64, aarch64 | Fully supported; installer handles ad-hoc codesign and Rosetta detection |

Windows is **not** supported as a control host — the installer does not run on
Windows. The target ECS being diagnosed must be Linux (see below), but the
control host does not need to be. A macOS laptop is a common control host for
remote diagnosis of Linux ECS instances.

## Target Instance OS

| Architecture | Supported distributions |
|--------------|-------------------------|
| x86_64 | Alibaba Cloud Linux 2/3, Alibaba Cloud Linux 3 Pro, Alibaba Cloud Linux 3 Container Optimized Edition, CentOS 7.6+, CentOS 8, Rocky Linux 8.8/9.1/9.5, Ubuntu 20.04/22.04/24.04, Anolis OS 7/8 |
| aarch64 | Alibaba Cloud Linux 3, Alibaba Cloud Linux 3 Pro |

## Region Availability

Remote diagnosis is available in China Mainland regions and China (Hong Kong).

## Prerequisites

- The target ECS instance is Linux.
- Cloud Assistant is online on the target ECS instance.
- Remote commands have valid Alibaba Cloud credentials through AK/SK or ECS RAM Role.
- Credentials also gate command *discovery*: without them the skills catalog is
  unreachable and remote deep commands are not registered in the CLI at all.
  Only local `memory classify` works uncredentialed.
- Java memory diagnosis requires OpenJDK 1.8 or later on the target instance.

## Unsupported Scenarios

- Windows instances.
- Instances without Cloud Assistant online.
- Regions outside China Mainland and Hong Kong.
- Pure configuration questions without a SysOM diagnosis symptom, such as generic
  security group or VPC routing administration.
