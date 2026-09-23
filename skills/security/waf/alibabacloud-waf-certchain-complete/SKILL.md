---
name: alibabacloud-waf-certchain-complete
description: Use when Alibaba Cloud WAF reports an incomplete SSL certificate chain or missing intermediate certificate, when a WAF certificate needs a cert chain fix, or when a WAF certificate PEM must be checked and repaired before manual upload.
---

# WAF Certificate Chain Check and Repair

Diagnose WAF certificate-chain completeness, repair a supplied PEM bundle, and guide manual upload. The Skill does not discover domains or probe remote TLS endpoints.

## Scope

Supported:

- Query a known WAF 3.0 instance with `DescribeCerts` and inspect `IsChainCompleted`
- Check a supplied local PEM file
- Fetch or manually locate missing intermediate certificates
- Build and verify a complete chain
- Guide manual upload and re-check WAF certificate status

Out of scope:

- Domain listing, certificate-to-domain binding discovery, or domain configuration queries
- Remote TLS probing by domain, CNAME, or IP
- Automatic certificate upload or deployment APIs

## Prerequisites

For local PEM-only work:

```bash
openssl version
python3 --version
```

The bundled `scripts/fix_certchain.py` requires Python 3.8+ and OpenSSL. It has no external Python dependencies.

For WAF certificate-list queries, also require Aliyun CLI 3.3.3+ and the current plugin:

```bash
aliyun version
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun configure list
```

Never read, print, or request literal AK/SK values. If no valid CLI profile exists, stop and tell the user, in a plain declarative statement, to configure credentials outside the conversation — do not ask a question, wait, or block.

## Permissions

Only read permission is required:

| Action | Purpose |
|---|---|
| `yundun-waf:DescribeCerts` | List WAF 3.0 certificates and read `IsChainCompleted` |

Do not request certificate write permissions. On `Forbidden.RAM`, `NoPermission`, or `not authorized`, terminate the task immediately: stop the whole workflow, do not continue, do not retry, and do not perform any workaround or act on the user's behalf. Only state which read-only Action (`yundun-waf:DescribeCerts`) is missing, then end the turn. This is a hard stop, not a hand-off for manual continuation.

## Observability

Generate one 32-character lowercase hexadecimal session ID:

```python
import secrets; session_id = secrets.token_hex(16)
```

Resolve `skill_version` at runtime from the `version` field of `references/manifest.json`; never hardcode it. Before the first `aliyun` call, verify that `references/manifest.json` exists and that its `version` is a non-empty string. If the file is missing or the `version` is empty, stop and state in one declarative sentence that the Skill version could not be resolved from `references/manifest.json`, so no cloud call is issued — do not guess a version, do not ask a question, do not wait.

Once resolved, append this flag to every `aliyun` command (`{skill-version}` is the value read from `references/manifest.json`):

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-certchain-complete/{session-id} skill-version/{skill-version}"
```

## Input Routing

| Input | Required path |
|---|---|
| Local PEM only | Skip all cloud setup and run the local checker |
| WAF `InstanceId` only | Run `DescribeCerts`; report incomplete certificate identifiers and request the affected PEM before repair |
| Both `InstanceId` and PEM | Query WAF status, then use the supplied PEM for repair |
| Neither | State, in one declarative sentence, that you need a WAF 3.0 `InstanceId` or a local PEM path, explicitly noting you will not guess a target, list domains/instances, or fabricate certificate data until the user supplies it, then end the turn on that statement. Do not phrase it as a question, do not use a trailing question mark, do not ask the user to reply, and do not pause, poll, wait, or call any interactive/blocking tool. Never proceed on assumed or invented values. |

Requesting missing input (or a target selection) is required behavior and is NOT the same as blocking: say in one declarative sentence exactly what you need, then stop the turn. Do NOT end with a question mark, do NOT explicitly ask the user to reply, and do NOT pause, poll, wait, or call any interactive/blocking tool — those are what turn a legitimate input request into a blocking stall. Fabricating data to avoid requesting the input is equally forbidden.

A supplied file path is authoritative. Never replace it with a certificate obtained from another endpoint.

## Workflow

### 1. Check WAF certificate status

When an instance ID is provided:

```bash
aliyun waf-openapi describe-certs \
  --instance-id <instance_id> \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-size 100 --pager \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-certchain-complete/{session-id} skill-version/{skill-version}"
```

Treat `IsChainCompleted: false` as the authoritative WAF-side incomplete-chain signal. Record `CertIdentifier`, `CertName`, `CommonName`, and `IsChainCompleted`. When two or more certificates are incomplete, list EVERY incomplete `CertIdentifier` to the user, then state in one declarative sentence that repairing requires the user to name the single target certificate and supply its matching local PEM path, and stop the turn — do not pick a target yourself. Listing every incomplete certificate and naming the required inputs is required behavior (distinct from blocking); phrase it as a statement, NOT a question, with no trailing question mark, and do not pause, poll, wait for a reply, or call any interactive/blocking tool inside the same turn. Retry a failed `DescribeCerts` call only under the Error Recovery policy below. A later post-upload check requires the user confirmation in Step 6; report completeness only from the target certificate's actual `IsChainCompleted` value in a successful response.

### 2. Check a local PEM

```bash
python3 scripts/fix_certchain.py --file cert.pem
python3 scripts/fix_certchain.py --file cert.pem --json
```

The checker reports certificate count, `COMPLETE`/`INCOMPLETE`, chain subjects and issuers, and missing intermediate gaps.

Exit codes:

- `0`: complete
- `1`: incomplete and no repair requested
- `2`: still incomplete after repair attempt

### 3. Repair the chain

```bash
python3 scripts/fix_certchain.py \
  --file cert.pem \
  --fix \
  --output complete_chain.pem
