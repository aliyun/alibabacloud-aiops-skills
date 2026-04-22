---
name: alibabacloud-network-alb-http-to-https
description: >
  Configure HTTP-to-HTTPS redirects on Alibaba Cloud ALB, including inspecting the
  current listener and rule setup, creating missing HTTP or HTTPS listeners, and
  adding a redirect rule that forces HTTP requests to HTTPS. Use this skill when a
  user wants to enable HTTPS enforcement on an existing ALB, redirect port 80
  traffic to 443, or check whether an ALB already has a correct HTTP-to-HTTPS
  redirect configuration.
license: Apache-2.0
compatibility: >
  Requires Alibaba Cloud CLI (>= 3.3.3) with AI-Mode support, credentials configured
  via `aliyun configure` or environment variables, the `aliyun-cli-alb` and
  `aliyun-cli-cas` product plugins, and `openssl` for generating self-signed
  test certificates.
metadata:
  domain: aiops
  owner: alb-team
  contact: alb-agent@list.alibaba-inc.com
allowed-tools: Bash Read
---

# ALB HTTP to HTTPS redirect

Use Alibaba Cloud CLI to configure HTTP-to-HTTPS 301/302 redirects on ALB. Write scripts poll resource status after creation until listeners or rules become available.

All Alibaba Cloud service calls in this skill must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https`.

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
>
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.
>
> Then **[MUST]** run the following commands before Alibaba Cloud service calls:
>
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https
> aliyun configure ai-mode enable
> ```
>
> After all skill commands finish, **[MUST]** disable AI-Mode so later manual CLI
> calls are not mislabeled as AI/Skill traffic:
>
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
>
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
>
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

This skill requires the following RAM permissions. See `references/ram-policies.md` for the complete list.

**Core Permissions Required**:

- ALB: `ListLoadBalancers`, `GetLoadBalancerAttribute`, `ListListeners`, `GetListenerAttribute`
- ALB: `CreateListener`, `UpdateListenerAttribute`, `ListRules`, `CreateRule`, `CreateServerGroup`
- CAS: `UploadUserCertificate`, `DeleteUserCertificate`

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
>
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Decision tree

Inspect the current state first, then choose the next action:

1. Use `get_load_balancer.sh` to confirm the ALB exists and is `Active`. Do not continue with certificate upload, server group creation, listener creation, or rule creation until the ALB existence check passes.
2. If the user provides an ALB name, or the identifier is ambiguous, resolve it to a real load balancer ID first with `list_load_balancers.sh`. Only pass a confirmed ALB ID to scripts that require `--lb-id`.
3. Use `list_listeners.sh` to inspect existing listeners.
4. Branch on the result:
   - **No HTTPS listener** -> Ask whether to create one. A server group ID and certificate ID are required. If no certificate exists, suggest `generate_test_cert.sh` plus `upload_cert.sh` to generate and upload a self-signed test certificate.
   - **HTTPS listener certificate must be replaced temporarily** -> Use `get_listener.sh` to capture the actual current default certificate ID, generate and upload the temporary certificate, use `update_listener.sh` to bind it, verify with `get_listener.sh`, then use `update_listener.sh` again to restore the captured certificate ID. If the user-provided original certificate ID differs from the actual listener certificate, report the difference and use the actual captured certificate ID as the rollback target.
   - **HTTPS exists, but no HTTP listener** -> Ask whether to create `HTTP:80` with a redirect. The HTTP listener's default forwarding action must reference a server group, so an empty placeholder server group may be needed.
   - **HTTP listener exists, but no redirect rule** -> Use `get_listener.sh` to confirm the protocol is HTTP, then use `list_rules.sh` to find occupied priorities and create a redirect rule with the highest available priority. `list_listeners.sh` output does not replace this listener-specific check.
   - **Existing redirect rule** -> Inform the user that redirect is already configured and show the current rule.

## Workflow

