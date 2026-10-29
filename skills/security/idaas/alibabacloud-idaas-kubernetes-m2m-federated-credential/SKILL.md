---
name: alibabacloud-idaas-kubernetes-m2m-federated-credential
description: Enable Kubernetes pods to obtain Alibaba Cloud access tokens via IDaaS EIAM without static credentials (AccessKey). Covers OIDC federated credential provider setup (three JWKS source modes), M2M client application creation, kubernetes-mode application federated credential, PAM feature permission authorization, id-token-bearer exchange verification, and SDK client-config.json generation. Use for Kubernetes pods without AccessKey, ServiceAccount token exchange, OIDC federated credential providers, static JWKS, kubernetes verification mode, id-token-bearer, pod workload identity, K8s-to-EIAM/IDaaS access tokens, or the Kubernetes path of PAM-to-STS.
---

# IDaaS Kubernetes M2M Federated Credential (OIDC, Without AK)

Implement the verified end-to-end flow: **Kubernetes ServiceAccount OIDC token → signature verification by an EIAM OIDC federated credential provider (three JWKS source modes, matching console terminology: Static Fill-in = static, Issuer Address Resolution = dynamic_from_issuer, JWKS URI Resolution = dynamic_from_jwks_uri) → kubernetes-mode application federated credential verification → M2M token issuance using client_credentials → SDK onboarding for PAM-to-STS**.

**Architecture**: Kubernetes Cluster (OIDC Issuer + ServiceAccount Token) → IDaaS EIAM (OIDC Federated Credential Provider + M2M Application + Application Federated Credential) → PAM Feature Permission → M2M Token (id-token-bearer)

All scripts are in `scripts/`. They use **Python 3 with the standard library only**, calling the `aliyun` CLI through subprocess (credentials must already be configured); kubectl is optional (probe first, degrade to paste-back). Run scripts from the workspace root: `python3 scripts/<script>.py`.

Respond in the user's language unless they request otherwise.

Source document: "[PAM]Native Kubernetes Static-Credential-Free STS Token" (DingTalk doc EpGBa2Lm8aZxe5myCzw3bwBEWgN7R35y).

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

## Environment Variables

This skill uses CLI credentials (no additional env vars required for the workflow itself). The SDK client-config output references:
- `KUBERNETES_OIDC_TOKEN_FILE` — path to the SA Token file inside the pod (set by the generated `client-config.json`).

## Phase 0: Prerequisites (Credential Validation, Permission Guidance, kubectl Probe)

1. **CLI installation**: Run `aliyun version`. Require version >= 3.3.3. If not installed or outdated, refer to the Installation section above. Prefer the CDN URL `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz` when GitHub is inaccessible.
2. **Credential validation** (the aliyun CLI has no separate login state; access depends on configured credentials):
   > **Pre-check: Alibaba Cloud Credentials Required**
   >
   > **Security Rules:**
   > - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
   > - **NEVER** ask the user to input AK/SK directly in the conversation or command line
   > - **NEVER** use `aliyun configure set` with literal credential values
   > - **ONLY** use `aliyun configure list` to check credential status
   >
   > ```bash
   > aliyun configure list
   > ```
   > Check the output for a valid profile (AK, STS, or OAuth identity).
   >
   > **If no valid profile exists, STOP here.**
   > 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
   > 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
   > 3. Return and re-run after `aliyun configure list` shows a valid profile

   After `aliyun configure list` shows a valid profile, run `aliyun sts get-caller-identity --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/<session-id> skill-version/<version>"` to validate server-side access:
   - Success → credentials are valid. **Record the returned AccountId**.
   - Failure → distinguish between expired STS credentials or invalid AK credentials (reconfigure or rotate them).
3. **Permission guidance (proactively show this after validation succeeds and before asking questions)**:
   > This skill requires the following RAM permissions:
   > - **Required**: EIAM read/write access (recommended system policy: `AliyunEIAMFullAccess`; alternatively, use the minimal custom policy in `references/ram-policies.md`).
   > - **Not required**: any ECS or RAM permissions.
   >
   > Cluster-side prerequisites (not RAM): Kubernetes >= 1.21 (Bound ServiceAccount Token), API Server configured with `--service-account-issuer`, and business pods able to reach the EIAM instance public endpoint. See `references/ram-policies.md` for the action-to-step mapping.
