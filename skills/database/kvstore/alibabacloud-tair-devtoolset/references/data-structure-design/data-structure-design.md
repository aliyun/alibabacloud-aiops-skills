
## Data Structure Design

Choose the appropriate data structure based on your access patterns and business requirements. Redis provides foundational data types, while Tair extends them with enhanced structures for complex scenarios.

### Redis Data Structures

| Name | Use Case |
|------|----------|
| String | Caching, counters, distributed locks, session storage, rate limiting |
| Hash | Object storage (user profiles, product info), grouped field-value pairs |
| List | Message queues, latest feeds, task queues, stack/queue operations |
| Set | Unique collections, tagging, social graph (followers/friends), set operations (intersection, union) |
| Sorted Set | Leaderboards, ranking systems, priority queues, range queries by score |
| Stream | Event sourcing, log streaming, message queues with consumer groups, time-ordered events |
| Bitmap | Feature flags, online status tracking, daily active user counting, bit-level operations |
| Bitfield | Compact counters, fixed-width integer encoding, atomic increment with overflow policies |
| Geospatial | Location-based services, nearby search, geofencing, distance calculations |
| HyperLogLog | Unique visitor counting, cardinality estimation with minimal memory (0.81% error) |

### Tair Data Structures

| Name | Use Case |
|------|----------|
| exString (String enhancement) | Versioned strings, bounded INCRBY/INCRBYFLOAT with min/max limits, CAS/CAD for distributed locks and optimistic locking |
| exHash (Hash enhancement) | Field-level TTL expiration, field versioning, user multi-device login management, session with per-field expiry |
| exZset (Zset enhancement) | Multi-dimensional scoring (up to 256 dimensions), complex leaderboards, multi-criteria ranking |
| GIS (Geospatial enhancement) | Point/line/polygon queries, spatial relationship checks (contains, intersects), geofencing, location-based services |
| Doc (JSON) | JSON document storage with binary tree indexing, fast sub-element access, compatible with JSON standard |
| Search | Full-text search, ES-like query syntax, multi-column index, tokenization, real-time search for logs and content |
| TS (TimeSeries) | Real-time monitoring, IoT sensor data, stock tickers, two-level timeline aggregation, historical data updates |
| Bloom | Probabilistic membership testing, recommendation deduplication, crawler URL filtering, activity push management |
| Cpc | Compressed cardinality estimation, streaming analytics, rolling/sliding window aggregation, DISTINCT/COUNT/MAX/MIN |
| Roaring (Bitmap enhancement) | User segmentation, audience targeting, multi-bitmap operations, high-performance compressed bitmaps |
| Vector | Vector similarity search, LLM Chatbot, image/text multimodal retrieval, molecular structure search, HNSW indexing |

**Reference:**
- [Redis Data Types](https://redis.io/docs/latest/develop/data-types/)
- [Tair Extended Data Structures](https://help.aliyun.com/zh/redis/developer-reference/extended-data-structures-of-apsaradb-for-redis-enhanced-edition)
