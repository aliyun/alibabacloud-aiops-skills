# Verification Method - alibabacloud-dns-resolve-diagnose-customer

## Post-Diagnosis Verification

After the diagnostic report is generated, users can verify fixes using the following commands.

### DNS Resolution Verification

```bash
# Query A records
dig <domain> @223.5.5.5 +short
dig <domain> @8.8.8.8 +short

# Query CNAME records
dig <domain> CNAME +short

# Trace resolution path
dig <domain> +trace

# Flush local DNS cache and verify
# macOS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
# Linux
sudo systemd-resolve --flush-caches
```

### Nationwide Propagation Verification

Visit https://boce.aliyun.com/detect/dns and enter the domain to perform a nationwide DNS probe, confirming that resolution results are consistent across all regions.

### OpenAPI Configuration Verification

```bash
# Verify DNS record configuration is correct
aliyun alidns describe-domain-records --DomainName <domain> --RRKeyWord <rr> --PageSize 100

# Verify domain status is normal
aliyun domain query-domain-by-domain-name --DomainName <domain>
```

### Expected Results After Common Fixes

| Issue Type | Fix Action | Expected Verification Result |
|------------|-----------|------------------------------|
| Missing record | Add A/CNAME record | dig returns correct IP/CNAME |
| Incorrect record | Modify record value | dig returns new IP (wait for TTL expiry) |
| Domain expired | Renew domain | WHOIS shows new expiration date; resolution recovers after 24-48h |
| NS not switched | Change domain NS servers | dig NS returns correct NS servers |
| PrivateZone VPC not bound | Bind VPC | dig from within VPC returns correct result |
