# Command Reference

## WAF 3.0 Certificate Status

```bash
aliyun waf-openapi describe-certs \
  --instance-id <instance_id> \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --page-size 100 --pager \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-certchain-complete/{session-id} skill-version/{skill-version}"
```

Key response fields: `CertIdentifier`, `CertName`, `CommonName`, and `IsChainCompleted`.

## Certificate Inspection

```bash
openssl x509 -in cert.pem -noout -subject
openssl x509 -in cert.pem -noout -issuer
openssl x509 -in cert.pem -noout -ext authorityInfoAccess
openssl x509 -in cert.pem -noout -dates
openssl x509 -in cert.pem -text -noout
```

## Local Chain Check and Repair

```bash
# Check a local PEM
python3 scripts/fix_certchain.py --file cert.pem

# JSON result
python3 scripts/fix_certchain.py --file cert.pem --json

# Fetch missing intermediates and create a complete chain
python3 scripts/fix_certchain.py \
  --file cert.pem \
  --fix \
  --output complete_chain.pem

# Verify repaired chain
python3 scripts/fix_certchain.py --file complete_chain.pem
```

## Manual Fallback

```bash
openssl x509 -in cert.pem -noout -issuer
openssl x509 -in cert.pem -noout -ext authorityInfoAccess
cat server_cert.pem intermediate.pem > complete_chain.pem
openssl verify -untrusted intermediate_bundle.pem server_cert.pem
```

Use only official CA repositories for intermediate downloads. This Skill does not list domains, query domain configuration, probe remote TLS endpoints, or upload certificates through APIs.
