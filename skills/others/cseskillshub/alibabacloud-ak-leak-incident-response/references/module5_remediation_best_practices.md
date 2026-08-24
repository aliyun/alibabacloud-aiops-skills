# Module 5: Remediation Best Practices

> Based on Alibaba Cloud official documentation. Each recommendation links to its source for customer-facing justification.

## Purpose

Provide authoritative, specific remediation recommendations for AK leakage incidents. These are referenced by Step 6 (Timeline Report) to generate the "VI. Remediation Recommendations" section with concrete, actionable steps backed by official Alibaba Cloud best practices.

## Remediation Priority Framework

### P0 — Immediate (Within 30 minutes)

#### P0-1: Disable and Delete the Leaked AK

**Action**: RAM Console → AccessKey Management → Disable → Confirm no service disruption → Delete.

**Manual only — this skill performs no write operations.** The skill is read-only: it detects and reports the leak but never disables, modifies, or deletes the AK. When a leak is confirmed, `ak_leak_investigation.py` prints a prominent URGENT banner instructing the operator to: (1) disable the leaked AK immediately, (2) replace it with a new AccessKey in all applications, (3) verify no service impact, then (4) delete the disabled AK. Execute these via the RAM Console / CLI yourself; never delete before replacing.

**Why**: A leaked AK with `Active` status grants full programmatic access to all authorized resources. Every second it remains active, the attacker can create new persistence mechanisms (sub-users, new AKs, CloudSSO configurations).

**Official guidance**: "Disable unused AccessKeys, observe for a period to confirm no service impact, then delete. If you still need AccessKey access, rotate the old AccessKey pair."

**Source**: https://www.alibabacloud.com/help/en/ram/user-guide/solution-to-accesskey-leakage

#### P0-2: Delete Attacker-Created Sub-Users and Their AKs

**Action**: RAM Console → Users → locate users created during incident window → Detach all policies → Delete AKs → Delete user.

**Why**: Sub-users with `AdministratorAccess` represent persistent backdoors. Even after the original leaked AK is disabled, these sub-users can continue accessing the account via console login or their own AKs.

**Verification**: Confirm deletion via `ListUsers` API and verify no residual `LoginProfile` or `AccessKey` exists.

#### P0-3: Revoke CloudSSO Access Configurations

**Action**: CloudSSO Console → Access Configurations → Delete attacker-created configurations (typically named "root" with 12h SessionDuration) → Revoke associated Access Assignments.

**Why**: CloudSSO persistence survives AK deletion and RAM user cleanup. An `AccessConfiguration` with `AdministratorAccess` + `CreateAccessAssignment` provides cross-account access that is invisible to standard RAM auditing.

#### P0-4: Terminate Unauthorized Resources

**Action**: ECS Console → Instances → filter by creation time within incident window → Release (force) → also release associated EIPs, security groups, and disk snapshots.

**Why**: Attacker-created ECS instances may be used for cryptocurrency mining, C2 relay, DDoS, or lateral movement. Each minute of operation incurs billing and increases liability.

### P1 — Urgent (Within 2 hours)

#### P1-1: Rotate All Remaining AKs on the Account

**Action**: For each active AK → Create new AK → Update application configurations → Verify service continuity → Disable old AK → Delete after 24h observation.

**Official guidance**: "Regularly rotate RAM user AccessKey pairs (recommended every 90 days). If a leak occurs, all existing AKs should be immediately rotated."

**Procedure** (manual rotation):
1. Create a new AK for the same RAM user.
2. Update all application/CI/CD configurations to use the new AK.
3. Disable (not delete) the old AK.
4. Monitor for 24h — if no errors, delete the old AK.

**Automated rotation** (recommended for long-term):
- Use **KMS Secrets Manager** for automatic AK rotation with configurable intervals.
- Source: https://www.alibabacloud.com/help/en/ram/regularly-rotate-accesskey-pairs-of-ram-users

#### P1-2: Restore DNS Records

