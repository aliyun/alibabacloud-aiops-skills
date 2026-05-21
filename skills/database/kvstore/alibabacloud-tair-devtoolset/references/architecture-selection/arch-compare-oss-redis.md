
## Tair vs Open Source Redis Comparison

Tair (Redis OSS-compatible) is fully compatible with Redis open source protocols, providing enhanced enterprise features.

### Tair vs Self-managed Redis

| Item | Tair | Self-managed Redis |
|------|------|-------------------|
| Security | VPC isolation, whitelists, custom accounts, TLS encryption, TDE, audit logs | Self-managed network security, no built-in auth, requires third-party SSL |
| Backup | Point-in-time recovery (data flashback) | Full data restoration only |
| O&M | 10+ metric groups, 5s monitoring, alert rules, large key analysis | Complex third-party tools required |
| Scaling | Elastic scaling, instant creation | Hardware procurement, manual node management |
| HA | Single-zone HA, zone-disaster recovery, independent central module | Sentinel mode, higher cost, potential split-brain issues |
| Memory | 100% available (overhead handled by Alibaba Cloud) | 25-40% reserved for DR/O&M |

### Tair Edition Selection Guide

| Series | Performance | Cost | Best For |
|--------|-------------|------|----------|
| Memory-optimized | 300% vs Redis OSS | ~117% | Performance-critical, mission-critical workloads |
| Persistent memory | 90% vs Redis OSS | ~70% | High persistence, cost-effective storage |
| Disk-based (ESSD/SSD) | 40-60% vs Redis OSS | 15-20% | Large storage, low access density, cost-primary |
| Redis Open-Source Edition | Baseline | 100% | Standard Redis use, migration scenarios |

### Tair Enterprise vs Redis Open-Source Edition

| Feature | Tair Enterprise | Redis Open-Source |
|---------|-----------------|-------------------|
| Extended data structures | exString, exHash, exZset, GIS, Bloom, Doc, TS, Cpc, Roaring, Search, Vector | Not supported |
| TDE (Transparent Data Encryption) | ✔️ | ❌ |
| Data flashback (PITR) | ✔️ | ❌ |
| Global Distributed Cache | ✔️ | ❌ |
| Proxy query cache | ✔️ | ❌ |
| Semi-synchronous mode | ✔️ | ❌ |
| Max connections per node | 30,000 | 10,000 |
| Single-key QPS | 450,000 | 140,000-160,000 |

### When to Use

**Use Tair Enterprise (Memory-optimized):**
- Ultra-high performance required (3x throughput)
- Need extended data structures (Vector, Search, etc.)
- Enterprise security (TDE, data flashback)

**Use Tair Enterprise (Persistent memory):**
- Cost-effective with high data persistence
- Command-level persistence without data loss

**Use Tair Enterprise (Disk-based):**
- Large storage needs (hundreds of TB)
- Low access density, cost-primary scenarios

**Use Redis Open-Source Edition:**
- Standard Redis workloads
- Migration from self-managed Redis
- Cost-sensitive with baseline performance needs

**References:**
- [Tair vs Self-managed Redis](https://www.alibabacloud.com/help/en/redis/product-overview/comparison-between-apsaradb-for-redis-and-self-managed-redis)
- [Tair Enterprise vs Redis Open-Source](https://www.alibabacloud.com/help/en/redis/product-overview/comparison-between-apsaradb-for-redis-enhanced-edition-and-apsaradb-for-redis-community-edition)
