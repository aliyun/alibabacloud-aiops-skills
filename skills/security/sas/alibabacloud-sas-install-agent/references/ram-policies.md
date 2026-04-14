# RAM Permission Manifest

RAM permissions required by this skill:

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read this file (`references/ram-policies.md`) to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Security Center (SAS)

- `yundun-sas:DescribeCloudCenterInstances` -- Query server client status
- `yundun-sas:DescribeInstallCodes` -- Query existing install code list
- `yundun-sas:AddInstallCode` -- Create new install code
- `yundun-sas:RefreshAssets` -- Sync asset list
- `yundun-sas:CreateOrUpdateAssetGroup` -- Create or update asset group
- `yundun-sas:GetAuthSummary` -- Query authorization quota statistics
- `yundun-sas:DescribeVersionConfig` -- Query version and instance details
- `yundun-sas:GetServerlessAuthSummary` -- Query Serverless authorization status
- `yundun-sas:ModifyPostPayModuleSwitch` -- Modify pay-as-you-go module switches
- `yundun-sas:BindAuthToMachine` -- Bind/unbind server authorization
- `yundun-sas:UpdatePostPaidBindRel` -- Change pay-as-you-go version binding
- `yundun-sas:DescribePropertyScaDetail` -- Query asset fingerprint software
- `yundun-sas:AddUninstallClientsByUuids` -- Uninstall agent from specified servers
- `yundun-sas:ModifyPushAllTask` -- Dispatch security check tasks
- `yundun-sas:ModifyStartVulScan` -- Trigger one-click vulnerability scan
- `yundun-sas:DescribeGroupedVul` -- Query grouped vulnerability info
- `yundun-sas:ExecStrategy` -- Execute baseline check strategy
- `yundun-sas:DescribeStrategy` -- Query baseline check strategy list
- `yundun-sas:ListCheckItemWarningSummary` -- Query baseline check risk statistics
- `yundun-sas:DescribeSuspEvents` -- Query security alert events
- `yundun-sas:GenerateOnceTask` -- Trigger asset fingerprint collection task
- `yundun-sas:CreateAssetSelectionConfig` -- Create asset selection configuration
- `yundun-sas:AddAssetSelectionCriteria` -- Add assets to selection configuration
- `yundun-sas:UpdateSelectionKeyByType` -- Associate asset selection to business
- `yundun-sas:CreateVirusScanOnceTask` -- Create virus scan task
- `yundun-sas:GetVirusScanLatestTaskStatistic` -- Query virus scan progress
- `yundun-sas:ListVirusScanMachine` -- Query virus scan machine list
- `yundun-sas:ListVirusScanMachineEvent` -- Query machine virus events
- `yundun-sas:DescribeOnceTask` -- Query scan task execution status

## Elastic Compute Service (ECS)

- `ecs:DescribeInstances` -- Query ECS instance basic info
- `ecs:DescribeCloudAssistantStatus` -- Query cloud assistant online status
- `ecs:RunCommand` -- Execute commands remotely via cloud assistant
- `ecs:InvokeCommand` -- Trigger an existing command on ECS instances
- `ecs:DescribeInvocationResults` -- Query cloud assistant command execution results
