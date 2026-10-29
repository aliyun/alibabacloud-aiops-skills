# GA Listener API Reference (Step 4)

This document provides complete CLI scripts for creating, querying, and modifying Global Accelerator listeners.

> **Listeners** inspect client connection requests and forward traffic to endpoint groups based on protocol and port. TCP, UDP, HTTP, and HTTPS are supported.

---

## 1. create-listener

Create a listener.

### TCP listener (standard routing)

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "tcp-listener-80" \
  --protocol tcp \
  --type Standard \
  --user-agent "$GA_USER_AGENT" \
  --client-affinity SOURCE_IP \
  --port-ranges FromPort=80 ToPort=80
```

### TCP listener (port range)

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "tcp-listener-range" \
  --protocol tcp \
  --user-agent "$GA_USER_AGENT" \
  --type Standard \
  --port-ranges FromPort=1000 ToPort=2000
```

### TCP listener (multiple port ranges)

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "tcp-listener-multi" \
  --protocol tcp \
  --user-agent "$GA_USER_AGENT" \
  --type Standard \
  --port-ranges '[{"FromPort":"80","ToPort":"80"},{"FromPort":"443","ToPort":"443"},{"FromPort":"8080","ToPort":"8090"}]'
```

### UDP listener

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "udp-listener-53" \
  --protocol udp \
  --user-agent "$GA_USER_AGENT" \
  --type Standard \
  --port-ranges FromPort=53 ToPort=53
```

### HTTP listener

> **Note**: HTTP/HTTPS listeners support only a single port (FromPort == ToPort).

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "http-listener-80" \
  --protocol http \
  --type Standard \
  --idle-timeout 900 \
  --request-timeout 60 \
  --http-version http2 \
  --user-agent "$GA_USER_AGENT" \
  --port-ranges FromPort=80 ToPort=80 \
  --xforwarded-for-config XForwardedForGaIdEnabled=true XRealIpEnabled=true
```

### HTTPS listener

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "https-listener-443" \
  --protocol https \
  --type Standard \
  --security-policy-id tls_cipher_policy_1_2 \
  --idle-timeout 900 \
  --request-timeout 60 \
  --http-version http2 \
  --user-agent "$GA_USER_AGENT" \
  --port-ranges FromPort=443 ToPort=443 \
  --certificates Id="${CERT_ID}" \
  --xforwarded-for-config XForwardedForGaIdEnabled=true XRealIpEnabled=true
```

### Custom routing listener

```bash
aliyun ga create-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --name "custom-routing-listener" \
  --protocol tcp \
  --user-agent "$GA_USER_AGENT" \
  --type CustomRouting \
  --port-ranges FromPort=10000 ToPort=20000
```

### Parameter reference

| Parameter | Type | Required | Description | Allowed values |
|-----------|------|----------|-------------|----------------|
| RegionId | string | Yes | Fixed `cn-hangzhou` | `cn-hangzhou` |
| AcceleratorId | string | Yes | GA instance ID | - |
| Name | string | No | Listener name | 1~128 characters |
| Description | string | No | Description | Max 200 characters |
| Protocol | string | Yes | Listener protocol | `tcp` / `udp` / `http` / `https` |
| PortRanges.N.FromPort | integer | Yes | Start port | `1` ~ `65499` |
| PortRanges.N.ToPort | integer | Yes | End port | `1` ~ `65499` |
| Type | string | No | Routing type | `Standard` / `CustomRouting` |
| ClientAffinity | string | No | Client affinity | `SOURCE_IP` / empty |
| Certificates.N.Id | string | No | Certificate ID (required for HTTPS) | SSL certificate ID |
| SecurityPolicyId | string | No | TLS security policy (HTTPS only) | `tls_cipher_policy_1_0` / `tls_cipher_policy_1_1` / `tls_cipher_policy_1_2` |
| IdleTimeout | integer | No | Connection idle timeout (seconds) | TCP/UDP default 900; HTTP/HTTPS 1~60 |
| RequestTimeout | integer | No | Request timeout (seconds, HTTP/HTTPS only) | 1~180, default 60 |
| HttpVersion | string | No | Maximum HTTP version (HTTP/HTTPS only) | `http1.1` / `http2` / `http3` |
| ClientToken | string | No | Idempotency token | - |

### XForwardedForConfig sub-parameters (HTTP/HTTPS only)

| Parameter | Type | Description |
|-----------|------|-------------|
| XForwardedForConfig.XForwardedForGaIdEnabled | boolean | Include GA instance ID in X-Forwarded-For headers |
| XForwardedForConfig.XForwardedForGaApEnabled | boolean | Include GA access point info in X-Forwarded-For headers |
| XForwardedForConfig.XForwardedForProtoEnabled | boolean | Include listener protocol in X-Forwarded-For headers |
| XForwardedForConfig.XForwardedForPortEnabled | boolean | Include listener port in X-Forwarded-For headers |
| XForwardedForConfig.XRealIpEnabled | boolean | Include client real IP in X-Real-IP headers |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| RequestId | string | Request ID |
| ListenerId | string | Listener ID |

### Sample response

```json
{
  "RequestId": "04F0F334-1335-436C-xxxx",
  "ListenerId": "lsr-bp1bpn0kn908w4nbq****"
}
```