**Action**: Alidns Console → Domain → Records → compare current records against known-good baseline → restore any modified/deleted A/CNAME/MX records.

**Why**: DNS hijacking (`DeleteDomainRecord` / `AddDomainRecord`) can redirect traffic to attacker-controlled servers for phishing, credential theft, or data exfiltration.

#### P1-3: Re-enable Notification Subscriptions

**Action**: Message Center → Notification Settings → verify all security alert subscriptions are active.

**Why**: Sophisticated attackers use `UpdateUserSubscription` and `DelMessage` to disable security alerts and destroy notification evidence.

#### P1-4: Review and Revoke Excessive RAM Permissions

**Action**: RAM Console → Policies → identify overly-broad policies (especially `AdministratorAccess`, `AliyunRAMFullAccess`) → replace with least-privilege custom policies.

**Official guidance**: "When authorizing RAM users, select the minimum permissions required for their work."

**Source**: https://www.alibabacloud.com/help/en/ram/product-overview/best-practices-for-identity-and-access-control

### P2 — Important (Within 24 hours)

#### P2-1: Investigate AK Leakage Source

**Common sources** (prioritized):
1. Code repositories (GitHub, Gitee, GitLab) — hardcoded in source files, `.env`, config YAML/JSON.
2. CI/CD pipeline configurations — environment variables visible in build logs.
3. Client-side code — JavaScript bundles, mobile app APKs.
4. Third-party platforms — SaaS integrations with over-permissioned credentials.
5. Compromised developer machine — malware exfiltrating credential files.

**Action**: Use `git log --all -p | grep "LTAI"` to search code history. Check GitHub exposure via Security Center's AK leak detection feature.

**Source**: https://www.alibabacloud.com/help/en/security-center/user-guide/detection-of-accesskey-pair-leaks

#### P2-2: Enable MFA for All RAM Users with Console Access

**Action**: RAM Console → Users → for each user with `LoginProfile` → bind virtual MFA device (TOTP) or U2F hardware key.

**Official guidance**: "Enable multi-factor authentication (MFA) for the Alibaba Cloud account and RAM users to add two layers of protection for logins."

**Enforcement**: RAM Console → Security Settings → enable "MFA is required for RAM user logins" policy.

**Source**: https://www.alibabacloud.com/help/en/ram/enable-mfa-for-alibaba-cloud-account

#### P2-3: Eliminate Root Account AK Usage

**Action**: If the leaked AK belongs to the root (main) account → migrate all applications to RAM user AKs or STS → disable and delete root AK.

**Official guidance**: "The Alibaba Cloud account AccessKey is equivalent to full administrative access. Once leaked, the damage cannot be limited through permissions. Create RAM users as replacements."

**Source**: https://www.alibabacloud.com/help/en/ram/avoid-using-the-accesskey-pair-of-an-alibaba-cloud-account

#### P2-4: Separate Human and Program Access

**Action**: Ensure no single RAM user has both console login AND active AK.

**Official guidance**: "Application users: enable only OpenAPI access. Individual users: enable only console access."

**Source**: https://www.alibabacloud.com/help/en/ram/separate-ram-users-for-individuals-from-those-for-programs

#### P2-5: Strengthen Password Policy

**Action**: RAM Console → Security Settings → Password Policy:
- Minimum length: 12+ characters
- Required character types: 3+ (uppercase, lowercase, digit, symbol)
- Expiration: ≤ 90 days
- Max login retries: 5
- Prevent password reuse: last 5 passwords

**Source**: https://www.alibabacloud.com/help/en/ram/configure-strengthened-password-rules

### P3 — Long-term Hardening (Within 1 week)

#### P3-1: Migrate to Credential-Free Architecture

