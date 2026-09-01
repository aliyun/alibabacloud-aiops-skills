# Config Templates

> **Password field notes**:
> - `SOURCE_PASSWORD` / `TARGET_PASSWORD` in the templates are placeholders; replace them with the real passwords when generating
> - If the password contains a `"` character, it must be escaped as `\"` (TOML escaping rule)
> - If the password contains a `\` character, it must be escaped as `\\`
> - When displayed in the conversation, the password is masked to the first 2 chars + `***`

## sync_reader template

[sync_reader]
cluster = false                    # whether the source is a cluster
address = "SOURCE_HOST:PORT"
username = ""                      # ACL username, leave empty if none
password = "SOURCE_PASSWORD"
tls = false
sync_rdb = true                    # whether to sync full data
sync_aof = true                    # whether to continuously sync incremental (false = exit after full)
prefer_replica = false             # true = read from replica, reduce load on the primary
try_diskless = false               # set to true when the source has repl-diskless-sync=yes enabled

[redis_writer]
cluster = false
address = "TARGET_HOST:PORT"
username = ""
password = "TARGET_PASSWORD"
tls = false
off_reply = false

[filter]
allow_key_prefix = []
block_key_prefix = []
allow_db = []
block_db = []
block_command = ["FLUSHALL", "FLUSHDB"]

[advanced]
dir = "data"
log_file = "shake.log"
log_level = "info"
log_interval = 5
rdb_restore_command_behavior = "rewrite"
pipeline_count_limit = 1024
target_redis_max_qps = 300000
empty_db_before_sync = false

## scan_reader template

[scan_reader]
cluster = false
address = "SOURCE_HOST:PORT"
username = ""
password = "SOURCE_PASSWORD"
tls = false
dbs = []
scan = true
ksn = false
count = 100

[redis_writer]
cluster = false
address = "TARGET_HOST:PORT"
username = ""
password = "TARGET_PASSWORD"
tls = false
off_reply = false

[filter]
allow_key_prefix = []
block_key_prefix = []
allow_db = []
block_db = []
block_command = ["FLUSHALL", "FLUSHDB"]

[advanced]
dir = "data"
log_file = "shake.log"
log_level = "info"
log_interval = 5
rdb_restore_command_behavior = "rewrite"
pipeline_count_limit = 1024
target_redis_max_qps = 300000

## rdb_reader template

[rdb_reader]
filepath = "/path/to/dump.rdb"

[redis_writer]
cluster = false
address = "TARGET_HOST:PORT"
username = ""
password = "TARGET_PASSWORD"
tls = false

[advanced]
dir = "data"
log_file = "shake.log"
log_level = "info"
rdb_restore_command_behavior = "rewrite"

## aof_reader template

[aof_reader]
filepath = "/path/to/appendonly.aof"
timestamp = 0

[redis_writer]
cluster = false
address = "TARGET_HOST:PORT"
username = ""
password = "TARGET_PASSWORD"
tls = false

[advanced]
dir = "data"
log_file = "shake.log"
log_level = "info"
