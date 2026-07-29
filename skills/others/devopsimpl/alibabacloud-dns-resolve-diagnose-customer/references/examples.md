# DNS Diagnosis Case Studies

## Case 1: ISP Hijacking Causes Resolution Failure

**Problem Description**: Domain `www.example.com` resolves to `127.0.0.1`

**Diagnostic Process**:
1. WHOIS check: Domain validity and status are normal
2. NS check: Using Alibaba Cloud DNS (`ns1.alidns.com`, `ns2.alidns.com`)
3. Recursive resolution trace: `dig +trace` chain is normal, authoritative DNS returns correct IP
4. Multi-DNS comparison: 223.5.5.5 returns `127.0.0.1`, 8.8.8.8 returns correct IP
5. OpenAPI query: DNS record configured as A record `1.2.3.4`, status normal
6. DNS probe: 90% of nodes resolve correctly, 10% of nodes return `127.0.0.1`

**Diagnosis Conclusion**:
- Authoritative DNS is configured correctly; some ISP recursive DNS servers are hijacking queries
- Hijacked IP `127.0.0.1` is a typical anti-fraud/security interception pattern

**Recommendations**:
1. Change local DNS server to `223.6.6.6` or `8.8.8.8` for testing
2. For a permanent fix, contact the ISP or change the domain

---

## Case 2: Domain Expiration Causes Full Resolution Failure

**Problem Description**: Domain `app.mysite.cn` cannot be resolved at all, returning NXDOMAIN

**Diagnostic Process**:
1. WHOIS check: **Domain expired 15 days ago**
2. Recursive resolution trace: All DNS servers return NXDOMAIN
3. DNS probe: 100% of nodes fail to resolve

**Diagnosis Conclusion**:
- Domain has expired; the registry has suspended DNS resolution services

**Recommendations**:
1. Renew the domain immediately
2. If the domain has entered the redemption period, contact the registrar for redemption
3. After renewal, wait for DNS propagation (typically 24-48 hours)

---

## Case 3: DNS Record Change Not Yet Propagated

**Problem Description**: Changed A record for `www.example.com` from `1.1.1.1` to `2.2.2.2`, but it still resolves to the old IP

**Diagnostic Process**:
1. OpenAPI query: Record has been updated to `2.2.2.2`, TTL is 600 seconds
2. Recursive resolution comparison:
   - 223.5.5.5 → `2.2.2.2` (updated)
   - 8.8.8.8 → `1.1.1.1` (not yet updated)
   - 114.114.114.114 → `1.1.1.1` (not yet updated)
3. DNS probe: 40% of nodes show updated record, 60% still return old IP

**Diagnosis Conclusion**:
- Authoritative configuration has been correctly updated, but recursive DNS caches nationwide have not yet expired
- Current TTL=600 seconds; need to wait for recursive DNS caches in various regions to refresh

**Recommendations**:
1. This is normal DNS propagation delay; wait 10-30 minutes and check again
2. To speed up future changes, lower the TTL to 60 seconds before making modifications
3. Locally verify via `dig @223.5.5.5 www.example.com` that Alibaba Cloud DNS has been updated

---

## Case 4: PrivateZone Domain Cannot Be Resolved Inside VPC

**Problem Description**: `dig db.internal.com` from within an ECS instance returns NXDOMAIN

**Diagnostic Process**:
1. NS check: `internal.com` has no NS records on the public internet (normal — PrivateZone does not take effect on public DNS)
2. OpenAPI query for PrivateZone: Found Zone `internal.com`, record `db` → A `10.0.1.100`
3. Zone details: **Bound to VPC-A, but the ECS instance is in VPC-B**

**Diagnosis Conclusion**:
- PrivateZone is not bound to the VPC where the ECS instance resides, so resolution fails within that VPC

**Recommendations**:
1. In the PrivateZone console, bind the Zone to the VPC where the ECS instance resides
2. After binding, wait approximately 1 minute for it to take effect

---

## Case 5: GTM Scheduling Anomaly

**Problem Description**: GTM domain `api.example.com` resolves to an IP that does not match the expected regional scheduling policy

**Diagnostic Process**:
1. NS check: Domain CNAME points to the GTM-assigned domain
2. OpenAPI query for GTM instance: Instance is active and not expired
3. GTM access strategy: Configured with East China→IP-A, North China→IP-B regional scheduling
4. DNS probe: East China nodes correctly resolve to IP-A, but North China nodes also resolve to IP-A

**Diagnosis Conclusion**:
- GTM regional policy configuration may be incomplete; North China region is not properly configured
- Or the North China address pool health check has failed, triggering failover to the default pool

**Recommendations**:
1. Check the health check status of GTM address pools
2. Verify that the North China region access policy is fully configured
3. Check the priority settings of the default address pool

---

## Case 6: Third-Party DNS Resolution Failure

**Problem Description**: Domain `shop.example.com` cannot be resolved; domain is registered with Alibaba Cloud but uses Cloudflare DNS

**Diagnostic Process**:
1. NS check: NS points to `xxx.ns.cloudflare.com` (not Alibaba Cloud)
2. OpenAPI query: Domain is under the Alibaba Cloud account, but DNS servers have been changed to Cloudflare
3. dig comparison: All public DNS servers return NXDOMAIN
4. DNS probe: 100% of nodes fail to resolve

**Diagnosis Conclusion**:
- Domain NS has been pointed to Cloudflare, but Cloudflare may not have the DNS records configured properly
- Alibaba Cloud cannot control third-party DNS resolution configuration

**Recommendations**:
1. Log in to the Cloudflare dashboard and check the domain's DNS record configuration
2. To switch back to Alibaba Cloud DNS, change the NS records to Alibaba Cloud-assigned DNS servers at the domain registrar
3. After NS change, wait 24-48 hours for global propagation
