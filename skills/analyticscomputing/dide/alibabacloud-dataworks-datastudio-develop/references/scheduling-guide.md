# Scheduling Configuration Guide

Scheduling defines the frequency at which nodes automatically execute in the production environment. The DataWorks scheduling system automatically generates cycle instances based on the configured scheduling cycle, and triggers execution based on inter-node dependencies and the scheduled time of each instance.

## Core Concepts

### Cycle Instances

The scheduling system generates a runtime entity, called a cycle instance, for each business date based on the scheduling configuration of a cycle task (e.g., run daily at midnight). The task's execution, status, and logs are all associated with this instance.

### Cross-Cycle Dependencies

DataWorks supports dependencies between nodes with different scheduling cycles. For example, a daily downstream node can depend on an hourly upstream node. The essence of inter-node dependencies is the dependency between the cycle instances they generate.

### Dry Run

For non-daily scheduled tasks (e.g., weekly, monthly, yearly), on dates that are not designated run dates, the scheduling system generates a "dry run" instance. This instance immediately changes to "Success" status once its scheduled time arrives, but **does not execute the node's code logic**. Dry runs primarily serve to bridge dependencies, ensuring that downstream daily nodes can trigger normally.

- Instance run status is Success, execution duration is 0 seconds, no execution logs
- Does not consume scheduling or compute resources
- Does not block downstream node execution

## Scheduling Execution Conditions

A cycle instance must **simultaneously satisfy** both of the following conditions to execute:

1. All upstream instances it depends on have successfully executed (including dry-run-success instances)
2. The instance's own scheduled time has been reached

Therefore, the configured scheduling time is only the **expected scheduled time**; the actual execution time of a node is affected by upstream completion time, available resources, actual execution conditions, and other factors.

## Scheduling Differences: Workflows vs. Standalone Nodes

- **Workflow nodes**: Scheduling time is configured uniformly on the workflow; individual nodes within the workflow cannot have their own scheduling times
- **Standalone nodes**: Scheduling time is independently configured on the node itself

If a node's scheduling cycle differs from other nodes in the workflow, it should be created as a standalone node or placed in a separate workflow.

## Workflow Scheduling Scenarios

### Scenario 1: Unified Start Time

Workflow A->B->C, the entire business flow must start after 3:00 AM. Simply set the start node A's scheduled time to `03:00`. Even if downstream nodes B and C have a default scheduled time of `00:00`, they must wait until A successfully executes at 3:00 AM before starting sequentially.

### Scenario 2: Different Start Times for Each Node

Node A is scheduled at 3:00 AM, Node B is required after 5:00 AM, Node C is required after 6:00 AM. Set the scheduled times for A, B, and C to `03:00`, `05:00`, and `06:00` respectively.

### Scenario 3: Some Nodes Have Specific Start Times

Node A is scheduled at 3:00 AM, Node B is required after 5:00 AM, Node C has no specific requirement. Set A to `03:00` and B to `05:00`. Node C will wait for B to successfully execute after 5:00 AM, then start.

## Scheduling Types and Cron Expressions

DataWorks supports six scheduling cycles: minute, hourly, daily, weekly, monthly, and yearly.

### Daily Scheduling

Runs once at a specified time each day.

```
cron: 00 00 03 * * ?     # Daily at 03:00
cron: 00 30 08 * * ?     # Daily at 08:30
```

### Hourly Scheduling

Runs at intervals within a specified time range. The time range follows the **closed-closed** principle.

```
cron: 00 00 */6 * * ?    # Every 6 hours (00:00, 06:00, 12:00, 18:00)
cron: 00 00 * * * ?      # Every hour
```

### Minute Scheduling

Minimum interval is 1 minute.

```
cron: 00 */30 * * * ?    # Every 30 minutes
cron: 00 */5 * * * ?     # Every 5 minutes
```

### Weekly Scheduling

A **dry run** occurs on non-designated scheduling dates.

```
cron: 00 00 01 ? * MON       # Every Monday at 01:00
cron: 00 00 03 ? * MON,FRI   # Every Monday and Friday at 03:00
```

### Monthly Scheduling

A **dry run** occurs on non-designated dates. Supports the last day of the month.

```
cron: 00 00 02 1 * ?     # 1st of every month at 02:00
cron: 00 00 02 L * ?     # Last day of every month at 02:00
```

### Yearly Scheduling

A **dry run** occurs on non-designated dates.

```
cron: 00 00 02 1 1,4,7,10 ?   # 1st of January/April/July/October at 02:00
```

## Impact of Updating Scheduling Time

After modifying a node's scheduling time and re-deploying, the impact depends on the instance generation method:

- **T+1 next-day generation**: The scheduled times of already-generated instances for the most recent two days (T and T-1) will be updated to the new configuration. Future instances are generated with the new time
- **Immediate instance generation**: New instances are generated immediately based on the new configuration; historical instances remain unchanged

## Business Date

In DataWorks, **business date = scheduled run date - 1**. For example:
- To backfill a weekly task that runs on Monday, the business date should be the previous Sunday
- To backfill a month-end task (running on January 31), the business date should be January 30
- Backfilling on a non-scheduled date will result in a dry run
