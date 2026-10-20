# EIAM auxiliary API contract and availability

Product: EIAM (`eiam`). Version: `2021-12-01`. Protocol: RPC, POST.
Both operations are declared PRIVATE in the current backend. Declaration in
`related_apis.yaml` does not make a private operation public or register its
metadata in the evaluation service. Do not invent public support, required
parameters, response bodies, or authorization from a successful historical call.

| Operation | Required request fields (strings) | Response fields |
| --- | --- | --- |
| GetCloudAccountRoleConfig | InstanceId, CloudAccountId, CloudAccountRoleId | RequestId; CloudAccountRoleConfig containing the selected vendor configuration |
| CheckCloudAccountRoleConfig | InstanceId, CloudAccountId, CloudAccountRoleId | RequestId; LastCheckTime, Result, ErrorReason (ErrorLevel, ErrorCode, ErrorMessage) |

For supported providers, configuration containers are
AlibabaCloudAccountRoleConfig, AwsCloudAccountRoleConfig and
TencentCloudAccountRoleConfig. Use only the selected vendor's actual container.
Read role name, trust configuration, policy configuration and session duration
from that returned container; never substitute another vendor's data.

The gateway declarations authorize these actions against
`acs:eiam:{regionId}:{accountId}:*`. An instance-scoped policy may not match this
resource even when it names the correct action. Do not broaden access to fix it
without explicit approval of the wider read scope. Deployment behavior must be
verified; a denied Get operation does not prove a Check operation is also denied.
Record the actual failed action, sanitized code and RequestId, then stop that
workflow. Do not continue cloud calls merely to obtain a healthy result.

The bundled SDK adapter validates the three IDs and expected EIAM owner before
sending the request. Missing input must fail locally; SDK authorization and API
availability failures are distinct from missing input. API information-completeness
and error-type metrics remain unavailable if the platform cannot retrieve the
private API metadata; local documentation cannot change that platform registry.

Contract source: BaseCloudAccountRoleRequest and its BaseCloudAccountRequest
parent, OpenCloudAccountRoleHelperApiService response mappings,
OpenCloudAccountRoleConfigDTO and HealthCheckResult in the EIAM backend.
