# Certificate Download — API Commands

## Certificate Download Reference

### get-instance-detail — Query Instance Details (New API)

```bash
aliyun cas get-instance-detail --profile $CERT_PROFILE --region $CERT_REGION --instance-id "{{instance_id}}" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id}
```

**Download-related response fields:**

| Field | Description |
|-------|-------------|
| `Cert` | Server certificate PEM (non-SM2, full chain or server only) |
| `Key` | Non-SM2 private key PEM |
| `EncryptCert` / `EncryptPrivateKey` | SM2 encryption cert/key |
| `SignCert` / `SignPrivateKey` | SM2 signing cert/key |
| `CertChain` | Certificate chain array |
| `Common` | Primary domain |
| `Sans` | All bound domains |
| `Algorithm` | Algorithm (RSA/ECC) |
| `StartDate` / `EndDate` | Validity period |
| `CertificateStatus` | Certificate status (`issued`/`checking`/`failed`) |

### list-instances — Search Instances

```bash
aliyun cas list-instances --profile $CERT_PROFILE --region $CERT_REGION --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-common-tools/{session-id} \
  --keyword "{{domain}}" --current-page 1 --show-size 10
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `keyword` | No | Fuzzy match domain, name, instance ID |
| `status` | No | `inactive` / `pending` / `normal` / `willExpire` / `expired` / `refund` / `closed` |
| `instance-type` | No | `BUY` / `TEST` |
| `certificate-type` | No | `DV` / `OV` / `EV` |

### Certificate Chain Split

Use `scripts/split-chain.sh` for chain splitting and verification (do not rewrite inline):
```bash
bash scripts/split-chain.sh fullchain.pem /output/dir
# Outputs: server_only.pem, chain.pem, fullchain.pem
```

### Chain Verification Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `unable to get local issuer certificate` | Missing intermediate cert | Check chain.pem completeness |
| `certificate has expired` | Cert or intermediate expired | Check `NotAfter` |
| `self signed certificate` | Root cert in chain | Ensure root not in chain file |

---

