# CFW API Error Codes

Common error codes across Cloud Firewall Internet Firewall APIs.

## Capacity Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorInstanceOpenIpNumExceed` | PutEnableFwSwitch, PutEnableAllFwSwitch | Protected IP count reached instance limit | Upgrade CFW edition or reduce protected IPs |
| `ErrorInstanceOpenIpRegionNumExceed` | PutEnableFwSwitch, PutEnableAllFwSwitch | Region protection quota exceeded | Upgrade CFW edition |
| `ErrorGeneralInstanceSpecFull` | PutEnableFwSwitch, PutEnableAllFwSwitch | Instance specification full | Upgrade instance |
| `ErrorBandwidthPenalty` | PutEnableFwSwitch, PutEnableAllFwSwitch | Bandwidth overuse enforcement active | Wait for enforcement to end or contact support |

## State Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorInstanceStatusNotNormal` | All write APIs | Instance status abnormal (unpaid, etc.) | Check instance status and billing in CFW console |

## Parameter Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorParamsNotEnough` | PutEnableFwSwitch, PutDisableFwSwitch, PutEnableAllFwSwitch, PutDisableAllFwSwitch | Missing required parameters | Provide at least one of: --ips, --regions, --resource-types, --ip-version |
| `ErrorParamsInvalid` | PutEnableFwSwitch | Invalid parameter values | Check IP format, region ID, or resource type values |

## Auth Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorAuthentication` | All APIs | Authentication failed | Check AK/SK validity via `validate-cli.sh` |

## Internal Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorDBSelect` | DescribeAssetList, PutDisableFwSwitch, PutDisableAllFwSwitch | Database query error | Retry after a moment |
| `ErrorDBTxError` | PutEnableFwSwitch | Database transaction error | Retry |
| `ErrorRecordLog` | PutDisableFwSwitch, PutEnableAllFwSwitch, PutDisableAllFwSwitch | Log write failure | Retry |
| `ErrorDbFailed` | PutEnableAllFwSwitch | Database access error | Retry |