**Priority order** (most secure → least):
1. **ECS Instance RAM Role** — applications on ECS/ECI fetch STS automatically from metadata service.
2. **RRSA (ACK)** — Kubernetes pods use OIDC-bound service accounts to assume roles via `AssumeRoleWithOIDC`.
3. **FC Function Role** — serverless functions auto-assume attached role.
4. **KMS Secrets Manager** — automated credential rotation with application SDK integration.
5. **STS temporary credentials** — short-lived tokens via `AssumeRole`, valid 15min–12h.
6. **Environment variables** (last resort) — `ALIBABA_CLOUD_ACCESS_KEY_ID` / `SECRET` in environment (never in code).

**Source**: https://www.alibabacloud.com/help/en/ram/use-cases/best-practices-for-programmatic-access-to-alibaba-cloud

#### P3-2: Enforce Single Active AK per RAM User

**Official guidance**: "RAM users with two AccessKeys face rotation difficulties and uncontrollable permission scope. Ensure each RAM user has only one active AccessKey."

**Source**: https://www.alibabacloud.com/help/en/ram/do-not-enable-two-accesskey-pairs-for-a-ram-user

#### P3-3: Clean Up Idle AKs and Users

**Idle AK criteria**: Not used in the last 90 days. **Procedure**: Disable → observe 90 days → delete if no impact.

**Source**: https://www.alibabacloud.com/help/en/ram/delete-idle-accesskey-pairs-of-ram-users

#### P3-4: Implement Real-Time Monitoring

**Action**:
1. **ActionTrail** — enable trail delivery to SLS (Log Service) for real-time indexing.
2. **CloudMonitor** — create event-based alarms for: RAM user creation, access key creation, policy attachment to users, DNS record deletion, ECS instance launches.
3. **Security Center** — verify AK leak detection is enabled.

#### P3-5: Adopt SSO / No-Password Login

**Action**: Integrate corporate IdP (SAML 2.0 / OIDC) with Alibaba Cloud RAM SSO → disable password login for all human users.

**Source**: https://www.alibabacloud.com/help/en/ram/product-overview/best-practices-for-identity-and-access-control

#### P3-6: Enable RAM Cloud Governance

**Action**: RAM Console → Cloud Governance → enable all 14+ detection items covering:
- AccessKey management (idle keys, dual active keys, root AK usage)
- User management (idle users, unseparated human/program users)
- Security settings (MFA not enabled, weak password policy)
- Permission settings (overly-broad policies)

**Source**: https://www.alibabacloud.com/help/en/ram/overview-of-cloud-governance-for-ram

## Quick Reference: Remediation by Attack Type

| Attack Type | P0 Actions | P1 Actions | P2+ Actions |
|-------------|-----------|-----------|-------------|
| Sub-user creation + privilege escalation | Delete sub-users + their AKs + policies | Rotate all account AKs | Enable MFA, audit all RAM policies |
| ECS instance creation (mining/C2) | Release instances + EIPs + security groups | Check billing anomalies | Instance RAM Role migration |
| DNS hijacking | Restore records, check cert issuance | Monitor DNS for 72h | DNSSEC, domain lock |
| SMS abuse | Disable AK immediately | Audit SMS quotas | Separate SMS user with IP whitelist |
| CloudSSO persistence | Delete AccessConfigurations + Assignments | Revoke all Access, audit SCIM | Re-architecture SSO trust |
| Notification suppression | Re-enable subscriptions | Review alert history gaps | CloudMonitor + SLS alerts |
| Data exfiltration (RDS/DMS) | Revoke DMS access, audit SQL logs | Change DB passwords | Network isolation, audit policies |

## Customer Communication Template

When communicating remediation advice to the customer in the incident report, use the following structure for Section VI (Remediation Recommendations):

