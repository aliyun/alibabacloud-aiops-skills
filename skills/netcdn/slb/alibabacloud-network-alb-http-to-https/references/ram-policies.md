# RAM Permissions

This skill requires the following RAM permissions.

## required_permissions

- `alb:ListLoadBalancers` - List ALB instances when locating the target load balancer.
- `alb:GetLoadBalancerAttribute` - Read ALB details and confirm the load balancer is in a usable state.
- `alb:ListListeners` - Inspect existing HTTP and HTTPS listeners.
- `alb:GetListenerAttribute` - Read listener protocol, default action, and certificate configuration.
- `alb:ListRules` - Inspect existing redirect and forwarding rules and detect priority conflicts.
- `alb:CreateServerGroup` - Create an empty placeholder server group for an HTTP listener when needed.
- `alb:CreateListener` - Create a missing HTTP or HTTPS listener.
- `alb:CreateRule` - Create the HTTP-to-HTTPS redirect rule.
- `cas:UploadUserCertificate` - Upload a user certificate when a test or temporary certificate is needed.

## Notes

- This is a read-write skill and therefore legitimately requires write permissions.
- Do not replace these granular permissions with wildcard permissions such as `alb:*` or `cas:*`.
- If the target ALB and HTTPS certificate already exist, only a subset of the permissions may be exercised in a given run.
