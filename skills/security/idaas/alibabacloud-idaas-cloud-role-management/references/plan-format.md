# Request and approval artifacts

Local request (examples are not live targets):

```json
{"instance_id":"idaas_example","vendor":"alibaba_cloud","account_id":"1234567890123456","role_name":"ecs-reader","permission_intent":"Read explicitly approved ECS APIs in cn-hangzhou only"}
```

Supported vendors: alibaba_cloud, aws, tencent_cloud. Account IDs are full owner
identifiers, not caller subaccount IDs. The local name rule is a conservative
portable subset; the selected vendor's current schema remains authoritative.

Sealing requires a completed discovery plan:

```json
{
  "instance_id":"idaas_example",
  "vendor":"alibaba_cloud",
  "account_id":"1234567890123456",
  "cloud_account_id":"ca_example",
  "role_name":"ecs-reader",
  "permission_intent":"Read the approved ECS instance APIs in cn-hangzhou",
  "eiam_profile":"eiam-admin",
  "cloud_profile":"target-cloud",
  "eiam_owner_id":"1234567890123456",
  "site":"china_mainland",
  "project_selection":"server_default",
  "mode":"create",
  "discovery_evidence":["discovery.json"],
  "business_policies":[{"kind":"custom","name":"ecs-reader-policy","document":{"Version":"1","Statement":[{"Effect":"Allow","Action":["ecs:DescribeInstances"],"Resource":["*"],"Condition":{"StringEquals":{"acs:Region":"cn-hangzhou"}}}]}}],
  "trust_constraints":{"provider_id":"read-from-account","issuer":"https://verified.example","audience":"read-from-config","max_session_duration":3600},
  "changes":["Create the named EIAM user role and cloud role","Bind only the approved policy; no shared provider changes"]
}
```

The sample policy is not a published regional permission template: its Action,
Resource and Condition support must be verified against official metadata before
use. The helper deliberately rejects wildcard business actions; enumerate actual
read APIs. Managed policies require kind, exact name/id, version, and the read-back
document in the sealed plan. The helper validates structure, not IAM semantics.

`mode` is create, register, reuse or repair. Repair means only a disclosed
in-place trust difference on this role; existing shared policies are immutable.
No cleanup or migration mode exists. A server_default project is explicit user
acceptance of server default behavior, not a fabricated internal project ID.

Seal outputs `{schema_version, plan, sha256, client_token}`. The token is derived
from the complete plan digest. Preserve the sealed file for resume and keep
approval separately in trusted conversation/execution context. Never hand edit
the file after approval; check recomputes the digest and token before use.
Evidence paths must refer to actual captured responses. File existence alone
does not prove cloud discovery, and seal does not examine their content.
