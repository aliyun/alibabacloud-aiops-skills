# Remediation, Hardening, and Product Recommendation Guide

Security remediation and hardening guidance for the OpenClaw environment.

> Disclaimer: All operations performed on target machines described in this guide are executed via Cloud Assistant.
>
> Before executing any command via Cloud Assistant, the following principles must be followed:
> 1. Clearly inform the user of the full command content to be executed.
> 2. Require the user to explicitly confirm (reply with agreement) before executing the command.
> 3. If the user has not confirmed or the command is high-risk, execution is prohibited.
> Notes:
> 1. The region-id for Cloud Assistant commands differs from that of Security Center and must match the target machine instance location.
> 2. Be aware of command escaping issues, e.g., `$()` must be written as `\$()`.

---

## 1. Isolate Malicious Skills

When a malicious or suspicious Skill is detected in OpenClaw:

### Investigation Steps

1. **Confirm alert details**: View the alert reason via `check_openclaw_alerts.py`
2. **Locate the Skill file**:
   ```bash
   # View installed Skills in OpenClaw via Cloud Assistant
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "ls -la ~/.openclaw/skills/ && openclaw skills list"
   ```

### Isolation Steps

1. **Isolate the malicious Skill (must be confirmed by the user before execution)**:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "mv ~/.openclaw/skills/<skill-name> /tmp/<skill-name>"
   ```

### Preventive Measures

- Only install Skills from trusted sources
- Regularly audit the list of installed Skills
- Enable Skill sandbox isolation (if available)

---

## 2. Fix Gateway Public Network Exposure

### Investigation Steps

1. Confirm the Gateway public network exposure risk via `check_openclaw_baseline.py` or alert information
2. Check the Gateway configuration:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "cat ~/.openclaw/openclaw.json | python3 -m json.tool"
   ```

### Remediation Steps

1. **Disable Gateway public network listening and restart Gateway via Cloud Assistant**:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "openclaw config set gateway.bind loopback"
   ```

   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "XDG_RUNTIME_DIR=/run/user/\$(id -u) DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u)/bus systemctl --user restart openclaw-gateway.service"
   ```

### Public Network Restriction Recommendations

- Bind the Gateway to the loopback address only (`loopback`)
- Use security groups to allow access only from authorized management IP ranges
- Access the management interface via VPN or bastion host
- Regularly verify listening addresses and exposed ports

---

## 3. Upgrade OpenClaw Version

### Check Current Version

```bash
python -m scripts.run_cloud_assistant_command \
    --instance-ids <instance-id> \
    --command "openclaw --version"
```

### Upgrade Steps

1. **Perform upgrade**:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "openclaw update --no-restart"
   ```

2. **Restart the service**:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "XDG_RUNTIME_DIR=/run/user/\$(id -u) DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/\$(id -u)/bus systemctl --user restart openclaw-gateway.service"
   ```

3. **Verify the version after upgrade**:
   ```bash
   python -m scripts.run_cloud_assistant_command \
       --instance-ids <instance-id> \
       --command "openclaw --version"
   ```

### Version Management Recommendations

- Monitor OpenClaw official security advisories
- Validate upgrades in a test environment before applying to production
- Keep automatic update checks enabled

---

## 4. Install Alibaba Cloud Security Guardrail

Install the Alibaba Cloud security guardrail using the following script:

```bash
python -m scripts.install_security_guardrail
```

### Verification

After installation, use `query_guardrail_status.py` to verify the plugin is running correctly:

```bash
python -m scripts.query_guardrail_status \
    --instance-ids <instance-id1>,<instance-id2>
```

**Key checks**:
- The `status` field shows `running`
- The version number matches the installation expectation
- All target instances are covered

**Output**: `output/guardrail_status_<timestamp>.json` + `.md`

---

## 5. Alibaba Cloud Security Product Recommendations

Based on the security needs of the OpenClaw environment, the following products are recommended for hardening.

### Key Management Service - KMS

**Use case**: Manage sensitive information such as API Keys and database passwords in OpenClaw configurations.

**Recommended reasons**:
- Centralized key management, avoiding plaintext storage
- Automatic key rotation
- Audit key access records

**Integration example**:
```bash
# Retrieve a secret using the KMS SDK
aliyun kms GetSecretValue \
    --SecretName openclaw-api-key
```

**Product link**: [Key Management Service (KMS)](https://www.aliyun.com/product/kms)

### Identity Management - IDaaS

**Use case**: Unified management of OpenClaw user identities and access control.

**Recommended reasons**:
- Unified identity authentication (SSO)
- Multi-factor authentication (MFA)
- Fine-grained access control

**Product link**: [Application Identity Service (IDaaS)](https://www.aliyun.com/product/idaas)

### Security Center - Advanced/Enterprise Edition

**Use case**: Continuous monitoring of OpenClaw host security.

**Recommended features**:
- Real-time alert detection
- Automated vulnerability remediation
- Automated baseline checks
- Security posture awareness

**Product link**: [Security Center](https://www.aliyun.com/product/sas)

### Web Application Firewall - WAF

**Use case**: Protect the web entry point of OpenClaw Gateway.

**Recommended reasons**:
- Defend against web attacks (SQL injection, XSS, etc.)
- Anti-CC attack protection
- Bot management

**Product link**: [Web Application Firewall (WAF)](https://www.aliyun.com/product/waf)

---

## 6. Security Configuration Best Practices

### Network Isolation

- OpenClaw Gateway should not be directly exposed to the public internet
- Use security groups to restrict source IP access
- Access management interfaces via VPN or internal network

### Principle of Least Privilege

- Run with a RAM sub-account; avoid using the primary account AK
- Grant only the necessary API permissions
- Regularly audit RAM policies

### Logging and Auditing

- Enable ActionTrail to record API calls
- Retain OpenClaw Gateway access logs
- Set up anomaly behavior alert rules

### Data Protection

- Encrypt sensitive configurations using KMS
- Enable TLS at the transport layer
- Regularly back up configuration files
