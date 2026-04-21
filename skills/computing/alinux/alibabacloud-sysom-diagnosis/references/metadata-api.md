# ECS Metadata Service

## What Is the Metadata Service?

ECS Metadata is a built-in HTTP service provided inside Alibaba Cloud ECS instances. It exposes instance metadata and can be accessed **from inside the instance without configuring AccessKey**.

---

## Endpoints

| Version | Endpoint URL | Notes |
|------|----------|------|
| V1 | `http://100.100.100.200/` | Simplified access, no token required |
| V2 | `http://100.100.100.200/latest/meta-data/` | Requires IMDSv2 token, more secure |
| Compatibility | `http://169.254.169.254/` | AWS-compatible endpoint |

---

## Common Metadata Fields

### Basic Instance Info

```bash
curl http://100.100.100.200/latest/meta-data/instance-id          # Instance ID
curl http://100.100.100.200/latest/meta-data/instance-type        # Instance type
curl http://100.100.100.200/latest/meta-data/region-id            # Region ID
curl http://100.100.100.200/latest/meta-data/zone-id              # Zone ID
curl http://100.100.100.200/latest/meta-data/hostname             # Hostname
curl http://100.100.100.200/latest/meta-data/serial-number        # Serial number
curl http://100.100.100.200/latest/meta-data/image-id             # Image ID
curl http://100.100.100.200/latest/meta-data/os-type              # OS type
curl http://100.100.100.200/latest/meta-data/os-name              # OS name
curl http://100.100.100.200/latest/meta-data/launch-time          # Launch time
```

### Networking

```bash
curl http://100.100.100.200/latest/meta-data/mac                  # MAC address
curl http://100.100.100.200/latest/meta-data/vpc-id               # VPC ID
curl http://100.100.100.200/latest/meta-data/vswitch-id           # VSwitch ID
curl http://100.100.100.200/latest/meta-data/private-ipv4         # Private IPv4
curl http://100.100.100.200/latest/meta-data/public-ipv4          # Public IPv4
curl http://100.100.100.200/latest/meta-data/eipv4                # EIP address
curl http://100.100.100.200/latest/meta-data/network/interfaces/macs/<MAC>/vpc-id  # VPC of specific NIC
```

### Security-Related

```bash
curl http://100.100.100.200/latest/meta-data/security-groups      # Security group list
curl http://100.100.100.200/latest/meta-data/ram-role-name        # RAM role name
```

### Others

```bash
curl http://100.100.100.200/latest/meta-data/ntp-conf/ntp-servers # NTP servers
curl http://100.100.100.200/latest/meta-data/source-address       # Request source address
```

---

## List All Available Fields

```bash
curl http://100.100.100.200/latest/meta-data/
```

---

## IMDSv2 (More Secure Access)

Alibaba Cloud supports IMDSv2, which requires a token:

```bash
# Step 1: get token
TOKEN=$(curl -X PUT "http://100.100.100.200/latest/api/token" \
  -H "X-aliyun-ecs-metadata-token-ttl-seconds: 21600")

# Step 2: access metadata with token
curl -H "X-aliyun-ecs-metadata-token: $TOKEN" \
  http://100.100.100.200/latest/meta-data/instance-id
```

---

## Metadata Service Characteristics

| Characteristic | Description |
|------|------|
| Instance-local only | Accessible only from inside the ECS instance |
| No credential required (V1) | V1 mode does not require credential material |
| Real-time | Values update with current instance state |
| Read-only | Can read only, cannot modify |
| Local traffic | No public internet traffic generated |

---

## Typical Use Cases

### 1) Auto-fetch Instance Info in Scripts

```bash
INSTANCE_ID=$(curl -s http://100.100.100.200/latest/meta-data/instance-id)
echo "Running on instance: $INSTANCE_ID"
```

### 2) Dynamic Config by Instance Type

```bash
INSTANCE_TYPE=$(curl -s http://100.100.100.200/latest/meta-data/instance-type)
case $INSTANCE_TYPE in
  *large*) WORKERS=4 ;;
  *xlarge*) WORKERS=8 ;;
esac
```

### 3) Fetch RAM Role Temporary Credentials

```bash
ROLE_NAME=$(curl -s http://100.100.100.200/latest/meta-data/ram-role-name)
curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/$ROLE_NAME
```

### 4) SysOM Tool Scenario

**Auto-collect instance metadata for diagnosis**:

```bash
#!/bin/bash
# Auto-collect metadata for diagnosis report

INSTANCE_ID=$(curl -s http://100.100.100.200/latest/meta-data/instance-id)
REGION_ID=$(curl -s http://100.100.100.200/latest/meta-data/region-id)
INSTANCE_TYPE=$(curl -s http://100.100.100.200/latest/meta-data/instance-type)

echo "Instance Info:"
echo "  Instance ID: $INSTANCE_ID"
echo "  Region: $REGION_ID"
echo "  Type: $INSTANCE_TYPE"

# Run in sysom-diagnosis (skill root), or: cd <sysom-diagnosis> && ...
# Deep diagnosis after quick triage (oomcheck):
cd <sysom-diagnosis> && ./scripts/osops.sh memory oom --deep-diagnosis --channel ecs --region "$REGION_ID" --instance "$INSTANCE_ID"
```

**Validate RAM Role configuration**:

```bash
# Check whether the instance has RAM role attached
ROLE_NAME=$(curl -s http://100.100.100.200/latest/meta-data/ram-role-name)

if [ -z "$ROLE_NAME" ]; then
  echo "Warning: no RAM role is attached to this instance"
  echo "See ECS RAM Role setup in ./authentication.md"
else
  echo "RAM role attached: $ROLE_NAME"

  # Fetch temporary credentials
  CREDS=$(curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/$ROLE_NAME)
  echo "Temporary credentials fetched (auto-rotated within validity window)"
fi
```

---

## Security Recommendations

- Prefer IMDSv2 (token-based) to mitigate SSRF risks.
- Restrict token hops through MetadataOptions controls.
- Audit metadata access configuration on instances regularly.
- Avoid exposing metadata values to external users in application code.

---

## References

- [Alibaba Cloud ECS Metadata Docs](https://help.aliyun.com/zh/ecs/user-guide/overview-of-ecs-instance-metadata)
- [IMDSv2 Security Practices](https://help.aliyun.com/zh/ecs/user-guide/use-instance-metadata)
- [Authentication Guide](./authentication.md)
