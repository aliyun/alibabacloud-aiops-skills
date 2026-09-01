# Reader Mode Details

## Decision flow

Is the source a local file?
- Yes -> .rdb file -> rdb_reader; .aof file -> aof_reader
- No -> Does the source support PSYNC (has replication permission)?
  - Supported (self-hosted Redis) -> sync_reader
    - Full + continuous incremental -> sync_rdb=true, sync_aof=true
    - Full only, then exit -> sync_rdb=true, sync_aof=false
    - Incremental only -> sync_rdb=false, sync_aof=true
    - Offload the primary -> prefer_replica=true
  - Not supported (managed cloud) -> scan_reader
    - One-time full -> ksn=false (exits automatically when done)
    - Continuous incremental sync -> ksn=true (requires notify-keyspace-events enabled on the source)

## sync_reader

Applicable: self-hosted Redis (2.8+) with primary-replica replication permission, needing zero-downtime migration
How it works: pretends to be a replica, first pulls the full RDB, then continuously receives the AOF incremental command stream
Not applicable: managed cloud instances such as Alibaba Cloud Tair, AWS ElastiCache (PSYNC disabled)

Key parameters:
- sync_rdb = true  - perform the full stage
- sync_aof = true  - continuously sync incremental (false = exit after full completes)
- prefer_replica = true - read from a replica, reducing load on the primary
- try_diskless = true   - use when the source has repl-diskless-sync=yes enabled

## scan_reader

Applicable: managed cloud Redis or instances without replication permission
How it works: SCAN traverses all keys, DUMP+RESTORE writes to the target

Key parameters:
- dbs = []     - specify DBs to scan, empty = all, e.g., [0, 1]
- count = 100  - number of keys per SCAN, can be increased to speed up
- ksn = false  - whether to enable incremental listening

ksn = true incremental mode:
- After the full SCAN, subscribe to Keyspace Notifications to listen for source changes
- Requires notify-keyspace-events enabled on the source (KEA recommended); cloud instances must enable it in the console
- Based on event notifications; in extreme cases events may be missed, so consistency is weaker than sync_reader

ksn mode comparison:

| Dimension | ksn=false | ksn=true |
|-----------|-----------|----------|
| Applicable | one-time full migration | needs continuous incremental sync |
| After done | exits automatically | continuously runs, listening for changes |
| Consistency | point-in-time snapshot | near real-time, may miss events in extreme cases |
| Source requirement | no special requirement | requires notify-keyspace-events enabled |

## rdb_reader

Applicable: restore from an RDB backup, or offline migration where the source is already down
Parameter: filepath = "/data/redis/dump.rdb"
Note: full import only, no incremental capability, exits automatically when done

## aof_reader

Applicable: point-in-time restore, or replaying historical Redis operations
Parameters:
- filepath  - AOF file path
- timestamp - replay only commands after this timestamp (0 = all, Unix timestamp)
