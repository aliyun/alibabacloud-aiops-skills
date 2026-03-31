# EIP Batch Associate Cloud Resources - Related APIs and CLI Commands

This document lists all APIs and CLI commands involved in the EIP batch association scenario.

## API and CLI Command List

| Product | CLI Command | API Action | Description |
|---------|-------------|------------|-------------|
| VPC | `aliyun vpc describe-vpcs` | DescribeVpcs | Query VPC list |
| VPC | `aliyun vpc create-default-vpc` | CreateDefaultVpc | Create default VPC |
| VPC | `aliyun vpc describe-vpc-attribute` | DescribeVpcAttribute | Query VPC attributes |
| VPC | `aliyun vpc create-vswitch` | CreateVSwitch | Create VSwitch |
| VPC | `aliyun vpc describe-vswitch-attributes` | DescribeVSwitchAttributes | Query VSwitch attributes |
| VPC | `aliyun vpc delete-vswitch` | DeleteVSwitch | Delete VSwitch |
| VPC | `aliyun vpc delete-vpc` | DeleteVpc | Delete VPC |
| VPC | `aliyun vpc allocate-eip-address` | AllocateEipAddress | Allocate EIP |
| VPC | `aliyun vpc describe-eip-addresses` | DescribeEipAddresses | Query EIP list |
| VPC | `aliyun vpc associate-eip-address` | AssociateEipAddress | Associate EIP (for ECS/NAT) |
| VPC | `aliyun vpc unassociate-eip-address` | UnassociateEipAddress | Disassociate EIP |
| VPC | `aliyun vpc release-eip-address` | ReleaseEipAddress | Release EIP |
| VPC | `aliyun vpc create-nat-gateway` | CreateNatGateway | Create NAT Gateway |
| VPC | `aliyun vpc describe-nat-gateways` | DescribeNatGateways | Query NAT Gateways |
| VPC | `aliyun vpc delete-nat-gateway` | DeleteNatGateway | Delete NAT Gateway |
| ECS | `aliyun ecs create-security-group` | CreateSecurityGroup | Create Security Group |
| ECS | `aliyun ecs delete-security-group` | DeleteSecurityGroup | Delete Security Group |
| ECS | `aliyun ecs run-instances` | RunInstances | Create ECS instance |
| ECS | `aliyun ecs describe-instances` | DescribeInstances | Query ECS instances |
| ECS | `aliyun ecs delete-instance` | DeleteInstance | Delete ECS instance |
| ALB | `aliyun alb create-load-balancer` | CreateLoadBalancer | Create ALB |
| ALB | `aliyun alb get-load-balancer-attribute` | GetLoadBalancerAttribute | Query ALB attributes |
| ALB | `aliyun alb delete-load-balancer` | DeleteLoadBalancer | Delete ALB |
| ALB | `aliyun alb update-load-balancer-address-type-config` | UpdateLoadBalancerAddressTypeConfig | Update ALB address type (bindng/unbind EIP) |

## EIP bindng Resource Type Mapping

| Resource Type | InstanceType Value | InstanceId Example | bindng Method |
|---------------|-------------------|-------------------|----------------|
| ECS Instance | `EcsInstance` | `i-bp123xxx` | `associate-eip-address` |
| NAT Gateway | `Nat` | `ngw-xyz789` | `associate-eip-address` |
| ALB Instance | N/A | `alb-abc123` | `update-load-balancer-address-type-config` |

> **Note**: ALB uses `update-load-balancer-address-type-config` API to bindng/unbind EIP, not `associate-eip-address`.

## API Version Information

| Product | API Version | Endpoint |
|---------|-------------|----------|
| VPC | 2016-04-28 | vpc.aliyuncs.com |
| ECS | 2014-05-26 | ecs.aliyuncs.com |
| ALB | 2020-06-16 | alb.aliyuncs.com |

## Official Documentation Links

| API | Documentation |
|-----|---------------|
| AllocateEipAddress | https://api.aliyun.com/document/Vpc/2016-04-28/AllocateEipAddress |
| AssociateEipAddress | https://api.aliyun.com/document/Vpc/2016-04-28/AssociateEipAddress |
| UnassociateEipAddress | https://api.aliyun.com/document/Vpc/2016-04-28/UnassociateEipAddress |
| ReleaseEipAddress | https://api.aliyun.com/document/Vpc/2016-04-28/ReleaseEipAddress |
| DescribeEipAddresses | https://api.aliyun.com/document/Vpc/2016-04-28/DescribeEipAddresses |
| CreateNatGateway | https://api.aliyun.com/document/Vpc/2016-04-28/CreateNatGateway |
| RunInstances | https://api.aliyun.com/document/Ecs/2014-05-26/RunInstances |
| CreateLoadBalancer (ALB) | https://api.aliyun.com/document/Alb/2020-06-16/CreateLoadBalancer |
| UpdateLoadBalancerAddressTypeConfig | https://api.aliyun.com/document/Alb/2020-06-16/UpdateLoadBalancerAddressTypeConfig |
