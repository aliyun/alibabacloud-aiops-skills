# Result Interpretation Guide

This guide helps you understand the results returned by AISC Skill file security checks and provides remediation advice for each risk category.

## Result Structure Overview

Each sub-task corresponds to a scanned file. Its `risk_info` array contains all risk findings for that file. Risks are divided into four categories:

---

## 1. Virus Detection

Detects whether the file contains malicious code, backdoors, trojans, etc.

| Field | Description |
|-------|-------------|
| `type` | Virus type, e.g., `Backdoor`, `Trojan`, `Malware`, `Suspicious` |
| `score` | Risk score out of 100. Higher scores indicate greater likelihood of malicious content |
| `ext` | Extended information (JSON string), reserved field |

### Remediation Advice

- **score >= 80**: High risk. Immediately quarantine the file; do not use in production
- **score 50-79**: Medium risk. Manual code review recommended to confirm whether it is a false positive
- **score < 50**: Low risk. Usually heuristic detection; consider combining with other detection dimensions

---

## 2. Guardrail Detection

Detects whether the Skill contains prompt injection attacks, jailbreak attempts, or other security risks.

| Field | Description |
|-------|-------------|
| `suggestion` | Overall disposition: `block` or `allow` |
| `detail[].level` | Risk level: `high`, `medium`, `low`, `none` |
| `detail[].type` | Risk type, e.g., `promptAttack` |
| `detail[].suggestion` | Per-item disposition: `block` or `allow` |
| `detail[].result[].confidence` | Confidence score, 0-100. Higher values indicate greater certainty |
| `detail[].result[].description` | Result description, e.g., `Suspicious attacks.` |
| `detail[].result[].label` | Label, e.g., `attack` |
| `detail[].result[].level` | Per-item risk level |

### Remediation Advice

- **level=high + suggestion=block**: Definite attack behavior detected. Must be fixed before use
- **level=medium**: Potentially suspicious content. Manual review of the Skill's prompts and instructions recommended
- **level=low/none**: Usually safe content or very low-risk false positives
- **promptAttack type**: Check whether the Skill file contains instructions attempting to manipulate Agent behavior; remove or rewrite the relevant prompts

---

## 3. Sensitive Data Detection

Detects whether the file hardcodes credentials such as AccessKey, SecretKey, Token, or passwords.

| Field | Description |
|-------|-------------|
| `detail[].desc` | Sensitive data type description, e.g., `aliyun_ak_24` (Alibaba Cloud AccessKey), `password`, `token` |
| `detail[].result` | List of detected sensitive values (partially masked), e.g., `LTAIvdi11f0b****` |

### Remediation Advice

- **Immediately remove** hardcoded credentials; use the default credential chain or `CredentialClient` instead
- Use `alibabacloud_credentials` `CredentialClient()` for secure authentication
- If credentials have been leaked, **rotate** the affected keys immediately
- Add files containing sensitive data to `.gitignore`
- Common fixes:
  - BAD: `access_key_id = "LTAI..."` -> GOOD: `CredentialClient()`
  - BAD: `password = "xxx"` -> GOOD: Read from environment or key management service

---

## 4. Configuration Detection

Detects security risks in Skill configuration files (e.g., `SKILL.md`, `settings.json`).

| Field | Description |
|-------|-------------|
| `detail[].item_name` | Check item name, e.g., `Dangerous Tools Without Confirmation` |
| `detail[].description` | Risk description |
| `detail[].content` | Matched configuration content, e.g., `allowed-tools: Bash(agent-browser:*)` |
| `detail[].line` | Line number of the matched content |

### Common Configuration Risk Items

| ItemName | Meaning | Fix |
|----------|---------|-----|
| `Dangerous Tools Without Confirmation` | Allows executing dangerous tools without user confirmation | Add user confirmation requirements; restrict `allowed-tools` scope |
| `Unrestricted Shell Access` | Unrestricted shell access permissions | Narrow the allowlist scope; add confirmation steps |
| `Missing Permission Guards` | Missing permission guards | Add necessary permission check logic |

### Remediation Advice

- Use the `line` field to locate the specific code line
- Review whether the `content` configuration is reasonable
- For `allowed-tools` configurations, apply the principle of least privilege
- Ensure sensitive operations (e.g., Bash execution, file writes) require explicit user confirmation

---

## Overall Risk Assessment

After scanning completes, handle risks in the following priority order:

1. **Virus (score >= 80)**: Block immediately; do not use the file
2. **Sensitive (credential leakage)**: Remove credentials and rotate keys immediately
3. **Guardrail (high/block)**: Fix attack-related prompts and re-scan
4. **Config (high-risk configuration)**: Correct configuration items and add security guardrails
5. **Other medium/low risks**: Handle at discretion; manual review recommended
