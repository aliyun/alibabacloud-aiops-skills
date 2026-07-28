# Verification Method

Detailed success verification steps for each toolkit function.

## Identity Resolver

**Expected Outcome:** Valid credential profile configured and verified.

**Verification Commands:**
```bash
# 1. Confirm identity
aliyun sts get-caller-identity --profile $CERT_PROFILE --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

**Success Indicator:** Response contains `AccountId` field with a valid account number.

**Failure Indicators:**
- `InvalidAccessKeyId.NotFound` — credential not configured
- `SignatureDoesNotMatch` — wrong secret key
- `Forbidden.RAM` — insufficient permissions

---

## Domain Verify

**Expected Outcome:** Domain ownership verified, certificate status changes to `issued`.

**Verification Commands:**
```bash
# 1. Check instance status
aliyun cas get-instance-detail --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{id}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}

# 2. Verify DNS TXT record (if DNS method)
aliyun alidns describe-domain-records --profile $CERT_PROFILE --domain-name "{{root_domain}}" --type TXT --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

**Success Indicator:** `CertificateStatus` field equals `issued`.

**Failure Indicators:**
- `CertificateStatus` stays `checking` after 30 minutes — DNS record not propagated
- `CertificateStatus` is `failed` — wrong TXT value or domain mismatch

---

## Certificate Download

**Expected Outcome:** Certificate files downloaded, chain split, integrity verified.

**Verification Commands:**
```bash
# 1. Verify certificate chain
openssl verify -CAfile "{{output_dir}}/chain.pem" "{{output_dir}}/server_only.pem"

# 2. Check output files exist
ls -la "{{output_dir}}/server_only.pem" "{{output_dir}}/chain.pem" "{{output_dir}}/fullchain.pem"

# 3. Verify certificate content
openssl x509 -in "{{output_dir}}/server_only.pem" -text -noout | grep -E "Subject:|Issuer:|Not Before:|Not After:"
```

**Success Indicator:** `openssl verify` outputs `OK`; all three PEM files exist with non-zero size.

**Failure Indicators:**
- `openssl verify` returns error — chain incomplete or wrong intermediate
- `Cert` field empty in API response — certificate not issued or SM2 type

---

## Certificate Upload

**Expected Outcome:** Third-party certificate uploaded to CAS, `CertId` returned.

**Verification Commands:**
```bash
# 1. Check upload result contains CertId
# API response should include: {"CertId": <numeric_id>}

# 2. Verify uploaded certificate exists
aliyun cas list-instances --profile $CERT_PROFILE --region $CERT_REGION --keyword "{{cert_name}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}

# 3. Verify key-cert match before upload
bash scripts/modulus-check.sh key-cert "{{key_file}}" "{{cert_file}}"
```

**Success Indicator:** `CertId` is a positive integer; `modulus-check.sh` reports `MATCH`.

**Failure Indicators:**
- `NameAlreadyExist` — certificate name not unique
- `KeyNotMatchCert` — private key does not match certificate

---

## CSR Generation

**Expected Outcome:** CSR file generated with correct subject and/or SAN entries.

**Verification Commands:**
```bash
# 1. Inspect CSR content
openssl req -in "{{csr_file}}" -text -noout

# 2. Check Subject field
openssl req -in "{{csr_file}}" -text -noout | grep "Subject:"

# 3. Check SAN entries (multi-domain)
openssl req -in "{{csr_file}}" -text -noout | grep -A1 "Subject Alternative Name"
```

**Success Indicator:** `Subject:` contains correct CN; SAN entries list all requested domains.

**Failure Indicators:**
- CSR file is empty or cannot be parsed
- SAN section missing when multi-domain was requested

---

## Format Conversion

**Expected Outcome:** Certificate converted to target format, output file is valid.

**Verification Commands:**
```bash
# PFX verification
openssl pkcs12 -in "{{output.pfx}}" -nokeys -passin pass:{{password}} | head -5

# JKS verification
keytool -list -keystore "{{output.jks}}" -storepass {{password}}

# DER verification
openssl x509 -inform DER -in "{{output.der}}" -text -noout | head -5

# PEM verification
openssl x509 -in "{{output.pem}}" -text -noout | head -5
```

**Success Indicator:** Target format file is parseable and contains valid certificate data.

**Failure Indicators:**
- `keytool` not found — JDK not installed (needed for JKS)
- Output file is empty — conversion failed silently

---

## Certificate Matching

**Expected Outcome:** Key/certificate/CSR matching status determined.

**Verification Commands:**
```bash
# Key-Certificate match
bash scripts/modulus-check.sh key-cert "{{key.pem}}" "{{cert.pem}}"

# Key-CSR match
bash scripts/modulus-check.sh key-csr "{{key.pem}}" "{{csr.pem}}"

# All three
bash scripts/modulus-check.sh all "{{key.pem}}" "{{cert.pem}}" "{{csr.pem}}"

# Domain coverage check
openssl x509 -in "{{cert}}" -text -noout | awk '/X509v3 Subject Alternative Name/{getline; print}'

# Validity check
openssl x509 -in "{{cert}}" -noout -dates
```

**Success Indicator:** `modulus-check.sh` reports `MATCH` for the requested comparison type.

**Failure Indicators:**
- `MISMATCH` — key and certificate were not generated from the same key pair
- Domain not found in SAN — certificate does not cover the target domain
- Certificate expired per `Not After` date
