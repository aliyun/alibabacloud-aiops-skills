# Configuration Reference (config.ini)

> Extracted from SKILL.md. Full field reference for every `config.ini` section.
> All examples use `<...>` placeholders. **In production, inject credentials via environment variables** and add `config.ini` to `.gitignore`. Supported environment variables are listed in the "Credential Security" section of SKILL.md.

## [metastore_db] — Hive Metastore DB (only needed for -d/-t input modes)

```ini
db_type = mysql              # mysql or postgres
host = <METASTORE_HOST>
port = 3306
user = <METASTORE_USER>
password = ${METASTORE_PASSWORD}   # recommended: read from env var
database = hivemeta
```

## [rclone_source_hdfs] — data source

```ini
name = source            # rclone remote name
type = hdfs              # source type: hdfs or s3/oss
# --- HDFS source (type=hdfs) ---
namenode = host:8020     # NameNode address
username = hadoop        # HDFS username
# --- S3/OSS source (type=s3) ---
# provider = Alibaba
# endpoint = oss-cn-hangzhou.aliyuncs.com
# access_key_id = YOUR_AK
# secret_access_key = YOUR_SK
# bucket = your-source-bucket
```

> **OSS-HDFS (DLS) note**: DLS data cannot be accessed via the S3 API; use `--direct-read` mode instead.

## [rclone_target_s3] — OSS target

```ini
name = target
provider = Alibaba
endpoint = oss-cn-hangzhou-internal.aliyuncs.com
access_key_id = ${OSS_AK}            # recommended: read from env var
secret_access_key = ${OSS_SK}        # recommended: read from env var
bucket = <YOUR_BUCKET>
```

## [rclone_options] — rclone parameters

```ini
copy_flags = -v --transfers 64 --checkers 64
bwlimit = 08:00,off 23:00,30M    # bandwidth-limit schedule
max_parallel = 4                   # max tables synced in parallel
```

## [spark_thrift] — Spark Thrift Server

```ini
host = <SPARK_GATEWAY_HOST>
port = 80
username = <SPARK_USER>
password = ${SPARK_PASSWORD}         # recommended: read from env var
database = default
auth = NONE
scheme = http
```
