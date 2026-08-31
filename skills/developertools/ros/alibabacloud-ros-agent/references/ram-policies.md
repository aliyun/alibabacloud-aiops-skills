# RAM permissions

## Required actions

The selected credential needs only the ROS API actions used by this bridge:

| Action | Required when | Access |
|---|---|---|
| `ros:StartChat` | Every ROS Agent conversation, continuation, or permission response | Write |
| `ros:StopChat` | The user explicitly cancels an active ROS Agent conversation | Write |

Do not grant `ros:*` or a product-wide `FullAccess` policy. If the RAM service supports resource-level scoping for
the selected ROS API, restrict `Resource` to the applicable account and region; otherwise use the API's documented
resource scope. The remote ROS Agent's downstream permissions are managed by the service and are not a reason to
broaden the caller credential used by this Skill.

## Failure handling

On `Forbidden`, `Forbidden.RAM`, `NoPermission`, or another authorization response, return the sanitized bridge
error and request ID when available. Do not enumerate credentials, switch identities, edit CLI configuration, or
fall back to a direct API or CLI invocation.