```

The script fetches only the certificate-provided AIA CA Issuers URL after validating that it resolves to a public HTTP(S) endpoint. It rejects redirects and oversized responses. If AIA retrieval fails, use the manual official-CA fallback below. The script writes the server certificate first, followed by intermediate certificates, and never overwrites the input file.

If automatic retrieval fails:

```bash
openssl x509 -in cert.pem -noout -issuer
openssl x509 -in cert.pem -noout -ext authorityInfoAccess
cat server_cert.pem intermediate.pem > complete_chain.pem
```

Use the issuer's official CA repository. Do not insert blank lines between certificate blocks. Root certificates are optional and normally should not be included.

### 4. Verify before upload

```bash
python3 scripts/fix_certchain.py --file complete_chain.pem
```

Require `Chain status: COMPLETE` and exit code `0`.

For an independent check, split the server certificate and intermediate bundle, then run:

```bash
openssl verify -untrusted intermediate_bundle.pem server_cert.pem
```

Do not use `openssl verify -CAfile complete_chain.pem complete_chain.pem`; it can trust the leaf as a CA and give a misleading result.

### 5. Guide manual upload

Explain that the user needs:

- Full `complete_chain.pem` content
- The original matching private key
- The WAF console certificate upload/replace action, or Digital Certificate Management Service → Deploy → WAF

Do not call certificate create or deployment APIs.

End the turn with a single declarative handoff sentence, stating that the complete-chain file and the manual upload steps have been provided, that the upload must be completed manually in the WAF console, and that the WAF-side certificate-chain status will be re-checked in a later turn after the user confirms the upload — this turn ends here. Frame it as a statement of what remains on the user's side, NOT a live request: do not end with a question, do not use a trailing question mark, do not pause, poll, block, or open a follow-up turn inside this response. Step 6 runs only in a later turn after the user actually confirms.

If a specific task explicitly asks you to include the confirmation wording, reproduce the template below verbatim (localized to the user's language) as declarative content within your answer, but still close the turn as a completed handoff in the same single reply — quoting it does not make you wait for it:

```text
上传完成后请回复“已上传”，我会继续验证证书链状态。
```

### 6. Verify after upload

After user confirmation:

1. Re-check the available complete-chain PEM locally
2. Query `DescribeCerts` again
3. Confirm the target certificate reports `IsChainCompleted: true`
4. Clearly distinguish local file verification from WAF-side deployment verification

## Error Recovery

Choose the recovery from the actual error returned by `DescribeCerts`. Permission and parameter errors are not transient; repeating the unchanged request cannot fix them. Throttling and server errors permit at most one retry with unchanged parameters. The retry budget is one additional call for the entire query, not one retry per error type.

| Observed result | Required behavior |
|---|---|
| `Forbidden.RAM`, `NoPermission`, or `not authorized` | Terminate immediately after the failed call. Do not retry, change credentials, request authorization, or perform a workaround. State that the query could not be completed because read-only `yundun-waf:DescribeCerts` permission is missing, then end the turn. |
| `InvalidParameter` | Terminate immediately after the failed call. Do not retry, consult `--help`, or modify, complete, or substitute the supplied instance or region. State that the query could not be completed because of the reported parameter error, then end the turn. |
| `Throttling.User` / HTTP 429 | Back off and re-issue the same call once. If the retry succeeds, continue using its actual response. If it fails, stop and report the actual final error and that the query could not be completed. |
| `InternalError` / HTTP 5xx | Re-issue the same call once. If the retry succeeds, continue using its actual response. If it fails, stop and report the actual final error and that the query could not be completed. Include a request ID only if one was returned. |
| AIA download failure | Use the issuer's official CA repository and guide manual concatenation. |
| No certificate in PEM | Stop and state that a valid PEM certificate file is required, then end the turn. |

A failed retry ends the query even if its error differs from the first error. Never issue a third call. A successful response is not a failed query: report its actual certificate data instead of repeating a failure template. Without a successful certificate-list response, certificate-chain status is unknown; do not report it as complete or incomplete.

For a terminal cloud error, give a factual declarative conclusion with the observed cause and unresolved status, then stop the whole workflow. Do not continue into local repair, suggest contacting support or retrying later, request permission changes, ask a question, or wait for input. Keep command outcomes, exit codes, and any returned request IDs distinguishable from the final user-facing conclusion; never fabricate a successful API response.

WAF OpenAPI limit is 5 calls/second per UID. Insert `sleep 0.3` between sequential calls. For a throttling retry, honor a returned retry delay when available; otherwise wait at least one second before the single retry.

## Final Response Contract

State, in order:

1. WAF finding: target `CertIdentifier` and `IsChainCompleted`, when queried
2. Local finding: `INCOMPLETE` or `COMPLETE`; for incomplete chains, name the missing issuer
3. Repair result: output path and post-repair status, or exact blocker
4. User action: manual upload or permission/error recovery
5. Verification status: local-file status versus WAF-side status

## Cleanup

The Skill creates only local output files. Do not delete automatically; tell the user where they are so they can retain or move them.

## References

- [CLI installation](references/cli-installation-guide.md)
- [Read-only RAM policy](references/ram-policies.md)
- [Command reference](references/related-commands.md)
- [Certificate-chain basics](references/certificate-chain-basics.md)
