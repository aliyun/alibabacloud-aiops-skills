# DNS Diagnostic Case Studies

## Case 1: ISP Hijacking Causing Resolution Failure

**Issue**: Domain `www.example.com` resolves to `127.0.0.1`

**Diagnostic Process**:
1. WHOIS check: Domain valid, status normal
2. NS check: Using Alibaba Cloud DNS (`ns1.alidns.com`, `ns2.alidns.com`)
3. Recursive trace: `dig +trace` chain normal, authoritative DNS returns correct IP
4. Multi-DNS comparison: 223.5.5.5 returns `127.0.0.1`, 8.8.8.8 returns correct IP
5. OpenAPI query: Record configured as A record `1.2.3.4`, status normal
6. DNS probing: 90% nodes resolve correctly, 10% return `127.0.0.1`

**Conclusion**:
- Authoritative DNS config is correct; some ISP recursive DNS servers are hijacking
- Hijack IP `127.0.0.1` is a typical anti-fraud/security interception indicator

**Recommendations**:
1. Switch local DNS server to `223.6.6.6` or `8.8.8.8` for testing
2. For permanent fix, contact ISP or change domain

---

## Case 2: Expired Domain Causing Global Resolution Failure

**Issue**: Domain `app.mysite.cn` completely unresolvable, returns NXDOMAIN

**Diagnostic Process**:
1. WHOIS check: **Domain expired 15 days ago**
2. Recursive trace: All DNS servers return NXDOMAIN
3. DNS probing: 100% nodes cannot resolve

**Conclusion**:
- Domain has expired; registry has stopped resolution service

**Recommendations**:
1. Renew domain immediately
2. If domain is in redemption period, contact registrar for redemption
3. After renewal, wait for DNS propagation (typically 24-48 hours)

---

## Case 3: DNS Record Change Not Propagated

**Issue**: Changed A record of `www.example.com` from `1.1.1.1` to `2.2.2.2`, but still resolves to old IP

**Diagnostic Process**:
1. OpenAPI query: Record updated to `2.2.2.2`, TTL is 600 seconds
2. Recursive DNS comparison:
   - 223.5.5.5 -> `2.2.2.2` (updated)
   - 8.8.8.8 -> `1.1.1.1` (not yet updated)
   - 114.114.114.114 -> `1.1.1.1` (not yet updated)
3. DNS probing: 40% nodes updated, 60% still return old IP

**Conclusion**:
- Authoritative config correctly updated, but recursive DNS caches nationwide have not expired
- Current TTL=600s, need to wait for cache refresh at each location

**Recommendations**:
1. This is normal DNS propagation delay; recheck after 10-30 minutes
2. To speed up future changes, lower TTL to 60s before modifying records
3. Verify locally with `dig @223.5.5.5 www.example.com` to confirm Alibaba Cloud DNS is updated

---

## Case 4: PrivateZone Domain Cannot Resolve Within VPC

**Issue**: `dig db.internal.com` returns NXDOMAIN inside ECS instance

**Diagnostic Process**:
1. NS check: `internal.com` has no public NS records (normal, PrivateZone doesn't work on public internet)
2. OpenAPI PrivateZone query: Found Zone `internal.com`, record `db` -> A `10.0.1.100`
3. Zone details: **Bound to VPC-A, but ECS is in VPC-B**

**Conclusion**:
- PrivateZone is not bound to the VPC where ECS resides

**Recommendations**:
1. Bind the Zone to the ECS instance's VPC in PrivateZone console
2. Takes approximately 1 minute to take effect after binding

---

## Case 5: GTM Scheduling Anomaly

**Issue**: GTM domain `api.example.com` resolves to IP not matching expected regional routing strategy

**Diagnostic Process**:
1. NS check: Domain CNAMEs to GTM-assigned domain
2. OpenAPI GTM query: Instance normal, not expired
3. GTM access strategy: Configured East China -> IP-A, North China -> IP-B
4. DNS probing: East China nodes correctly resolve to IP-A, but North China nodes also resolve to IP-A

**Conclusion**:
- GTM regional strategy may be incomplete; North China region not properly configured
- Or North China address pool health check failed, triggering failover to default pool

**Recommendations**:
1. Check GTM address pool health check status
2. Verify North China access strategy configuration
3. Check default address pool priority settings

---

## Case 6: Third-Party DNS Domain Resolution Failure

**Issue**: Domain `shop.example.com` cannot resolve; domain registered on Alibaba Cloud but uses Cloudflare DNS

**Diagnostic Process**:
1. NS check: NS points to `xxx.ns.cloudflare.com` (not Alibaba Cloud)
2. OpenAPI query: Domain under Alibaba Cloud account, but DNS servers changed to Cloudflare
3. dig comparison: All public DNS return NXDOMAIN
4. DNS probing: 100% nodes cannot resolve

**Conclusion**:
- Domain NS points to Cloudflare, but Cloudflare may not have DNS records configured
- Alibaba Cloud cannot control third-party DNS configuration

**Recommendations**:
1. Log into Cloudflare dashboard to check DNS record configuration
2. To switch back to Alibaba Cloud DNS, modify NS at domain registrar to Alibaba Cloud-assigned DNS servers
3. NS switch takes 24-48 hours for global propagation