### Error handling

| Error code | Meaning | Resolution |
|------------|---------|------------|
| StateError.Accelerator | GA instance state does not allow the operation | Retry after the instance becomes `active` |
| PortRangeIllegal.Listener | Invalid port configuration | HTTP/HTTPS support only single ports; check port ranges |
| PortConflict.Listener | Port conflict | Check for conflicts with existing listener ports |
| ListenerOverLimit | Too many listeners | Delete unnecessary listeners |
| CertificateNotFound | Certificate not found | Check the HTTPS certificate ID |

---

## 2. describe-listener

Query listener details.

```bash
aliyun ga describe-listener \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" \
  --listener-id "${LISTENER_ID}"
```

### Extract key fields

```bash
aliyun ga describe-listener \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    ListenerId,
    Name,
    State,
    Protocol,
    PortRanges,
    Type,
    ClientAffinity,
    AcceleratorId,
    Certificates,
    SecurityPolicyId
  }'
```

### Poll until the listener is active

```bash
LISTENER_ID="lsr-bp1xxxx"
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
STATE=$(aliyun ga describe-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "Listener is active."
    break
  fi

  echo "Waiting for listener to become active... [$i/$MAX_WAIT] current state: $STATE"
  sleep 10
done

if [ "$STATE" != "active" ]; then
  echo "Timeout: listener did not become active"
fi
```

### Key response fields

| Field | Type | Description |
|-------|------|-------------|
| ListenerId | string | Listener ID |
| Name | string | Listener name |
| State | string | State: `init`/`active`/`creating`/`configuring`/`deleting` |
| Protocol | string | Protocol |
| PortRanges | array | Port range list |
| Type | string | Routing type |
| ClientAffinity | string | Client affinity |
| AcceleratorId | string | GA instance ID |
| Certificates | array | Certificate list (HTTPS) |
| SecurityPolicyId | string | TLS security policy (HTTPS) |
| CreateTime | string | Creation time |

---

## 3. list-listeners

Query the listener list.

```bash
aliyun ga list-listeners \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

### Format output

```bash
aliyun ga list-listeners \
  --biz-region-id cn-hangzhou \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" | jq '.Listeners[] | {
    ListenerId,
    Name,
    State,
    Protocol,
    PortRanges: [.PortRanges[] | "\(.FromPort)-\(.ToPort)"],
    Type
  }'
```

---

## 4. update-listener

Modify a listener.

### Change listener name

```bash
aliyun ga update-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --name "${NEW_NAME}"
```

### Change listener ports

```bash
aliyun ga update-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --port-ranges FromPort=8080 ToPort=8080
```

### Change client affinity

```bash
aliyun ga update-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --client-affinity SOURCE_IP
```

### Replace HTTPS certificate

```bash
aliyun ga update-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --certificates Id="${NEW_CERT_ID}"
```

---

## 5. list-system-security-policies

Query the list of TLS security policies supported by HTTPS listeners.

```bash
aliyun ga list-system-security-policies \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou
```

---

## 6. HTTPS certificate management

### Bind additional certificates to a listener

```bash
aliyun ga associate-additional-certificates-with-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --accelerator-id "${GA_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --certificates Id="${ADDITIONAL_CERT_ID}" Domain="example.com"
```

### Unbind additional certificates

```bash
aliyun ga dissociate-additional-certificates-from-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --accelerator-id "${GA_ID}" \
  --domains "example.com" \
  --user-agent "$GA_USER_AGENT"
```

### Replace an additional certificate

```bash
aliyun ga update-additional-certificate-with-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --accelerator-id "${GA_ID}" \
  --certificate-id "${NEW_CERT_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --domain "example.com"
```

### List certificates bound to a listener

```bash
aliyun ga list-listener-certificates \
  --biz-region-id cn-hangzhou \
  --listener-id "${LISTENER_ID}" \
  --user-agent "$GA_USER_AGENT" \
  --accelerator-id "${GA_ID}"
```

---

## Complete example: create a TCP listener

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"

# Step 1: Create a TCP listener
echo "Creating TCP listener..."
LISTENER_RESULT=$(aliyun ga create-listener \
  --user-agent "$GA_USER_AGENT" \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --name "tcp-listener-80" \
  --protocol TCP \
  --type Standard \
  --client-affinity SOURCE_IP \
  --port-ranges FromPort=80 ToPort=80)

LISTENER_ID=$(echo "$LISTENER_RESULT" | jq -r '.ListenerId')
echo "Listener created: $LISTENER_ID"

# Step 2: Wait for the listener to become active
echo "Waiting for listener to become active..."
for i in $(seq 1 30); do
STATE=$(aliyun ga describe-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" | jq -r '.State')

  if [ "$STATE" = "active" ]; then
    echo "Listener is active."
    break
  fi
  echo "Waiting... [$i/30] state: $STATE"
  sleep 10
done

# Step 3: Display listener information
echo ""
echo "=== Listener configuration ==="
aliyun ga describe-listener \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    ListenerId,
    Name,
    Protocol,
    PortRanges: [.PortRanges[] | "\(.FromPort)-\(.ToPort)"],
    Type,
    State
  }'
```