```bash
# 1. Verify CLI version, refresh plugins, and mark this run as AI/Skill traffic
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https
aliyun configure ai-mode enable

# 2. Verify credentials without printing secrets
aliyun configure list

# 3. Resolve ALB name to ID if needed
bash scripts/list_load_balancers.sh --region <REGION> --lb-names <ALB_NAME>

# 4. Inspect current state and stop early if the ALB does not exist
bash scripts/get_load_balancer.sh --region <REGION> --lb-id <ALB_ID>
bash scripts/list_listeners.sh --region <REGION> --lb-id <ALB_ID>

# 5. Generate and upload a certificate only if a new HTTPS listener is needed and no usable certificate exists
bash scripts/generate_test_cert.sh --domain <DOMAIN>
bash scripts/upload_cert.sh --name <NAME> --cert-file /tmp/alb-test-certs/cert.pem --key-file /tmp/alb-test-certs/key.pem

# 5a. Replace an existing HTTPS listener certificate only when requested
bash scripts/get_listener.sh --region <REGION> --listener-id <HTTPS_LSN_ID>
bash scripts/update_listener.sh --region <REGION> --listener-id <HTTPS_LSN_ID> --cert-id <NEW_CERT_ID>
bash scripts/get_listener.sh --region <REGION> --listener-id <HTTPS_LSN_ID>
# For temporary test certificates, restore the captured original certificate and delete the uploaded test certificate
bash scripts/update_listener.sh --region <REGION> --listener-id <HTTPS_LSN_ID> --cert-id <ORIGINAL_CERT_ID>
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https cas delete-user-certificate --cert-id <NEW_CERT_ID>

# 6. Create an empty server group only if an HTTP listener must be created and no placeholder server group is available
# Use the VPC ID from the ALB details in step 4 instead of trusting free-form VPC input
bash scripts/create_server_group.sh --region <REGION> --name http-placeholder --vpc-id <VPC_ID>

# 7. Create the HTTPS listener if it does not exist
bash scripts/create_listener.sh --region <REGION> --lb-id <ALB_ID> \
    --protocol HTTPS --port 443 --forward-sg <SGP_ID> --cert-id <CERT_ID>

# 8. Create the HTTP listener if it does not exist, using the placeholder server group
bash scripts/create_listener.sh --region <REGION> --lb-id <ALB_ID> \
    --protocol HTTP --port 80 --forward-sg <SGP_PLACEHOLDER>

# 9. Confirm the specific listener protocol, inspect used priorities, and add the redirect rule
# This GetListenerAttribute step is mandatory even when list_listeners.sh already showed the listener.
bash scripts/get_listener.sh --region <REGION> --listener-id <HTTP_LSN_ID>
bash scripts/list_rules.sh --region <REGION> --listener-id <HTTP_LSN_ID>
bash scripts/create_rule.sh --region <REGION> --listener-id <HTTP_LSN_ID> \
    --name "force-https" --priority <AVAILABLE> --action-type redirect

# 10. Verify
bash scripts/list_listeners.sh --region <REGION> --lb-id <ALB_ID>
bash scripts/list_rules.sh --region <REGION> --listener-id <HTTP_LSN_ID>

# 11. Disable AI-Mode after the skill run
aliyun configure ai-mode disable
```

Not every step is required. Skip any step already satisfied by the current state.

## Defaults & rules

