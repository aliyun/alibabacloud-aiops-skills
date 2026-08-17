# RAM Permission List

RAM permissions required for this Skill execution:

## Diagnostic Operation Permissions

`ecs:CreateDiagnosticReport` — Create ECS instance diagnostic report

`ecs:DescribeDiagnosticReports` — Query diagnostic report status and results

## Instance Query Permissions (for prerequisite checks)

`ecs:DescribeInstances` — Query ECS instance basic information, verify instance existence

`ecs:DescribeRegions` — Query ECS supported regions

## Cloud Assistant Permissions (for Cloud Assistant Diagnosis)

`ecs:RunCommand` — Execute cloud assistant commands on ECS instances

`ecs:DescribeInvocationResults` — Query cloud assistant command execution results

## Scheduled Diagnosis Permissions (for scheduled/periodic diagnosis)

`ecs:CreateCommand` — Create a cloud assistant command with the fixed GPU diagnosis script

`ecs:InvokeCommand` — Create a periodic schedule (Cron `--frequency`) to run the command on target instances

`ecs:DescribeInvocations` — Verify the scheduled task status (RepeatMode, Frequency, InvocationStatus)

`ecs:StopInvocation` — Stop a scheduled task when the user explicitly requests stopping/deleting it (stopping only; deletion is done manually in the ECS console)