# LookupAttribute Parameter Guide

## Overview

When calling the LookupEvents API to search historical events, the `LookupAttribute` parameter sets the search conditions. Currently only **1 to 2** AttributeItem entries are supported as search conditions.

Each AttributeItem consists of a search key (Key) and a search value (Value).

## Supported AttributeKeys

| Key | Description | Example Value |
|-----|-------------|---------------|
| **ServiceName** | Cloud service name (case-sensitive) | Ecs, Vpc, Slb, ALB |
| **EventName** | Event name | ConsoleSignin, AllocateEipAddress |
| **User** | Caller name | Alice, admin |
| **EventId** | Event ID | B702AFA3-FD4B-40E3-88E4-C0752FAA**** |
| **ResourceType** | Resource type | ACS::ECS::Instance |
| **ResourceName** | Resource name | i-bp14664y88udkt45****, eip-xxx |
| **EventRW** | Read/write type | Read / Write |
| **EventAccessKeyId** | AccessKey ID | LTAI**************** |
| **SensitiveAction** | Whether it is a sensitive event | true |
| **SourceIpAddress** | Source IP of the request | 192.168.*.** |
| **EventType** | Event type | ConsoleOperation, ApiCall |
| **RoleName** | Role name | AliyunServiceRoleForActionTrail |
| **PrincipalId** | Principal ID | Used in combined queries |

## Restriction Rules

### General Rules

1. Key and Value are **case-sensitive** and must match exactly
2. At most 2 AttributeItem entries; any additional ones are ignored
3. Two conditions are combined with **AND** semantics (both must match)
4. When the same Key appears twice, only the second one takes effect

### Supported Two-Condition Combinations

#### With ServiceName as the Primary Key

Can be combined with any one of the following keys:
- EventName
- User
- PrincipalId
- RoleName
- ResourceName
- EventRW
- SensitiveAction
- EventType

#### With ResourceName as the Primary Key

Can be combined with any one of the following keys:
- ResourceType
- EventName
- User
- RoleName
- ServiceName

#### Special Combination

- EventType + EventName

### Unsupported Combinations (Results Become Unreliable)

- User + EventName (not in the supported list)
- EventRW + EventName (not in the supported list)
- SourceIpAddress + any other key (SourceIpAddress can only be used alone)

## Usage Examples

### Example 1: Query write operations of the Vpc service

```
LookupAttribute.1.Key = ServiceName
LookupAttribute.1.Value = Vpc
LookupAttribute.2.Key = EventRW
LookupAttribute.2.Value = Write
```

### Example 2: Query operation records of a specific resource

```
LookupAttribute.1.Key = ResourceName
LookupAttribute.1.Value = eip-bp1234567890abcde
```

### Example 3: Query by service + event name

```
LookupAttribute.1.Key = ServiceName
LookupAttribute.1.Value = Vpc
LookupAttribute.2.Key = EventName
LookupAttribute.2.Value = AllocateEipAddress
```

### Example 4: Query operations of a specific user under a service

```
LookupAttribute.1.Key = ServiceName
LookupAttribute.1.Value = Ecs
LookupAttribute.2.Key = User
LookupAttribute.2.Value = Alice
```

## Common Mistakes

- Wrong ServiceName case: `vpc` (wrong) -> `Vpc` (correct)
- Wrong EventRW case: `read` (wrong) -> `Read` (correct)
- Using unsupported combinations: the system may return empty or inaccurate results
