# Verification Method - alibabacloud-dns-resolve-diagnose

## Post-Diagnosis Verification

After the diagnostic report is generated, users can verify fixes with the following commands.

### DNS Resolution Verification

```bash
# Query A record
dig <domain> @223.5.5.5 +short
dig <domain> @8.8.8.8 +short

# Query CNAME record
dig <domain> CNAME +short

# Trace resolution path
dig <domain> +trace

# Flush local DNS cache before verification
# macOS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
# Linux
sudo systemd-resolve --flush-caches
```

### Nationwide Propagation Verification

Visit https://boce.aliyun.com/detect/dns, enter the domain name to run nationwide probing and confirm consistent results across regions.

### OpenAPI Config Verification

```bash
# Verify DNS record configuration
aliyun alidns describe-domain-records --DomainName <domain> --RRKeyWord <rr> --PageSize 100 --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}

# Verify domain status
aliyun domain query-domain-by-domain-name --DomainName <domain> --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

### Expected Results After Common Fixes

| Issue Type | Fix Action | Expected Verification Result |
|-----------|-----------|----------------------------|
| Missing record | Add A/CNAME record | dig returns correct IP/CNAME |
| Incorrect record | Modify record value | dig returns new IP (wait for TTL expiry) |
| Domain expired | Renew domain | WHOIS shows new expiry date, resolution recovers in 24-48h |
| NS not switched | Modify domain NS servers | dig NS returns correct NS servers |
| PrivateZone VPC not bound | Bind VPC | dig within VPC returns correct result |
