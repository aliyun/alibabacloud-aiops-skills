## Errors Troubleshooting

Common errors when connecting to and using Tair, with causes and solutions.

> **Reference:** [Common errors and troubleshooting](https://www.alibabacloud.com/help/en/redis/support/common-errors-and-troubleshooting)

### Authentication Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NOAUTH Authentication required` | Password not provided or incorrect | Use correct account and password. Default account: password only. Custom account: `<user>:<password>`. **Note:** If using Lettuce 6.4.0–6.4.1, this error may occur even with correct password due to CLIENT SETINFO support. Upgrade to Lettuce 6.4.2+ or Spring Data Redis 3.4.2+ |
| `WRONGPASS invalid username-password pair` | Wrong password | Verify credentials. If using Sentinel mode, see Sentinel compatibility connection guide |
| `ERR invalid password` | Wrong password | Check credentials. In DMS, update saved password if changed — right-click the instance, choose Edit, and enter the new password |

### Connection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ERR illegal address` | Client IP not in whitelist | Add client IP to instance whitelist |
| `ERR sentinel compatibility mode is disabled` | Sentinel-compatible mode not enabled | Enable Sentinel-compatible mode in the console |
| `ERR max number of clients reached` | Connection limit exceeded | Check for connection leaks (e.g., missing `close()` after JedisPool), terminate abnormal sessions, or upgrade instance |
| `Connection reset by peer` | Client buffer exception | Check application code or adjust client buffer size |
| `UnknownHostException` or `failed to connect: xxx.redis.rds.aliyuncs.com could not be resolved` | DNS resolution failure | Set correct DNS server address |
| `ERR must use ssl connection in ssl port` | Connecting to TLS port without TLS | Enable TLS in client configuration |
| `NOWRITE You can't write against a non-write redis` | Read-only instance during failover/upgrade | Wait for operation to complete |

### Cluster Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `CROSSSLOT Keys in request don't hash to the same slot` | Multi-key command across different slots in direct connection mode | 1) Use `CLUSTER KEYSLOT` to verify keys are in the same slot; 2) Use Hash Tags `{tag}` to group keys in same slot (avoid data skew); 3) Switch to proxy mode which supports cross-slot multi-key commands |
| `ERR READONLY you can't write against a read only instance` | Writing to a replica node, or instance is in failover/configuration change | Connect to the primary node or wait for failover/upgrade to complete |
| `MOVED 3999 10.0.0.1:6379` | Key moved to another node in cluster | Use cluster-aware client (e.g., JedisCluster, RedisCluster) that handles redirection automatically |
| `Failed to connect to any host resolved for DNS name` | DNS resolution failure for cluster nodes | Check DNS server configuration and network connectivity |

### Memory and Command Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `OOM command not allowed when used memory > 'maxmemory'` | Memory usage exceeded maxmemory limit | If total memory at 100%, upgrade instance. If only a single shard is at 100%, check for big keys using offline key analysis or instance diagnostics |
| `WRONGTYPE Operation against a key holding the wrong kind of value` | Wrong command for data type (e.g., HASH command on String key) | Fix command to match the actual data type |
| `ERR unknown command 'xxx'` | Command not supported by instance version | Check command support list, upgrade minor version, or switch to direct connection mode (e.g., WAIT command requires direct mode) |
| `ERR command 'xxx' not support for your account` | Command disabled by security policy | Remove command from `#no_loose_disabled-commands` parameter if needed |
| `NOPERM this user has no permissions to run the 'xxx'` | Permission denied for command | Check user permissions or remove from `#no_loose_disabled-commands` list |
| `ERR FLUSHDB is not allowed in migrating mode` | FLUSHDB/FLUSHALL disabled during cluster shard scaling | Wait until shard scaling operation completes |

### redis-cli Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection reset by peer` | Client buffer exception causing connection close | Check application code or adjust client buffer size |
| `ERR must use ssl connection in ssl port` | Connecting to TLS port without TLS in redis-cli | Use `--tls` flag: `redis-cli -h host -p port --tls -a password` |

### Proxy Mode Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ERR client ip is not in whitelist` | Client IP not in proxy whitelist (different from instance whitelist) | Add client IP to proxy whitelist in console |
| `NOWRITE You can't write against a non-write redis` | Read-only instance during failover/upgrade | Wait for operation to complete |
| `ERR syntax error` | Command syntax error in proxy mode | Check command syntax; some commands have different syntax in proxy mode |
| `ERR no such db node` | Requested database node does not exist | Check if the data shard or node is available; may occur during scaling |
| `ERR 'xxx' command keys must in same slot` | Multi-key command across slots in proxy mode | Use Hash Tags `{tag}` to group keys, or restructure data model |
| `ERR for redis cluster, eval/evalsha number of keys can't be negative or zero` | EVAL/EVALSHA called without specifying key count | Ensure the NUMKEYS parameter is a positive integer when calling EVAL/EVALSHA |
| `ERR redis temporary failure` | Sub-instance timeout, network jitter, failover, or slow query | Check slow queries, monitor failover events, verify connection limits |
| `ERR redis temporary failure (ErrorCode 7002)` | Proxy internal error | Check instance status, retry after brief wait |
| `ERR request refused, too many pending request, now count xxx, beyond threshold xxx` | Request queue overflow on proxy | Reduce concurrent requests, optimize slow queries, or upgrade instance |

### Lua Scripts and Transaction Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NOSCRIPT No matching script. Please use EVAL.` | Script SHA not found in script cache | Use EVAL instead of EVALSHA, or call SCRIPT LOAD first to cache the script |
| `BUSY Redis is busy running a script. You can only call SCRIPT KILL or SHUTDOWN NOSAVE.` | Long-running Lua script blocking the instance | Call `SCRIPT KILL` to terminate the script. If the script has already executed write commands, use `SHUTDOWN NOSAVE` (with caution) |
| `ERR command eval not support for normal user` | EVAL/EVALSHA not available for the current account | Remove EVAL/EVALSHA from `#no_loose_disabled-commands`, or use an account with permission |
| `ERR eval/evalsha command keys must be in same slot` | Keys referenced in Lua script span different slots in cluster | Use Hash Tags `{tag}` to ensure all keys map to the same slot |
| `ERR bad lua script for redis cluster, all the keys that the script uses should be passed using the KEYS array` | Lua script in cluster mode does not pass keys via KEYS array | Refactor script to pass all keys via the KEYS array parameter, not hardcoded in the script body |
| `EXECABORT Transaction discarded because of previous errors` | A command in the transaction queue failed | Check the error for the specific command that caused the failure and fix it |
| `UNKILLABLE Sorry the script already executed write commands against the dataset.` | Cannot kill a script that has already performed writes | Wait for the script to complete, or use `SHUTDOWN NOSAVE` on a replica (with extreme caution) |
| `UNKILLABLE The busy script was sent by a master instance in the context of replication and cannot be killed.` | Script from master during replication cannot be killed on replica | Wait for the master's script to complete; it will propagate through replication |
| `NOTBUSY No scripts in execution right now.` | Called SCRIPT KILL when no script is running | No action needed — this is informational |

### Jedis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Could not get a resource from the pool` | Connection pool exhausted or instance unreachable | Check connection pool config (maxTotal, maxIdle), verify instance is accessible, check for connection leaks |
| `java.net.SocketTimeoutException: connect timed out` | Connection establishment timeout | Check network connectivity, increase connection timeout, verify whitelist and endpoint |
| `java.net.SocketTimeoutException: Read timed out` | Read operation timeout | Increase read timeout, check for slow queries on the instance |
| `No reachable node in cluster` | All cluster nodes unreachable | Check cluster status, verify endpoint and port, check network connectivity |
| `Caused by: java.lang.NumberFormatException: For input string: "6379@13028"` | Jedis version incompatible with cluster topology info format | Upgrade Jedis to latest version (3.x+) |
| `No more cluster attempts left` | All cluster redirect attempts exhausted | Check cluster health, verify nodes are accessible, increase max attempts config |
| `Unexpected end of stream` | Client buffer too small or connection closed by server | Increase timeout and buffer size, check for idle connection eviction |
| `java.lang.Long cannot be cast to java.util.List` | Jedis version incompatible with server response format | Upgrade Jedis to latest version |
| `Broken pipe (Write failed)` | Writing to a closed connection | Enable connection validation (testOnBorrow), adjust idle timeout, check for server-side connection eviction |
| `No way to dispatch this command to Redis Cluster because keys have different slots` | Multi-key command across slots in cluster mode | Use Hash Tags `{tag}` to group keys, or switch to proxy mode |

### Lettuce Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection to xxx not allowed. This Partition is not known in the cluster view.` | Cluster topology not refreshed after node change | Enable periodic cluster topology refresh: `ClusterTopologyRefreshOptions.builder().enablePeriodicRefresh(true)` |
| `io.lettuce.core.RedisConnectionException: Unable to connect xxx` | Connection refused or unreachable | Check network, whitelist, endpoint, and instance status |
| `java.nio.channels.UnresolvedAddressException` | DNS resolution failure | Set correct DNS server address, or use IP address instead of hostname |
| `ERR Unknown sentinel subcommand 'master'` | Sentinel-compatible mode not enabled | Enable Sentinel-compatible mode in the console |
| `NOAUTH` with correct password (Lettuce 6.4.0–6.4.1) | Lettuce CLIENT SETINFO bug | Upgrade to Lettuce 6.4.2+ or Spring Data Redis 3.4.2+. Alternatively, switch to RESP2 protocol |
| RESP3 `unknown command` error | Some Tair instance versions do not support RESP3 protocol | Switch to RESP2 protocol in Lettuce client configuration |

### Redisson Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `org.redisson.client.RedisConnectionException: Unable to connect to Redis server xxx` | Connection refused or unreachable | Check network, whitelist, endpoint, and instance status |
| `No enum constant org.redisson.cluster.ClusterNodeInfo.Flag.NOFAILOVER` | Redisson version incompatible with cluster node info format | Upgrade Redisson to latest version (3.x+) |

### Spring Data Redis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `NOPERM this user has no permissions to run the 'config|get' command` | Spring Data Redis tries to execute CONFIG command which is disabled | Grant CONFIG permission, or remove `config` from `#no_loose_disabled-commands`, or disable the health check that calls CONFIG |

### StackExchange.Redis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Multiple databases are not supported on this server; cannot switch to database` | Tair cluster mode only supports database 0 | Remove `AllowAdmin` flag, do not switch databases, ensure only database 0 is used |

### Predis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Error while reading line from the server.` | Read timeout or connection closed by server | Increase timeout, check for slow queries, verify network stability |

### phpredis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Cannot assign requested address` | Local port exhaustion (too many short-lived connections) | Enable persistent connections, increase local port range, or use connection pooling |
| `redis protocol error, got ' ' as reply type byte` | Protocol mismatch or dirty connection | Check for RESP2/RESP3 compatibility, ensure no stale data on connection, reconnect |
| `php_network_getaddresses: getaddrinfo failed: Temporary failure in name resolution` | DNS resolution failure | Set correct DNS server address, or use IP address instead of hostname |

### Go-redis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `panic: got 4 elements in cluster info address, expected 2 or 3` | go-redis version incompatible with Tair cluster info format | Upgrade go-redis to latest version (v9+) |

### node-redis Client Errors

| Error | Cause | Solution |
|-------|-------|----------|
| SCAN command enters infinite loop or returns empty data | Tair proxy mode may return cursor values that node-redis cannot handle properly | Use direct connection mode for SCAN operations, or handle cursor values manually in the application |
