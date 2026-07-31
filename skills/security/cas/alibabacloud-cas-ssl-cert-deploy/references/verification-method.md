# Verification Method — SSL Certificate Deployment

## HTTPS Access Verification

After certificate deployment, verify HTTPS is working correctly.

### Basic Verification

```bash
curl -sI --connect-timeout 10 --max-time 30 https://{{domain}} | grep -i "subject\|issuer\|HTTP"
```

**Expected output:**
- `HTTP/2 200` (or `HTTP/1.1 200`)
- `subject: CN = {{domain}}`
- `issuer: CN = Alibaba Cloud SSL Certificate`

### Certificate Detail Verification

```bash
echo | openssl s_client -connect {{domain}}:443 -servername {{domain}} 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

Verify the certificate subject matches the target domain and the issuer is Alibaba Cloud.

## Per-Product Verification Checklist

### CDN

1. Verify via API:
   ```bash
   aliyun cdn describe-domain-certificate-info --domain-name "{{domain}}" --profile $CERT_PROFILE --region $CERT_REGION
   ```
2. Confirm `ServerCertificateStatus` is `on`
3. Verify HTTPS access with curl

### ALB

1. Verify listener certificate:
   ```bash
   aliyun alb list-listeners --load-balancer-ids.1 {{alb_id}} --region {{region_id}} --profile {{profile_name}}
   ```
2. Confirm HTTPS listener port 443 shows the new certificate ID
3. Verify HTTPS access with curl

### SLB / NLB

1. Verify via SLB console or API that HTTPS listener is active
2. Verify HTTPS access with curl

### WAF

1. Verify domain is onboarded with HTTPS enabled
2. Verify HTTPS access via WAF CNAME

### OSS

1. Verify custom domain is bound with HTTPS
2. Access `https://{{domain}}` to confirm static content serves over HTTPS

### ESA

1. Verify site/subdomain is configured with certificate
2. Verify HTTPS access with curl

## Common Verification Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SSL certificate problem: unable to get local issuer certificate` | Certificate chain incomplete | Re-deploy with full chain certificate |
| Connection timeout | Domain DNS not resolved | Check DNS records, wait for propagation |
| Certificate domain mismatch | Deployed to wrong domain | Redeploy to correct matching domain |
| `HTTP/1.1 301` redirect loop | HTTP→HTTPS redirect misconfigured | Check redirect configuration |
| Old certificate still shown | CDN cache not refreshed | Wait 1-2 minutes, retry verification |