4. **kubectl probe**: Run `scripts/probe_k8s.py /tmp/idaas-k8s-jwks-<session_id>.json`.
   - `K8S_PROBE=ok` → the cluster is directly reachable; ISSUER and JWKS were collected automatically. Show them for user confirmation; no paste-back needed.
   - `no_kubectl` / `unreachable` (typical in agent sandboxes) → degrade: run `scripts/gen_k8s_commands.py [namespace] [service_account] [pod]` and send the generated command block to the user. Ask them to run it on a **control node** and paste back: 1 Issuer and 3 SA Token (**both required**); 2 JWKS JSON is **only needed for Static Fill-in mode** (request it via the blocking gate in Round 1 when the issuer is private, or after mode selection in Round 3 for public issuers — never ask for it up front).
5. **Permission Failure Handling**:
   > **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
   > 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
   > 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
   > 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

**Script / Terraform execution:** Inject both scoped values inline:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/deploy.py

# Terraform
TF_VAR_session_id={session-id} TF_VAR_skill_version={skill-version} terraform apply
# provider: configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/${var.session_id} skill-version/${var.skill_version}"
```

Scripts and Terraform configs MUST require both values and construct the same UA product.
Generated Terraform providers MUST set `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/${var.session_id} skill-version/${var.skill_version}"`.

### Skill Switch Isolation
- This skill **must not modify global state** or the configuration of other skills.
- All temporary files (SA token, JWKS, intermediate outputs) must include the session ID in their filename (e.g. `/tmp/sa_token_<session_id>.jwt`, `/tmp/idaas-k8s-jwks-<session_id>.json`) and be deleted after use.
- If the user switches to a different skill mid-conversation, this skill's session state is considered stale; generate a new session ID on the next invocation.

## Interaction Rules (Required for User Experience)

- Collect all parameters marked **[Ask]** below using **AskUserQuestion**. **Do not assume answers on the user's behalf**.
- Provide a **suggested default** for every name question, marking the option "(Recommended)". The user can always supply a custom value through **Other**.
- For list selections (IDaaS instances, OIDC providers, M2M applications), first show the complete list in a table in the **message body**, including IDs, names, and key settings. Include only the most representative ≤3 entries plus Other in AskUserQuestion options (maximum 4 options).
- **Combine independent questions** into a single AskUserQuestion call (maximum 4 questions per call) to reduce interaction rounds.
- Check for **name conflicts** using List APIs before creation. If a name conflicts, append `-2` or `-3` to the suggested name and explain this in the message body; no extra question round is needed.
- Use parameters the user has already supplied (instance IDs, names, namespace/SA) directly. **Do not ask again**.
- **User-facing commands must be zero-dependency and unique**: only kubectl (plus POSIX grep/awk when unavoidable); never require python3/jq on cluster nodes (ACK nodes and CloudShell may lack them — verified 2026-10). Give exactly one command per artifact; parsing JSON/JWT is the skill's job, never the user's. Do not show internal script commands to the user; run them silently and report results.
- Pasted SA Tokens are sensitive: save to session-scoped temporary files (delete after use) and truncate when displayed.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Region | Required | EIAM instance region (supported: cn-hangzhou, cn-beijing, cn-hongkong, ap-southeast-1, ap-southeast-5, ap-northeast-2, eu-central-1) | cn-hangzhou |
| IDaaS Instance ID | Required | EIAM instance (selected from ListInstances) | — |
| Provider Name | Required | OIDC federated credential provider name | k8s-oidc-trust |
| JWKS Source Mode | Required | static / dynamic_from_issuer / dynamic_from_jwks_uri | dynamic_from_issuer (public issuer) |
| M2M Client App Name | Required | M2M client application name | k8s-m2m-client |
| Credential Name | Required | Application federated credential name (≤64 chars) | k8s-oidc-credential |
| Namespace | Required | Kubernetes namespace (from SA token parse) | parsed from token |
| ServiceAccount | Required | Kubernetes ServiceAccount name (from SA token parse) | parsed from token |
| Trust Condition | Optional | DSL expression for additional trust constraints | empty |
| PodNamePrefix | Optional | Pod name prefix filter for credential verification | empty |
| Scope | Required | M2M token scope | urn:cloud:idaas:pam\|cloud_account_role:obtain_access_credential |

## Phase 1: Collect Parameters in Four Rounds