- Listener default forwarding supports only forwarding to a server group. Rule-based redirect and fixed-response behavior must be implemented through rules.
- An HTTP listener must reference a placeholder server group, which may be empty, and then use a redirect rule to cover all requests.
- For temporary certificate replacement, record the actual current certificate from `get_listener.sh` before updating. Do not rely only on a user-provided certificate ID for rollback if the live listener shows a different default certificate.
- Before reading or creating redirect rules on a listener, explicitly confirm that exact listener with `get_listener.sh` so the run includes `GetListenerAttribute`. Do not treat user text, ALB names, listener descriptions, or `list_listeners.sh` output as a replacement for this check.
- A redirect rule can be attached only to an HTTP listener. `create_rule.sh` validates the listener protocol automatically, but still run the standalone `get_listener.sh` check first so the protocol confirmation is visible in the execution trace.
- Update existing HTTPS or QUIC listener certificates only through `update_listener.sh`. It uses ALB plugin mode with the flat list argument format `--certificates CertificateId=<CERT_ID>` and verifies the default certificate after update.
- After a temporary certificate test, always restore the captured original certificate with `update_listener.sh`, verify the listener again with `get_listener.sh`, then delete the uploaded temporary certificate with `cas delete-user-certificate`.
- `create_rule.sh` checks for priority conflicts automatically and returns an error with the conflicting rule if one exists.
- The default is HTTP `301` permanent redirect, which browsers may cache. Use `--redirect-code 302` during testing.
- The certificate service (`cas`) is global. `upload_cert.sh` calls the `cas.aliyuncs.com` endpoint.
- `aliyun configure list` is only a local credential check and does not need `--user-agent`.
- AI-Mode must be enabled before Alibaba Cloud service calls and disabled after the skill run. Set the AI-Mode user agent to `AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https` so cloud-side audit can identify this skill.
- All Alibaba Cloud service calls in this skill must set `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https`. The bundled scripts do this through `scripts/common.sh`, and any manual `aliyun alb ...` or `aliyun cas ...` command must include the same flag.
- ALB and CAS commands use product-plugin mode with lowercase-hyphenated subcommands and the global `--region` parameter.
- Query scripts automatically aggregate paginated results in plain-text output so the first page is not shown in isolation.
- Query scripts return structured raw service responses when `--json` is used, which is useful for automation.
- Write scripts perform scenario-specific prechecks before execution, such as instance state, port conflicts, and rule priority conflicts.

## Scripts

| Script | Purpose |
|------|------|
| `scripts/list_load_balancers.sh` | List ALB instances and resolve a load balancer name to its load balancer ID |
| `scripts/get_load_balancer.sh` | Get load balancer details |
| `scripts/list_listeners.sh` | List listeners |
| `scripts/get_listener.sh` | Get listener details, including protocol, certificate, and default forwarding action |
| `scripts/list_rules.sh` | List forwarding rules, or query a single rule with `--rule-id` |
| `scripts/generate_test_cert.sh` | Generate a self-signed test certificate with `openssl` |
| `scripts/upload_cert.sh` | Upload a certificate to Alibaba Cloud Certificate Management Service and return the certificate ID |
| `scripts/update_listener.sh` | Replace the default certificate on an existing HTTPS or QUIC listener and verify the result |
| `scripts/create_server_group.sh` | Create an empty server group for the HTTP listener default forwarding placeholder |
| `scripts/create_listener.sh` | Create an HTTP, HTTPS, or QUIC listener |
| `scripts/create_rule.sh` | Create a forwarding rule; use `--action-type redirect`, `--action-type forward-group`, or `--action-type fixed-response` |

Each script supports `--help`, `--json`, `--dry-run` for write operations, and `--output FILE`.

## References

- `references/ram-policies.md`: Required RAM permissions for this skill
- `related_apis.yaml`: API inventory for the ALB and CAS operations covered by this skill

## Rollback

Deleting the redirect rule does not affect the HTTPS listener or backend services.

```bash
# Delete only the rule
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https alb delete-rule --region <REGION> --rule-id <RULE_ID>

# Or delete the HTTP listener as well
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-alb-http-to-https alb delete-listener --region <REGION> --listener-id <HTTP_LSN_ID>
```

## Troubleshooting

| Symptom | Cause | Resolution |
|------|------|------|
| Too many redirects with `ERR_TOO_MANY_REDIRECTS` | The HTTPS listener also has a redirect | Check that the HTTPS listener defaults to forwarding to a server group |
| Connection fails after redirect | The HTTPS listener is not running or has no certificate attached | Check the HTTPS listener status and certificate |
| Only some domains are redirected | The rule condition restricts `Host` | Remove the `--host` condition or use `/*` to match all paths |
| Listener creation fails with a port conflict | A listener already exists on the same port | Add the rule to the existing listener instead |
| The browser does not redirect | The `301` response is cached | Clear the cache, use incognito mode, or test with `curl -I` |
