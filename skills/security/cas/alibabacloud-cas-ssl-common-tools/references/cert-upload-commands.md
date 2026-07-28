# Certificate Upload — API Commands

## Certificate Upload Reference

### upload-user-certificate — Upload Third-Party Certificate

```bash
aliyun cas upload-user-certificate --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --Name "my-cert" --Cert "$(cat cert.pem)" --Key "$(cat key.pem)"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `Name` | Yes | Certificate name (unique per user, max 63 chars) |
| `Cert` | Conditional | PEM certificate content (mutually exclusive with SM2 params) |
| `Key` | Conditional | PEM private key content |
| `EncryptCert` / `EncryptPrivateKey` | Conditional | SM2 encryption cert/key |
| `SignCert` / `SignPrivateKey` | Conditional | SM2 signing cert/key |

**Success response:** `{"CertId": 12345}`

### PFX Extraction

```bash
openssl pkcs12 -in cert.pfx -nokeys -passin pass:"{{password}}" -out cert.pem
openssl pkcs12 -in cert.pfx -nocerts -nodes -passin pass:"{{password}}" -out key.pem
```

### Certificate Parsing

```bash
openssl x509 -in cert.pem -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After:|Subject Alternative Name:" -A1
# Modulus comparison
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

### Upload Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| `NameAlreadyExist` | Duplicate name | Use different name |
| `InvalidParameter.Cert` | Invalid certificate content | Check PEM format |
| `KeyNotMatchCert` | Private key doesn't match certificate | Verify modulus match |

---

## Pre-Upload Checklist

| Check | Method | Failure Handling |
|-------|--------|------------------|
| Certificate parseable | `openssl x509 -in cert.pem -noout` exit 0 | Format error or wrong password |
| Validity not expired | `Not After` after current time | Cannot deploy expired cert |
| Key matches cert | `scripts/modulus-check.sh key-cert` | Mismatch — wrong key file |