### Round 1 [Ask]: Region and Cluster Artifacts (Issuer + SA Token)
- Q1 Region: `cn-hangzhou` (Recommended) / `cn-beijing` / `ap-southeast-1` / `eu-central-1` + Other.
  (Supported EIAM regions: cn-hangzhou, cn-beijing, cn-hongkong, ap-southeast-1, ap-southeast-5, ap-northeast-2, eu-central-1.)
- Q2 Cluster artifacts: if the Phase 0 probe returned `ok`, show the ISSUER for confirmation. Otherwise the command block was already sent; ask the user to paste back **two items**: the **Issuer** (command 1; its output is the discovery JSON — the user pastes the whole JSON and **the agent extracts the issuer field**; when parsing, note the in-cluster `jwks_uri` may be a broken value such as `https://:6443/openid/v1/jwks` with an empty host (observed on ACK) — flag that it must not be used for JWKS URI Resolution) and **one SA Token** (command 3, recommended `kubectl create token <sa> -n <namespace> --duration=1h`, where `<sa>` is the ServiceAccount used by the business pod and `<namespace>` its namespace; **both default to `default` when no dedicated SA exists**, and must match the credential's ns/sa in Round 4). **Do not ask for JWKS (command 2) yet** — whether it is needed depends on the issuer reachability check below.

Immediately after receiving the token, run `scripts/parse_sa_token.py <token_file>` (this is how aud/iss auto-fill works; **never ask the user to type these values**):
- `ISS=` → provider Issuer, auto-filled (cross-check against the discovery issuer the user pasted; report any mismatch)
- `AUD_PRIMARY=` → provider Audiences recommendation (primary aud: the value equal to the issuer if present, else the first array element); `AUD_ALL=` for reference
- `NS=` / `SA=` → Round 4 credential Namespace/ServiceAccount recommendations
- `EXP=` → expiry reminder; show the parse table in the message body for confirmation

Then immediately run `scripts/check_issuer_public.py <ISS> /tmp/idaas-k8s-jwks-<session_id>.json` to probe issuer public reachability (result drives the flow branch; the sandbox probe is advisory — in dynamic modes IDaaS performs the authoritative synchronous fetch at creation time):
- **`ISSUER_PUBLIC=no` (private issuer, typical for self-managed clusters) → JWKS blocking gate**: immediately ask the user to paste the JWKS JSON from command 2 (save to the session-scoped path; `read_jwks_file` validates a non-empty keys array). **Do not send the next question round until it is received.** The JWKS source mode is determined as Static Fill-in (the only feasible option — state this in the message body; skip the mode question in Round 3).
- **`ISSUER_PUBLIC=yes` (public issuer, typical for managed clusters) →** the user does not need to export JWKS manually — the script fetched and saved it (`JWKS_FILE=`, `JWKS_URI_OK=`); used for Round 2 kid-staleness comparison and directly usable if the user still picks Static Fill-in in Round 3. The mode question stays in Round 3 (recommend Issuer Address Resolution).

Then run `scripts/list_instances.py <region>` to retrieve the instance list.

### Round 2 [Ask]: IDaaS Instance (+ optional Trust Condition)
- Q1 Instance: select from the list (show the complete table first; ≤3 representative options plus Other for manual instance ID input).
- Q2 (optional; independent of the instance so asked in the same round) Trust Condition: default empty + Other (for production, recommend restricting by namespace/SA; syntax in references).

Once the instance ID is known, **immediately run in parallel** (results feed Round 3 options; avoids dependency inversion):
- `scripts/list_oidc_trust_sources.py <region> <instance_id> <ISS> <AUD_PRIMARY> <cluster_jwks_file>` (auto-detects reuse candidates and kid staleness; last lines `REUSE_CANDIDATE=<fcp_id>|none|skipped(missing_args)` + `REUSE_KID_STALE=<fcp_id>|no|unknown(...)`. **Rule: `skipped(missing_args)` means the call omitted the issuer and performed no comparison — never treat it as "no candidates" for a create decision; rerun with full arguments first.**)
- `scripts/list_m2m_apps.py <region> <instance_id>`

### Round 3 [Ask]: Provider + JWKS Source Mode + M2M Client + Credential Name
- Q1 Federated credential provider (**strongly recommend reuse when `REUSE_CANDIDATE` is set**; option wording follows the three `REUSE_KID_STALE` states — **never present unknown as "verified fresh"**):
  - `REUSE_KID_STALE=no` (compared, kid fresh): `Reuse existing provider <fcp_id> (<name>, <mode>; issuer/aud/kid verified)` (Recommended — duplicate same-issuer providers multiply key-rotation maintenance; static ones must each be updated manually) / `Create new, name k8s-oidc-trust` + Other
  - `REUSE_KID_STALE=<fcp_id>` (compared; cluster keys rotated, stored JWKS stale): `Reuse and update JWKS first <fcp_id>` (Recommended — the skill silently runs `scripts/rotate_static_jwks.py` with the cluster JWKS already collected in Round 1; no extra user export needed; report old→new kid afterwards. For dynamic modes: stored JWKS refreshes on schedule; mention the manual refresh API for urgency) / `Create new` (note in body: aligns kid immediately but leaves a stale duplicate; suggest cleaning the old one) + Other
  - `REUSE_KID_STALE=unknown(<reason>)` (comparison impossible): `Reuse existing provider <fcp_id> (<name>, <mode>; issuer/aud verified, kid NOT checked)` (Recommended; explain the risk in the body: if the cluster rotated keys and refresh has not run, verification will fail — proceed to verification to find out, or check JwksLastObtainedTime) / `Create new` + Other
  - No candidate: `Create new provider, name k8s-oidc-trust` (Recommended) / `Bind another existing provider` (full table in body, ≤2 options) + Other — when manually binding, verify the Issuer matches the cluster and Audiences contain `AUD_PRIMARY` (ANY-match; otherwise unusable).
- Q2 **JWKS source mode** (only when Q1 = create new AND Round 1 did not already determine static; options use console terminology with API enum in parentheses; show the three-mode comparison table + probe result + recommendation rationale in the body first):
  - `ISSUER_PUBLIC=yes` → recommend **`Issuer Address Resolution (dynamic_from_issuer)`** (IDaaS fetches and periodically refreshes JWKS, following cluster key rotation, maintenance-free); `Static Fill-in (static)` (manual JWKS export; manual update after key rotation) as second choice; `JWKS URI Resolution (dynamic_from_jwks_uri)` via Other (when the user has an independent public JWKS URL; must be HTTPS; never use the possibly-broken in-cluster discovery jwks_uri — use the public `DISCOVERY_JWKS_URI` when `JWKS_URI_OK=yes`).
  - `ISSUER_PUBLIC=no` → Round 1 already determined Static Fill-in and collected JWKS; **skip this question**.
  - Mode risks must be stated (source-verified): Static Fill-in **never auto-rotates** — after a cluster SA signing key rotation, authentication fails immediately (kid miss triggers no re-fetch); update StaticJwks via `scripts/rotate_static_jwks.py`. Both dynamic modes refresh via a SchedulerX2 job and synchronously fetch at create/update time (failure = creation fails = authoritative unreachability signal).
- Q3 M2M client application:
  - `Create an application named k8s-m2m-client` (Recommended); the name can be changed through Other.
  - `Use existing application <app_id> (<name>)`; include ≤2 entries from list_m2m_apps plus Other (full table in body).
- Q4 Application federated credential name: suggest `k8s-oidc-credential` (≤64 characters) + Other.
- Audiences are **not asked**: show in the body "Audiences auto-filled: `AUD_PRIMARY` (ANY-match: the token passes if its aud intersects the configured Audiences; configuring more than needed widens the trust surface)". Handle objections conversationally.

### Round 4 [Ask]: Namespace and ServiceAccount
- Q1 Namespace / Q2 ServiceAccount: recommended values = `NS=`/`SA=` parsed from the token (verify the SA the token was issued for); the user may change them via Other to the actual business values. PodNamePrefix is optional, explained in the body (empty by default; adds a pod-name prefix check). **Production red line: never use default/default** — always state this; if the parsed values are default/default and the user keeps them, re-confirm the test purpose before creating.
- Remind the user that a fresh token will be re-issued for Phase 3 verification.

## Phase 2: Create Resources (Stop on Failure and Suggest a Fix)

**Parallelization (verified speedup)**: steps 1, 2, 4 do **not** depend on Round 4's ns/sa — start them as soon as Round 3 is answered, **in parallel with the Round 4 questions**; only step 3 waits for Round 4. 4 depends on 2's APP_ID.

```bash
# 1 OIDC federated credential provider (skip when reusing); jwks_source: static | dynamic_from_issuer | dynamic_from_jwks_uri
scripts/create_oidc_trust_source.py <region> <instance_id> <provider_name> \
    <issuer> <aud_primary> <jwks_source> [jwks_value] [nae_id=inae_public] [trust_condition]
#    jwks_value: static → JWKS file path (required); dynamic_from_jwks_uri → HTTPS URL (required); dynamic_from_issuer → omit
#    aud: use AUD_PRIMARY from parse_sa_token (ANY-match semantics; one value suffices — never copy the token's full aud list)
#    → Record FCP_ID=fcp_xxx (NetworkAccessEndpointId is REQUIRED for OIDC providers; shared endpoint default inae_public)
#    → Dynamic modes fetch synchronously at creation; OBTAIN_JWKS_ERROR means IDaaS cannot reach the issuer/jwks_uri → fall back to Static Fill-in

# 2 M2M client application (only when creating new; skip when using existing)
scripts/create_m2m_client.py <region> <instance_id> <app_name>
#    → Record APP_ID=app_xxx and confirm M2M_STATUS=enabled

# 3 Application federated credential (structured + kubernetes profile)
scripts/create_k8s_credential.py <region> <instance_id> <app_id> <fcp_id> <cred_name> <namespace> <service_account> [pod_name_prefix]
#    → Record AFC_ID=afc_xxx; the server compiles VerificationCondition:
#      And(Equals(jwt.claims.'kubernetes.io'.namespace, "<ns>"), Equals(jwt.claims.'kubernetes.io'.serviceaccount.name, "<sa>"))

# 4 PAM feature permission authorization (run by default; fully automated in two stages)
scripts/authorize_pam_scope.py <region> <instance_id> <app_id>
#    → PAM_AUTH=auto_done: use token scope urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential
#    → PAM_AUTH=module_disabled: PAM not enabled; skip if only an M2M token is needed
#    → PAM_AUTH=scope_not_found: fall back to the console (Permission Center > Feature Permission Management)
#    Reminder: STS exchange additionally requires two console steps (no OpenAPI):
#      a. Assets > Cloud Identity: onboard the cloud account + target cloud role (see the idaas-cloud-identity-setup skill)
#      b. Permission Center > Data Permission Management: authorization rule linking the application to the target cloud role
```

## Phase 3: Summary, Verification Guidance, and SDK Output

1. **Summary table**: list IDs, names, and key settings (issuer, aud, ns/sa) of the provider, application, and credential, plus the PAM authorization state.
2. Retrieve the instance endpoint: `aliyun eiam get-instance --region <r> --instance-id <iid> --cli-query 'Instance.DefaultEndpoint.Endpoint' --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/<session-id> skill-version/<version>"`
3. **Obtain the verification SA Token (freshness hard rule + proactive guidance; never wait for the user to figure it out)**: the Round 1 token is very likely expired after the interaction rounds — **re-issue before verification**; reuse the old token only if `parse_sa_token.py` shows more than 15 minutes remaining on `EXP`.
   - kubectl reachable (Phase 0 ok) → sign/fetch on the user's behalf.
   - Otherwise **run `scripts/gen_k8s_commands.py --token-only <final_ns> <final_sa> [pod]` and send its output verbatim** — commands embed the actual ns/sa (copy-paste ready), covering Method A `kubectl create token <sa> -n <ns> --duration=1h` (recommended, no pod needed) and Method B `kubectl exec -n <ns> <pod> -- cat /var/run/secrets/kubernetes.io/serviceaccount/token` (with `kubectl get pods -n <ns>` first).
   - On receipt, save to a session-scoped temp file (delete after use), run `scripts/parse_sa_token.py <token_file>` and verify `ISS`/`AUD_PRIMARY`/`NS`/`SA` against the provider and credential settings (ANY-match for aud; iss must be strictly equal); report any mismatch immediately.
4. **[Ask]** which **scope** to request: for the PAM-to-STS flow recommend the fixed value `urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential` (Phase 2 step 4 must be auto_done); for a custom M2M server use `<ResourceServerIdentifier>|<ScopeValue>`.
5. Run `scripts/test_m2m_token.py <endpoint> <client_id> <cred_name> <scope> <token_file>`; last line `TOKEN_OK=yes|no`. Report the result accurately (token summary or error).
6. **SDK onboarding output**: `scripts/gen_client_config.py <region> <endpoint> <instance_id> <app_id> <cred_name> [role_arn]` → outputs client-config.json (authnMethod=OIDC, clientDeployEnvironment=KUBERNETES, oidcTokenFilePathEnvVarName=KUBERNETES_OIDC_TOKEN_FILE) + a Java code sample + pod deployment notes; send to the user.
7. **Closing reminders**: a) STS exchange still requires the console data-permission rule (see Phase 2 4 notes); b) JWKS rotation ops by mode: **Static Fill-in** fails immediately after a cluster key rotation (kid miss, no auto re-fetch) — update via the rotation flow below; **dynamic modes** refresh automatically via the SchedulerX2 job; c) use a dedicated namespace/SA in production.

