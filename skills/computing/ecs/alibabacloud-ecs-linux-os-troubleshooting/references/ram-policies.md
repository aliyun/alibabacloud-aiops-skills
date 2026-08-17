# RAM Policies

This file declares the minimum RAM permissions required by `alibabacloud-ecs-linux-os-troubleshooting`. Grant only the actions required for the selected troubleshooting path. Do not use product-wide wildcard permissions.

## required_permissions

### Read-only metadata and evidence collection

`ecs:DescribeInstances` — Query ECS instance status, zone, image, network, billing, and basic runtime metadata.

`ecs:DescribeInstanceAttribute` — Query detailed attributes for a single ECS instance.

`ecs:DescribeDisks` — Query system and data disk metadata, attachment status, device name, zone, and portability.

`ecs:DescribeImages` — Query image metadata when boot or image compatibility evidence is needed.

`ecs:DescribeNetworkInterfaces` — Query primary and secondary ENI configuration for network troubleshooting.

`ecs:DescribeSecurityGroups` — Query security groups attached to an ECS instance.

`ecs:DescribeSecurityGroupAttribute` — Query inbound and outbound security group rules.

`ecs:DescribeUserData` — Query ECS UserData content for cloud-init and userdata troubleshooting.

`ecs:GetInstanceScreenshot` — Obtain a VNC console screenshot for boot, display, and login evidence.

`ecs:GetInstanceConsoleOutput` — Obtain serial console output for boot and kernel evidence.

`ecs:DescribeInstanceHistoryEvents` — Query instance system events to determine whether an abnormality originates from the platform side.

`ecs:DescribeInstanceTypes` — Query instance type metadata for performance and capacity comparison.

`ecs:DescribeInstanceTypeFamilies` — Query available instance type families.

`ecs:DescribeImageSupportInstanceTypes` — Query image and instance type compatibility.

`ecs:DescribeDiagnosticReports` — Query historical ECS diagnostic reports.

`ecs:DescribeDiagnosticReportAttributes` — Query the status and detailed results of a diagnostic report.

`ecs:DescribeDiagnosticMetricSets` — Enumerate the available diagnostic metric sets before creating a diagnostic report.

`cms:QueryMetricMeta` — Enumerate the CloudMonitor metrics available for ECS before querying a trend (RAM action for the `DescribeMetricMetaList` / `cms describe-metric-meta-list` call; CloudMonitor read APIs authorize under the legacy `cms:Query*` action codes, not the API name).

`cms:QueryMetricList` — Query historical CloudMonitor metric trends to locate the abnormal time window (RAM action for the `DescribeMetricList` / `cms describe-metric-list` call).

`cms:QueryMetricLast` — Query the latest CloudMonitor metric value of an instance (RAM action for the `DescribeMetricLast` / `cms describe-metric-last` call).

`ecs:DescribeCloudAssistantStatus` — Query Cloud Assistant availability before in-instance command execution.

`ecs:DescribeInvocations` — Query Cloud Assistant command invocation status.

`ecs:DescribeInvocationResults` — Query Cloud Assistant command stdout, stderr, and exit code.

### User-confirmed diagnostic execution

`ecs:CreateDiagnosticReport` — Create an ECS diagnostic report after the user confirms the diagnostic metric set execution.

`ecs:RunCommand` — Run read-only GuestOS evidence collection commands through Cloud Assistant, or run explicitly confirmed offline-preparation commands on a rescue instance.

`ecs:StopInvocation` — Stop a Cloud Assistant command that remains running or exceeds the troubleshooting timeout.

### User-confirmed state-changing operations

These actions are required only for the offline troubleshooting workflow in `references/utils/guestos-pe-prep.md` and for the instance restart step in `references/instance-stuck-starting.md`. They change ECS resource state and require explicit user confirmation before execution.

`ecs:StopInstance` — Stop the problematic instance before detaching its system disk, or stop it before a confirmed restart attempt.

`ecs:DetachDisk` — Detach the system disk from the problematic instance or detach it from the rescue instance during rollback.

`ecs:AttachDisk` — Attach the system disk to the rescue instance for offline troubleshooting, and reattach it to the original instance during rollback.

`ecs:StartInstance` — Start the original instance after the system disk is reattached, or start it again during a confirmed restart attempt.