```
VI. Remediation Recommendations (Priority-Ordered)

[P0 — Immediate (Within 30 Minutes)]
1. Disable and delete the leaked AK <AK-ID>. Path: RAM Console → Users → AccessKey Management → Disable → Confirm no impact → Delete.
2. Delete attacker-created sub-accounts <usernames> and all their AKs and attached policies.
3. [If CloudSSO] Delete attacker-created AccessConfigurations and revoke associated Access Assignments.
4. [If ECS] Terminate attacker-created <N> ECS instances and associated EIPs/security groups.

[P1 — Urgent (Within 2 Hours)]
5. Rotate all remaining AccessKeys on this account (manual rotation or KMS Secrets Manager).
6. [If DNS] Restore deleted/modified DNS records, compare current records against known-good baseline.
7. [If notification tampering] Re-enable disabled security alert subscriptions.
8. Tighten RAM permissions to least-privilege principle, remove unnecessary AdministratorAccess.

[P2 — Important Hardening (Within 24 Hours)]
9. Investigate AK leakage source (code repos, CI/CD configs, third-party platforms) and remediate.
10. Enable mandatory MFA policy for all RAM users.
11. If leaked AK belongs to root account, migrate to RAM user AK and delete root AK.
12. Implement human/machine separation: console users and API users managed separately.
13. Strengthen password policy (12+ chars, 3 char types, 90-day expiration).

[P3 — Long-term Governance (Within 1 Week)]
14. Migrate to credential-free architecture (ECS Instance Role / RRSA / FC Function Role / KMS Secrets Manager).
15. Clean up idle AKs (unused 90 days → disable → observe → delete) and idle RAM users.
16. Ensure each RAM user retains only 1 active AK.
17. Enable ActionTrail real-time delivery to SLS + CloudMonitor alerts (Ram/DNS/CloudSSO critical operations).
18. Enable RAM Cloud Governance with all 14+ detection items for continuous compliance monitoring.
19. Adopt enterprise SSO integration, eliminate password-based logins.

Reference Documents:
- RAM Identity & Access Best Practices: https://www.alibabacloud.com/help/en/ram/product-overview/best-practices-for-identity-and-access-control
- AK Leakage Remediation: https://www.alibabacloud.com/help/en/ram/user-guide/solution-to-accesskey-leakage
- AK Leak Detection: https://www.alibabacloud.com/help/en/security-center/user-guide/detection-of-accesskey-pair-leaks
- RAM Cloud Governance: https://www.alibabacloud.com/help/en/ram/overview-of-cloud-governance-for-ram
- Programmatic Access Best Practices: https://www.alibabacloud.com/help/en/ram/use-cases/best-practices-for-programmatic-access-to-alibaba-cloud
```

## Source Index

| Topic | Official URL |
|-------|-------------|
| RAM Identity & Access Best Practices | https://www.alibabacloud.com/help/en/ram/product-overview/best-practices-for-identity-and-access-control |
| AK Leakage Remediation Solution | https://www.alibabacloud.com/help/en/ram/user-guide/solution-to-accesskey-leakage |
| Security Center AK Leak Detection | https://www.alibabacloud.com/help/en/security-center/user-guide/detection-of-accesskey-pair-leaks |
| Programmatic Access Best Practices | https://www.alibabacloud.com/help/en/ram/use-cases/best-practices-for-programmatic-access-to-alibaba-cloud |
| Avoid Root Account AK | https://www.alibabacloud.com/help/en/ram/avoid-using-the-accesskey-pair-of-an-alibaba-cloud-account |
| Regular AK Rotation | https://www.alibabacloud.com/help/en/ram/regularly-rotate-accesskey-pairs-of-ram-users |
| Delete Idle AKs | https://www.alibabacloud.com/help/en/ram/delete-idle-accesskey-pairs-of-ram-users |
| No Dual Active AKs | https://www.alibabacloud.com/help/en/ram/do-not-enable-two-accesskey-pairs-for-a-ram-user |
| Enable MFA | https://www.alibabacloud.com/help/en/ram/enable-mfa-for-alibaba-cloud-account |
| Separate Human/Program Users | https://www.alibabacloud.com/help/en/ram/separate-ram-users-for-individuals-from-those-for-programs |
| Password Policy | https://www.alibabacloud.com/help/en/ram/configure-strengthened-password-rules |
| RAM Cloud Governance | https://www.alibabacloud.com/help/en/ram/overview-of-cloud-governance-for-ram |