## Critical Constraints and Verified Pitfalls

1. **CreateFederatedCredentialProvider / CreateApplicationFederatedCredential require `--force --method POST` and flattened dot-notation parameters** for nested config. Passing a JSON string causes InvalidXxxConfig; dot-notation without `--force` is rejected by CLI validation; `--force` without `--method POST` causes `UnsupportedHTTPMethod`. The scripts implement this; do not change it manually.
2. **OIDC providers require `NetworkAccessEndpointId`** (optional for PKCS#7, mandatory for OIDC); shared endpoint default `inae_public`. Static mode essentials: `OidcProviderConfig.JwksSource=static` + `.Issuer` (HTTPS URL, verbatim from cluster discovery) + `.Audiences.1..5` + `.StaticJwks` (JWKS JSON string); `.TrustCondition` optional.
3. **There is no standalone "kubernetes" verification mode enum**: it is `ApplicationFederatedCredentialType=oidc` + `VerificationMode=structured` + `OidcVerificationConfig.Profile=kubernetes` + `.KubernetesConfig.Namespace/.ServiceAccountName` (required; note the field name is ServiceAccountName) + `.PodNamePrefix` (optional). In structured mode **never pass** VerificationCondition/AttributeMappings (server-compiled; verified to match source).
4. **aud verification is ANY-match; iss is strict equality** (source: jose4j `setExpectedAudience`): the token passes when its aud array intersects the configured Audiences. **Configure only one primary aud** (`AUD_PRIMARY` from parse_sa_token.py) — copying the token's full aud list (e.g. a distribution identifier value) is over-configuration that widens the trust surface. ⚠️ Two look-alike but different values: `https://kubernetes.default.svc` (short name; default tokens on ACK/EKS) vs `https://kubernetes.default.svc.cluster.local` (FQDN; default on self-managed clusters) — exact string matching, never interchangeable. Distribution combinations of `--service-account-issuer`/`--api-audiences` vary (some self-managed clusters issue dual aud; ACK issues the single short name while its issuer is an OSS URL; RRSA uses custom `sts.aliyuncs.com`) — **always derive from the actual parsed token; never infer from the issuer; never reuse another cluster's experience**.
5. **client_assertion_type is fixed**: `urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer` (standard `jwt-bearer` is **not** in the federated-authentication allowlist). client_assertion = the SA JWT **verbatim** (three dot-separated segments); no PEM wrapping or newline stripping (unlike PKCS#7).
6. The token endpoint is fixed: `https://<DefaultEndpoint>/api/v2/iauths_system/oauth2/token`. Query the endpoint using GetInstance; do not guess. Error states: RS not authorized → 400 `invalid_request "not been authorized by resource server"`; RS authorized but scope not → 400 `invalid_scope`; all set → 200.
7. **Two hidden PAM pitfalls** (inherited from the ECS skill, verified): (1) the PAM system application has the fixed ID `iap_pam` (system_init; excluded from ListApplications by default). (2) **`ListResourceServerScopes` returns 0 for iap_pam without the filter** — pass `--ResourceServerScopeType all` (PAM scopes are application_delegated/delegated). Scope-level authorization takes ress_id (passing the scope value causes InvalidParameter.ResourceServerScopeIds).
8. **JWKS rotation behavior by mode (source-verified)**:
   - Static Fill-in: never contacts the network. **After a cluster SA key rotation, authentication fails immediately** (kid miss raises InvalidJwtException with **no auto re-fetch**); update StaticJwks via UpdateFederatedCredentialProvider (use `scripts/rotate_static_jwks.py`). On Update the **Issuer cannot change** (server forces the stored value); StaticJwks/Audiences/TrustCondition/JwksUri can.
   - Dynamic modes: synchronous fetch at create/update (failure rolls back the request — the authoritative reachability signal), plus periodic refresh via the SchedulerX2 job `DYNAMIC_OBTAINING_JWKS` (**follows key rotation**); the authentication hot path reads the DB cache only; periodic fetch failures only log a warning and keep the old JWKS. A manual refresh API exists (refreshOidcProviderJwks; rejects static).
   - Selection rule: public issuer (ACK/EKS/GKE) → prefer Issuer Address Resolution; private issuer (self-managed) → Static Fill-in only, and the rotation duty must be explained to the user.
   - ⚠️ **The in-cluster discovery `jwks_uri` on ACK is a broken value** (observed `https://:6443/openid/v1/jwks`, empty host; the public OSS discovery's `…/<clusterid>/keys` is the valid one): never configure JWKS URI Resolution from the in-cluster value; use `DISCOVERY_JWKS_URI` from check_issuer_public when `JWKS_URI_OK=yes`. Issuer Address Resolution is unaffected (IDaaS fetches the public discovery). In-cluster JWKS export always uses `kubectl get --raw /openid/v1/jwks` (direct API Server path).
   - Stored-JWKS readback differs by API: Get does **not** return JWKS for dynamic providers; List **does** return DynamicJwks + JwksLastObtainedTime (kid comparison uses List). When comparison is impossible, `REUSE_KID_STALE=unknown(...)` — **unknown ≠ fresh**; never present it as verified.
9. Provider names must match `[a-z0-9_-]{1,64}`; application/credential names ≤64 characters. Use the ResourceServer identifier in scope exactly as registered; never "normalize" slash counts.
10. For curl SSL failures in proxy or sandbox environments (HTTP_STATUS=000), the test script automatically retries once with `-k` and issues a warning.
11. SA Tokens are sensitive. Delete session-scoped temporary files immediately after use. **Redaction must occur in script stdout**: test_m2m_token.py replaces access_token with its first 12 characters and total length, while printing error responses unchanged. Stdout enters the conversation transcript and telemetry as-is; agent-side presentation rules alone are insufficient. When relaying tool output, never reconstruct or paste a complete token. (JWKS contains public keys only — not sensitive.)
12. M2M is a paid feature. If it is not enabled, CreateApplication or token requests fail. Guide the user to upgrade in the console (enable M2M for Enterprise Edition, or enable extended services for Free Edition).
13. **UpdateFederatedCredentialProvider has full-overwrite semantics** (verified in production 2026-10): `--FederatedCredentialProviderName` and `--NetworkAccessEndpointId` are **required** even when unchanged (omitting them causes MissingFederatedCredentialProviderName / MissingParameter.NetworkAccessEndpoint); include all OidcProviderConfig fields. Prefer `scripts/rotate_static_jwks.py`, which reads back and refills everything automatically.

## Independent Execution and Resource Ownership

- Treat each invocation as independent. Never infer resource IDs from another invocation, test case, or an earlier session. Resolve explicitly supplied existing resources in the current instance before use.
- When the user requests a test workflow with cleanup, record every newly created resource ID and its instance, name, and ownership in a session-scoped resource inventory, including preparation resources. Use actual API-returned IDs for dependent steps.
- Generate unique names for disposable test resources using the current session ID. Normal user-requested names and existing-resource reuse remain supported; resolve name conflicts through the existing interaction rules.
- Keep creation, verification, and requested cleanup sequential within that invocation. Clean up only resources created by that invocation, after explicit confirmation; never delete a reused resource merely because it was part of the workflow.
- If creation or verification fails, report the failure and the inventory of resources already created. Obtain cleanup confirmation if not already granted for that exact inventory. Report cleanup failures and remaining IDs; never hide partial failures.
- A rejected business deletion does not authorize later cleanup. Ask separately for test teardown; without confirmation retain resources and report their IDs.

## Cleanup and Rollback (When the User Requests Deletion)

**All EIAM resources must be disabled before deletion**. Deleting an enabled resource causes `XXX.NotDisabled`.

```bash
UA="AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/<session-id> skill-version/<version>"
# Application federated credential
aliyun eiam disable-application-federated-credential --region <r> --instance-id <iid> --application-id <app_id> --application-federated-credential-id <afc_id> --user-agent "$UA"
aliyun eiam delete-application-federated-credential  --region <r> --instance-id <iid> --application-id <app_id> --application-federated-credential-id <afc_id> --user-agent "$UA"
# Federated credential provider
aliyun eiam disable-federated-credential-provider --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"
aliyun eiam delete-federated-credential-provider  --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"
# Application
aliyun eiam disable-application --region <r> --instance-id <iid> --application-id <app_id> --user-agent "$UA"
aliyun eiam delete-application  --region <r> --instance-id <iid> --application-id <app_id> --user-agent "$UA"
```

Delete in this order: application federated credential → provider → application. List the resources to be deleted and obtain user confirmation before deletion.

**Static Fill-in key rotation** (cluster rotated its SA signing key; authentication reports kid mismatch / `REUSE_KID_STALE` hit): this is an internal maintenance action — **run silently, never show internal script commands to the user**. Use the cluster JWKS already collected in Round 1 (`/tmp/idaas-k8s-jwks-<session_id>.json`):

```bash
scripts/rotate_static_jwks.py <region> <instance_id> <fcp_id> <cluster_jwks_file>
#    → reads back and refills Name/NAE/Issuer/Audiences, replaces StaticJwks only
#    → last lines ROTATED=yes + KIDS_OLD/KIDS_NEW (verified 2026-10)
```
Only ask the user to re-run `kubectl get --raw /openid/v1/jwks` when the file is missing or possibly outdated. Dynamic modes need no manual rotation (periodic refresh; manual refresh API for urgency).

## Command Reference

| Command | Purpose |
|---------|---------|
| `scripts/probe_k8s.py [jwks_out]` | Probe kubectl/cluster reachability; collect issuer + JWKS when reachable |
| `scripts/gen_k8s_commands.py [ns] [sa] [pod]` | Generate zero-dependency cluster-side command block (paste-back mode) |
| `scripts/gen_k8s_commands.py --token-only <ns> <sa> [pod]` | Phase 3 fresh-token guidance with actual ns/sa embedded |
| `scripts/parse_sa_token.py <token_file>` | Parse SA Token → ISS/AUD_PRIMARY/AUD_ALL/NS/SA/EXP (auto-fill source) |
| `scripts/check_issuer_public.py <issuer> [jwks_out]` | Probe issuer public reachability; save fetched JWKS; JWKS_URI_OK check |
| `scripts/list_instances.py <region>` | List IDaaS EIAM instances |
| `scripts/list_oidc_trust_sources.py <region> <iid> [issuer] [aud] [jwks_file]` | List OIDC providers; reuse-candidate + kid-staleness detection |
| `scripts/list_m2m_apps.py <region> <iid>` | List existing M2M applications |
| `scripts/create_oidc_trust_source.py <region> <iid> <name> <issuer> <auds> <jwks_source> [jwks_value] [nae] [cond]` | Create OIDC provider (three JWKS source modes) |
| `scripts/create_m2m_client.py <region> <iid> <app_name>` | Create M2M client application |
| `scripts/create_k8s_credential.py <region> <iid> <app_id> <fcp_id> <name> <ns> <sa> [pod_prefix]` | Create kubernetes-mode application federated credential |
| `scripts/authorize_pam_scope.py <region> <iid> <client_app_id>` | Auto-authorize PAM feature permissions |
| `scripts/rotate_static_jwks.py <region> <iid> <fcp_id> <new_jwks_file>` | Rotate Static Fill-in JWKS (full-overwrite Update, auto-refilled) |
| `scripts/test_m2m_token.py <endpoint> <client_id> <cred_name> <scope> <token_file>` | Test M2M token exchange (stdout-redacted) |
| `scripts/gen_client_config.py <region> <endpoint> <iid> <app_id> <cred_name> [role_arn]` | Produce SDK client-config.json + Java sample |

*All script paths are relative to the workspace root `scripts/` directory.*

## References

- `references/api-and-pitfalls.md`: Complete API parameters (with source-code DTO findings), token request/response specs, DSL expression syntax, error mappings, JWKS mode runtime behavior, and verified test records.
- `references/ram-policies.md`: RAM permissions required by this skill (actions mapped to steps), ready-to-use policy JSON, and prerequisites unrelated to permissions. Use this reference to troubleshoot Forbidden.RAM.
- `references/manifest.json`: Skill name and version (read gate for the user-agent string).
- Sister skills: `idaas-ecs-m2m-federated-credential` (ECS PKCS#7 scenarios), `idaas-cloud-identity-setup` (cloud account/role onboarding, STS prerequisite).
