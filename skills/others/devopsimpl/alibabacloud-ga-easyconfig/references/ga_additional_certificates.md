# HTTPS Additional Certificates Reference

This document describes how to bind multiple SSL certificates (additional certificates / SNI) to a single GA HTTPS listener, so that different domains can use different certificates.

> **Important**: Additional certificates apply only to **HTTPS listeners**.

---

## 1. Use Cases

- One HTTPS listener serves multiple domains (e.g., `www.example.com`, `api.example.com`, `*.example.com`).
- Different domains use different certificates instead of a single multi-domain (SAN) certificate.
- Independent certificate lifecycle management per business line.

---

## 2. Prerequisites

1. An HTTPS listener already exists with a default certificate (`Certificates` field).
2. Additional certificates must be uploaded to Alibaba Cloud SSL Certificate Service (CAS) first; obtain the certificate IDs.
3. Certificate domains must match the listener's configured domains or SNI expectations.

---

## 3. Associate Additional Certificates

```bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
CERT_ID_1="1234-cn-hangzhou"   # Certificate ID from CAS
CERT_ID_2="5678-cn-hangzhou"

aliyun ga associate-additional-certificates-with-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --certificates "[{\"Id\":\"$CERT_ID_1\"},{\"Id\":\"$CERT_ID_2\"}]" \
  --user-agent "$GA_USER_AGENT"
```

### Parameter Reference

| Parameter | Description |
|---|---|
| AcceleratorId | GA accelerator ID |
| ListenerId | HTTPS listener ID |
| certificates | JSON array of `{"Id":"<cert-id>"}`; each Id is an SSL certificate ID from CAS console or `list-certificates` (`CertIdentifier`) |

---

## 4. List Additional Certificates

```bash
aliyun ga list-listener-certificates \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.Certificates[] | {
    CertificateId,
    Domain,
    Type
  }'
```

---

## 5. Dissociate Additional Certificates

```bash
aliyun ga dissociate-additional-certificates-from-listener \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --certificates "[{\"Id\":\"$CERT_ID_1\"}]" \
  --user-agent "$GA_USER_AGENT"
```

---

## 6. Replace the Default Listener Certificate

To replace the listener-level default certificate, use `update-listener`:

```bash
aliyun ga update-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --certificates "[{\"Id\":\"$NEW_DEFAULT_CERT_ID\"}]" \
  --user-agent "$GA_USER_AGENT"
```

---

## 7. Complete Example

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
REGION="cn-hangzhou"

# Step 1: List available CAS certificates
echo "=== Available SSL certificates ==="
aliyun cas list-certificates \
  --region "$REGION" \
  --current-page 1 \
  --show-size 50 | jq '.CertificateList[] | {CertId: .CertificateId, CertIdentifier, CommonName, NotAfter}'

# Step 2: Associate additional certificates
read -p "Enter certificate IDs to associate (space-separated): " CERT_IDS

echo "=== Associating additional certificates ==="
CERT_JSON=$(printf '%s\n' $CERT_IDS | jq -R '{Id: .}' | jq -s -c .)

aliyun ga associate-additional-certificates-with-listener \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --certificates "$CERT_JSON" \
  --user-agent "$GA_USER_AGENT"

# Step 3: Verify
aliyun ga list-listener-certificates \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" \
  --page-size 50
```

---

## 8. Skill Integration Notes

During Step 4 (create HTTPS listener), optionally ask:

```
Question: Do you want to add additional certificates (multi-domain SNI) to this listener?
- Option 1: No (default, use only the default certificate)
- Option 2: Yes

If yes:
1. Call `cas list-certificates` to list issued certificates.
2. Let the user select certificate IDs to bind.
3. Call associate-additional-certificates-with-listener.
4. Call list-listener-certificates to verify.
```

---

## 9. Notes

1. Additional certificates are supported only on HTTPS listeners; HTTP/TCP/UDP listeners do not support certificates.
2. Only certificates in `ISSUED` status can be bound.
3. The CommonName or SAN domain of the additional certificate must match the listener's SNI.
4. Each listener has a quota for additional certificates (commonly 10 by default; verify in the console).
5. GA does not support direct certificate upload; manage certificates through CAS.
