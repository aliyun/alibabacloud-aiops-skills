#!/usr/bin/env python3
"""外部服务统一收口。所有工具脚本通过本模块访问外部依赖，便于统一替换实现。

当前实现：
  - dryrun                   : HTTP 直连目标 DB（PyODPS / prestodb / psycopg2 / clickhouse-connect / boto3 Data API）
  - execute_sql              : HTTP 直连目标 DB，返回结果行
  - get_odps / get_holo_connection / get_ck_client : 返回原生长连接对象，供评测层 DBExecutor 复用
  - get_table_schema         : HTTP 直连目标 DB（PyODPS / psycopg2）
  - save_skill_audit_record  : 通过 aliyun lhm 插件 save-skill-audit-record（API SaveSkillAuditRecord）
                               上报 SQL 转换审计记录（best-effort，失败不中断主流程）

DB 配置：优先读取环境变量，其次 ~/.lhm/credentials.json，最后硬编码默认值。
  配置文件：
    ~/.lhm/credentials.json（统一配置文件，包含所有 LHM 技能的配置）
  环境变量（同时支持规范命名与评测层 legacy 命名）：
    MaxCompute : SQLT_MC_ACCESS_ID / SQLT_MC_ACCESS_KEY / SQLT_MC_PROJECT / SQLT_MC_ENDPOINT
                 legacy: testevalmc_ak / testevalmc_sk / testevalmc_project / testevalmc_region
    Hologres   : HOLOGRES_ENDPOINT / HOLOGRES_ACCESS_ID / HOLOGRES_ACCESS_KEY / HOLOGRES_DB
                 legacy: holotesthost + holotestport / holotestuser / holotestpasswd / holotestdb
    ClickHouse : CK_HOST / CK_PORT / CK_USER / CK_PASSWORD / CK_DB
                 legacy: cktesthost / cktestport / cktestuser / cktestpasswd / cktestdb
    Redshift   : REDSHIFT_HOST / REDSHIFT_PORT / REDSHIFT_DB / REDSHIFT_USER / REDSHIFT_PASSWORD
    Presto     : 硬编码连接参数
    Spark      : 默认走 Kyuubi Gateway（杭州 EMR Serverless Spark, DLF/Paimon 场景）。

═══════════════════════════════════════════════════════════════════════════════
【Spark dryrun / execute 走 Kyuubi —— 部署必读】
═══════════════════════════════════════════════════════════════════════════════
target=spark 时，dryrun 与真实执行默认通过 **Kyuubi Gateway**（pyhive over HTTPS）
连接杭州 EMR Serverless Spark，而非旧的 EMR Serverless OpenAPI。
后端由 SQLT_SPARK_BACKEND 路由：
  - kyuubi（默认）       : _kyuubi_run() —— pyhive 直连 Kyuubi Gateway
  - emr_serverless       : _spark_emr_run() —— 旧 EMR OpenAPI，保留作 fallback

【环境变量（连接信息不入库，需在 ~/.lhm/credentials.json 中配置）】
  SQLT_SPARK_BACKEND          后端选择，'kyuubi'（默认）| 'emr_serverless'
  SQLT_KYUUBI_HOST            Kyuubi Gateway 公网域名
  SQLT_KYUUBI_PORT            端口（公网 443）
  SQLT_KYUUBI_SCHEME          协议（公网必须 https）
  SQLT_KYUUBI_USERNAME        登录用户名（DLF 场景非 Token 名，详见连接信息）
  SQLT_KYUUBI_PASSWORD        Token（仅供 Kyuubi 使用；勿与 SPARK_GATEWAY_PASSWORD 混用）
  SQLT_KYUUBI_DEFAULT_CATALOG 默认 catalog（如 paimon）
  SQLT_KYUUBI_DEFAULT_DATABASE 默认 database（可空）

⚠️ 凭证（PASSWORD/Token）禁止硬编码进本文件，亦不随 git 提交（.env.local 已 gitignore）。
   首次部署请向项目维护者索取连接信息，写入本地 .env.local；eval/start.sh 启动时
   会 `set -a; source .env.local` 自动注入所有子进程。缺少密码时 dryrun 会直接报
   "kyuubi config incomplete: need password"。
═══════════════════════════════════════════════════════════════════════════════
"""
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))

# ── JSON 配置读取 ─────────────────────────────────────────────────────────────

# 统一配置文件路径：~/.lhm/credentials.json
# 所有配置（包括 SQL 转换的数据库连接配置）都从此文件读取
_CREDENTIALS_PATH = Path.home() / ".lhm" / "credentials.json"
_cached_cfg: Optional[dict] = None


def _load_json() -> dict:
    """加载并缓存 ~/.lhm/credentials.json 配置文件。

    该文件包含所有 LHM 技能的配置，包括：
    - 阿里云凭证（AK/SK）
    - LHM 服务配置（endpoint、region_id）
    - SQL 转换的数据库连接配置（maxcompute、hologres、clickhouse 等）
    - 调度迁移的数据源名称等
    
    文件不存在时返回空 dict。
    """
    global _cached_cfg
    if _cached_cfg is not None:
        return _cached_cfg

    merged: dict = {}
    
    # 加载 credentials.json（统一配置文件）
    if _CREDENTIALS_PATH.is_file():
        try:
            with open(_CREDENTIALS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                merged = data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load %s: %s", _CREDENTIALS_PATH, e)
    
    _cached_cfg = merged
    return _cached_cfg


def _get(section: str, key: str, env_var, default: Any = None) -> Any:
    """优先级：环境变量 > ~/.lhm/credentials.json > 硬编码默认值。

    env_var 可以是单个字符串，或字符串列表（按顺序尝试，用于兼容 legacy 命名）。
    """
    env_vars = [env_var] if isinstance(env_var, str) else list(env_var)
    for ev in env_vars:
        v = os.environ.get(ev)
        if v is not None and v != "":
            return v
    cfg = _load_json()
    sec = cfg.get(section) if isinstance(cfg, dict) else None
    if isinstance(sec, dict):
        value = sec.get(key)
        if value is not None and value != "":
            return value
    if default is not None:
        return default
    return ""


# ── DB 配置（环境变量 → ~/.lhm/credentials.json → 默认值）────────────────────────

def get_mc_cfg() -> dict:
    """MaxCompute 连接参数。支持 SQLT_MC_* 和评测层 legacy testevalmc_* 命名。

    endpoint 无显式值时，尝试从 region（SQLT_MC_REGION / testevalmc_region / maxcompute.region）构造
    http://service.cn-{region}.maxcompute.aliyun.com/api。
    """
    endpoint = _get("maxcompute", "endpoint", ["SQLT_MC_ENDPOINT"])
    if not endpoint:
        region = _get("maxcompute", "region", ["SQLT_MC_REGION", "testevalmc_region"])
        if region:
            endpoint = f"http://service.cn-{region}.maxcompute.aliyun.com/api"
    return {
        "access_id":  _get("maxcompute", "access_id",  ["SQLT_MC_ACCESS_ID", "testevalmc_ak"]),
        "access_key": _get("maxcompute", "access_key", ["SQLT_MC_ACCESS_KEY", "testevalmc_sk"]),
        "project":    _get("maxcompute", "project",    ["SQLT_MC_PROJECT", "testevalmc_project"]),
        "end_point":  endpoint,
    }

def _holo_cfg() -> dict:
    """Hologres 连接参数。支持 HOLOGRES_* 和评测层 legacy holotest* 命名。

    endpoint 无显式值时，尝试用 holotesthost + holotestport 拼接。
    """
    endpoint = _get("hologres", "endpoint", ["HOLOGRES_ENDPOINT"])
    if not endpoint:
        host = os.environ.get("holotesthost", "")
        port = os.environ.get("holotestport", "")
        if host and port:
            endpoint = f"{host}:{port}"
    return {
        "end_point":  endpoint,
        "access_id":  _get("hologres", "access_id",  ["HOLOGRES_ACCESS_ID", "holotestuser"],
                           os.environ.get("SQLT_SPARK_EMR_ACCESS_KEY_ID", "")),
        "access_key": _get("hologres", "access_key", ["HOLOGRES_ACCESS_KEY", "holotestpasswd"],
                           os.environ.get("SQLT_SPARK_EMR_ACCESS_KEY_SECRET", "")),
        "db_name":    _get("hologres", "db_name",    ["HOLOGRES_DB", "holotestdb"]),
    }

def _ck_cfg() -> dict:
    """ClickHouse 连接参数。支持 CK_* 和评测层 legacy cktest* 命名。"""
    return {
        "host":     _get("clickhouse", "host",     ["CK_HOST", "cktesthost"]),
        "port":     int(_get("clickhouse", "port", ["CK_PORT", "cktestport"], 8123)),
        "user":     _get("clickhouse", "user",     ["CK_USER", "cktestuser"]),
        "password": _get("clickhouse", "password", ["CK_PASSWORD", "cktestpasswd"]),
        "database": _get("clickhouse", "database", ["CK_DB", "cktestdb"], "default"),
    }

def _redshift_cfg() -> dict:
    """Redshift Data API 参数，纯环境变量读取。"""
    return {
        "workgroup": os.environ.get("REDSHIFT_WORKGROUP", "default-workgroup"),
        "database":  os.environ.get("REDSHIFT_DB", "dev"),
        "region":    os.environ.get("REDSHIFT_REGION", "ap-southeast-1"),
    }


def _starrocks_cfg() -> dict:
    """StarRocks 连接参数。走 MySQL 协议（9030）。"""
    return {
        "host":     _get("starrocks", "host",     ["SQLT_STARROCKS_HOST"], "localhost"),
        "port":     int(_get("starrocks", "port", ["SQLT_STARROCKS_PORT"], 9030)),
        "user":     _get("starrocks", "user",     ["SQLT_STARROCKS_USER"], "root"),
        "password": _get("starrocks", "password", ["SQLT_STARROCKS_PASSWORD"], ""),
        "database": _get("starrocks", "database", ["SQLT_STARROCKS_DB"],   "db"),
    }


def _hive_cfg() -> dict:
    """Hive 连接参数。走 HiveServer2 Thrift 协议（默认 10000）。"""
    return {
        "host":     _get("hive", "host",     ["SQLT_TEST_HIVE_HOST", "SQLT_HIVE_HOST"], "localhost"),
        "port":     int(_get("hive", "port", ["SQLT_TEST_HIVE_PORT", "SQLT_HIVE_PORT"], 10000)),
        "username": _get("hive", "user",     ["SQLT_TEST_HIVE_USER", "SQLT_HIVE_USER"], "hive"),
        "password": _get("hive", "password", ["SQLT_TEST_HIVE_PASSWORD", "SQLT_HIVE_PASSWORD"], ""),
        "database": _get("hive", "database", ["SQLT_TEST_HIVE_DATABASE", "SQLT_HIVE_DB"], "default"),
        "auth":     _get("hive", "auth",     ["SQLT_TEST_HIVE_AUTH", "SQLT_HIVE_AUTH"], "NONE"),
    }


def _mysql_cfg() -> dict:
    """MySQL 连接参数。走 MySQL 协议（pymysql，默认 3306）。"""
    return {
        "host":     _get("mysql", "host",     ["SQLT_TEST_MYSQL_HOST"], "localhost"),
        "port":     int(_get("mysql", "port", ["SQLT_TEST_MYSQL_PORT"], 3306)),
        "user":     _get("mysql", "user",     ["SQLT_TEST_MYSQL_USER"], "root"),
        "password": _get("mysql", "password", ["SQLT_TEST_MYSQL_PASSWORD"], ""),
        "database": _get("mysql", "database", ["SQLT_TEST_MYSQL_DATABASE"], ""),
    }


def _sqlserver_cfg() -> dict:
    """SQL Server 连接参数。走 TDS 协议（pymssql，默认 1433）。"""
    return {
        "host":     _get("sqlserver", "host",     ["SQLT_TEST_SQLSERVER_HOST"], "localhost"),
        "port":     int(_get("sqlserver", "port", ["SQLT_TEST_SQLSERVER_PORT"], 1433)),
        "user":     _get("sqlserver", "user",     ["SQLT_TEST_SQLSERVER_USER"], "sa"),
        "password": _get("sqlserver", "password", ["SQLT_TEST_SQLSERVER_PASSWORD"], ""),
        "database": _get("sqlserver", "database", ["SQLT_TEST_SQLSERVER_DATABASE"], ""),
    }


def _bigquery_cfg() -> dict:
    """BigQuery 连接参数。走 google-cloud-bigquery SDK。

    认证方式（按优先级）：
      1. GOOGLE_APPLICATION_CREDENTIALS 环境变量指向 service account JSON 密钥文件
      2. ~/.lhm/credentials.json 中 bigquery.credentials_file 指定 JSON 密钥文件路径
      3. gcloud CLI 默认凭证（gcloud auth application-default login）
    """
    credentials_file = _get("bigquery", "credentials_file",
                            ["GOOGLE_APPLICATION_CREDENTIALS"], "")
    project = _get("bigquery", "project", ["SQLT_BIGQUERY_PROJECT", "BIGQUERY_PROJECT"], "")
    dataset = _get("bigquery", "dataset", ["SQLT_BIGQUERY_DATASET", "BIGQUERY_DATASET"], "")
    location = _get("bigquery", "location", ["SQLT_BIGQUERY_LOCATION", "BIGQUERY_LOCATION"], "US")
    return {
        "credentials_file": credentials_file,
        "project": project,
        "dataset": dataset,
        "location": location,
    }


# ── 原生连接构造器（供评测层长连接、dryrun、execute_sql 统一复用）─────────────────────────────

def get_odps():
    """返回 PyODPS ODPS 实例，配置来源与其他 client helpers 一致。"""
    from odps import ODPS
    p = get_mc_cfg()
    return ODPS(
        access_id=p["access_id"],
        secret_access_key=p["access_key"],
        project=p["project"],
        endpoint=p["end_point"],
    )


def get_holo_connection():
    """返回 psycopg2 Hologres 连接，用于评测层长连接场景（search_path / 事务维护等）。"""
    import psycopg2
    p = _holo_cfg()
    if not p["end_point"]:
        raise ValueError("Hologres endpoint 未配置（HOLOGRES_ENDPOINT / holotesthost+holotestport）")
    host, port = p["end_point"].rsplit(":", 1)
    return psycopg2.connect(
        host=host, port=int(port),
        user=p["access_id"], password=p["access_key"],
        dbname=p["db_name"],
    )


def get_ck_client():
    """返回 clickhouse_connect 客户端，用于评测层长连接场景（namespace、多条语句等）。"""
    import clickhouse_connect
    c = _ck_cfg()
    return clickhouse_connect.get_client(
        host=c["host"], port=c["port"],
        username=c["user"], password=c["password"],
        database=c["database"],
    )


def _redshift_execute_stmt(sql: str, wait: bool = True) -> dict:
    """通过 Redshift Data API 执行 SQL，返回 {status, records, columns, error}。"""
    import boto3, time
    c = _redshift_cfg()
    client = boto3.client("redshift-data", region_name=c["region"])
    resp = client.execute_statement(
        WorkgroupName=c["workgroup"],
        Database=c["database"],
        Sql=sql,
    )
    stmt_id = resp["Id"]
    if not wait:
        return {"stmt_id": stmt_id}
    # 轮询等待完成（最多 120 秒）
    for _ in range(120):
        time.sleep(1)
        desc = client.describe_statement(Id=stmt_id)
        status = desc["Status"]
        if status in ("FINISHED", "FAILED", "ABORTED"):
            break
    if status == "FINISHED":
        try:
            result = client.get_statement_result(Id=stmt_id)
            columns = [col["name"] for col in result.get("ColumnMetadata", [])]
            rows = []
            for rec in result.get("Records", []):
                row = []
                for field in rec:
                    # Data API 返回 {"longValue": x} / {"stringValue": x} / ...
                    val = None
                    for k, v in field.items():
                        if k != "isNull":
                            val = v
                            break
                    if field.get("isNull", False):
                        val = None
                    row.append(val)
                rows.append(row)
            return {"success": True, "columns": columns, "rows": rows, "error": ""}
        except client.exceptions.ResourceNotFoundException:
            # EXPLAIN 等无结果集的语句
            return {"success": True, "columns": [], "rows": [], "error": ""}
    else:
        err = desc.get("Error", f"Statement {status}")
        return {"success": False, "columns": [], "rows": [], "error": err}


# ═════════════════════════════════════════════════════════════════════════════
# DryRun 语法验证
# ═════════════════════════════════════════════════════════════════════════════

def _extract_error_line(sql: str, error_msg: str) -> str:
    m = re.search(r"[Pp]osition[：:]\s*(\d+)|位置[：:]\s*(\d+)", error_msg)
    if not m:
        return ""
    pos = int(m.group(1) or m.group(2)) - 1
    if pos < 0 or pos >= len(sql):
        return ""
    start = sql.rfind("\n", 0, pos) + 1
    end = sql.find("\n", pos)
    return sql[start:(end if end != -1 else len(sql))].strip()


def _dryrun_odps(sql: str) -> dict:
    """HTTP-based MaxCompute dryrun via PyODPS SDK (no JDBC/Java required).

    对齐评测框架 db_executor.execute_target() 的处理方式：
    1. 从 SQL 文本中提取 SET 语句，转为 PyODPS hints 字典参数
       （MaxCompute EXPLAIN 不支持 SET 语句，拼在 SQL 里会报 parse error）
    2. 注入标准 hints（odps.sql.type.system.odps2、odps.sql.hive.compatible 等）
    3. 使用脚本模式 EXPLAIN，支持 CTE + INSERT 多语句
    """
    import re as _re
    from odps import ODPS
    p = get_mc_cfg()
    o = ODPS(
        access_id=p["access_id"],
        secret_access_key=p["access_key"],
        project=p["project"],
        endpoint=p["end_point"],
    )
    # ── 提取 SET 语句 → hints 字典 ──────────────────────────────────
    # MaxCompute EXPLAIN 不支持 SET，必须从 SQL 体中剥离后通过 hints 参数注入。
    # 与 db_executor._MC_SQL_HINTS 对齐的标准 hints。
    hints = {
        "odps.sql.type.system.odps2": "true",
        "odps.sql.allow.cartesian": "true",
        "odps.sql.hive.compatible": "true",
    }
    # 逐行提取 SET key = value（支持大小写混合，去掉末尾分号）
    body_lines = []
    for line in sql.split("\n"):
        m = _re.match(r"^\s*(?:SET|set)\s+(\S+)\s*=\s*(.+?)\s*;?\s*$", line)
        if m:
            hints[m.group(1)] = m.group(2).rstrip(";").strip()
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    # 脚本模式 hints（与 db_executor.execute_target skip_source 分支对齐）
    hints["odps.sql.submit.mode"] = "script"
    hints["odps.sql.step.script.mode"] = "true"
    try:
        inst = o.run_sql("EXPLAIN " + body, hints=hints)
        inst.wait_for_success()
        return {"success": True, "error": ""}
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _dryrun_presto(sql: str) -> dict:
    """Presto dryrun：优先 prestodb 客户端，socket 不通时 fallback 到 curl。"""
    host = os.environ.get("SQLT_PRESTO_HOST") or "localhost"
    port = int(os.environ.get("SQLT_PRESTO_PORT") or 8889)
    user = os.environ.get("SQLT_PRESTO_USER") or "admin"
    catalog = os.environ.get("SQLT_PRESTO_CATALOG") or "hive"
    schema = os.environ.get("SQLT_PRESTO_SCHEMA") or "default"

    # 先尝试 prestodb 客户端
    try:
        import prestodb
        conn = prestodb.dbapi.connect(
            host=host, port=port, user=user,
            catalog=catalog, schema=schema,
            http_scheme="http",
        )
        try:
            cur = conn.cursor()
            cur.execute("EXPLAIN " + sql)
            cur.fetchall()
            return {"success": True, "error": ""}
        except Exception as e:
            msg = str(e)
            if "ConnectionError" in msg or "Bad file descriptor" in msg or "NewConnectionError" in msg:
                return _dryrun_presto_curl(sql, host, port, user, catalog, schema)
            return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}
        finally:
            conn.close()
    except ImportError:
        return _dryrun_presto_curl(sql, host, port, user, catalog, schema)
    except Exception as e:
        msg = str(e)
        if "ConnectionError" in msg or "Bad file descriptor" in msg:
            return _dryrun_presto_curl(sql, host, port, user, catalog, schema)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _dryrun_presto_curl(sql: str, host: str, port: int, user: str,
                        catalog: str, schema: str) -> dict:
    """通过 curl 子进程执行 Presto EXPLAIN，作为 prestodb 客户端的 fallback。"""
    import time
    base_url = f"http://{host}:{port}"
    explain_sql = "EXPLAIN " + sql

    # 1) 提交语句
    submit = subprocess.run(
        ["curl", "-s", "-w", "\n%{http_code}", "-X", "POST",
         f"{base_url}/v1/statement",
         "-H", f"X-Presto-User: {user}",
         "-H", f"X-Presto-Catalog: {catalog}",
         "-H", f"X-Presto-Schema: {schema}",
         "-d", explain_sql, "--max-time", "30"],
        capture_output=True, text=True,
    )
    if submit.returncode != 0:
        return {"success": False, "error": f"curl submit failed: {submit.stderr.strip()}", "error_line": ""}

    lines = submit.stdout.strip().rsplit("\n", 1)
    body_str = lines[0] if len(lines) == 2 else submit.stdout.strip()
    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        return {"success": False, "error": f"Invalid JSON from Presto: {body_str[:300]}", "error_line": ""}

    # 检查立即返回的错误
    if "error" in body and body["error"]:
        err_msg = body["error"].get("message", str(body["error"]))
        return {"success": False, "error": err_msg, "error_line": _extract_error_line(sql, err_msg)}

    # 2) 轮询 nextUri 直到完成
    next_uri = body.get("nextUri")
    for _ in range(60):
        if not next_uri:
            break
        time.sleep(0.5)
        poll = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-X", "GET", next_uri,
             "-H", f"X-Presto-User: {user}", "--max-time", "30"],
            capture_output=True, text=True,
        )
        if poll.returncode != 0:
            return {"success": False, "error": f"curl poll failed: {poll.stderr.strip()}", "error_line": ""}
        poll_lines = poll.stdout.strip().rsplit("\n", 1)
        poll_body_str = poll_lines[0] if len(poll_lines) == 2 else poll.stdout.strip()
        try:
            body = json.loads(poll_body_str)
        except json.JSONDecodeError:
            return {"success": False, "error": f"Invalid JSON: {poll_body_str[:300]}", "error_line": ""}
        if "error" in body and body["error"]:
            err_msg = body["error"].get("message", str(body["error"]))
            return {"success": False, "error": err_msg, "error_line": _extract_error_line(sql, err_msg)}
        next_uri = body.get("nextUri")

    state = body.get("stats", {}).get("state", "")
    if state == "FAILED":
        err_msg = body.get("error", {}).get("message", "Unknown Presto error")
        return {"success": False, "error": err_msg, "error_line": _extract_error_line(sql, err_msg)}

    return {"success": True, "error": ""}


def _dryrun_clickhouse(sql: str) -> dict:
    """ClickHouse dryrun via clickhouse-connect（HTTP 协议）。"""
    import clickhouse_connect
    c = _ck_cfg()
    try:
        client = clickhouse_connect.get_client(
            host=c["host"], port=c["port"],
            username=c["user"], password=c["password"],
            database=c["database"],
        )
        client.command("EXPLAIN SYNTAX " + sql)
        client.close()
        return {"success": True, "error": ""}
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _dryrun_hologres(sql: str) -> dict:
    import psycopg2
    p = _holo_cfg()
    host, port = p["end_point"].rsplit(":", 1)
    try:
        conn = psycopg2.connect(host=host, port=int(port),
                                user=p["access_id"], password=p["access_key"],
                                dbname=p["db_name"])
        conn.cursor().execute("EXPLAIN " + sql)
        conn.close()
        return {"success": True, "error": ""}
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _spark_backend() -> str:
    """返回当前 Spark 后端：'kyuubi'（默认） | 'emr_serverless'。

    用于 _dryrun_spark / _exec_spark 路由。可通过环境变量 SQLT_SPARK_BACKEND 切换。
    """
    return (os.environ.get("SQLT_SPARK_BACKEND") or "kyuubi").strip().lower()


def _kyuubi_cfg() -> dict:
    """Kyuubi Gateway（EMR Serverless Spark, DLF 场景）连接参数。

    优先级：环境变量 > ~/.lhm/credentials.json (kyuubi) > 公网 endpoint 默认值。
    凭证（password/token）禁止硬编码。
    """
    cfg = _load_json()
    ky_cfg = cfg.get("kyuubi", {}) if isinstance(cfg, dict) else {}
    return {
        "host":             os.environ.get("SQLT_KYUUBI_HOST") or ky_cfg.get("host") or "emr-spark-kyuubi-gateway-cn-hangzhou.aliyuncs.com",
        "port":         int(os.environ.get("SQLT_KYUUBI_PORT") or ky_cfg.get("port") or 443),
        "scheme":           os.environ.get("SQLT_KYUUBI_SCHEME") or ky_cfg.get("scheme") or "https",
        "username":         os.environ.get("SQLT_KYUUBI_USERNAME") or ky_cfg.get("username") or "user",
        "password":         os.environ.get("SQLT_KYUUBI_PASSWORD") or ky_cfg.get("password") or "",
        "default_catalog":  os.environ.get("SQLT_KYUUBI_DEFAULT_CATALOG") or ky_cfg.get("default_catalog") or "paimon",
        "default_database": os.environ.get("SQLT_KYUUBI_DEFAULT_DATABASE") or ky_cfg.get("default_database") or "",
    }


def _kyuubi_run(sql: str, fetch: bool = False, timeout_sec: int = 600) -> dict:
    """通过 Kyuubi Gateway 执行 SQL。

    参数：
      - sql: 单条 SQL（已去尾分号；调用方自行裁剪）
      - fetch: True=拉取结果行（SELECT/SHOW/EXPLAIN）；False=只看是否成功
      - timeout_sec: 单语句执行总超时

    返回：{success, error, columns, rows}。dryrun 路径忽略 columns/rows。
    """
    c = _kyuubi_cfg()
    if not c["password"]:
        return {"success": False, "error": "kyuubi config incomplete: need password (SQLT_KYUUBI_PASSWORD)", "columns": [], "rows": []}

    try:
        from pyhive import hive  # noqa: F401
    except ImportError as e:
        return {"success": False, "error": f"pyhive not installed: {e}", "columns": [], "rows": []}

    conn = None
    cur = None
    try:
        from pyhive import hive
        conn = hive.connect(
            host=c["host"],
            port=c["port"],
            scheme=c["scheme"],
            username=c["username"],
            password=c["password"],
        )
        cur = conn.cursor()
        # 切 catalog / database（Spark 单段 USE，禁用 USE CATALOG）
        if c["default_catalog"]:
            try:
                cur.execute(f"USE {c['default_catalog']}")
            except Exception:
                pass  # catalog 已是默认时忽略
        if c["default_database"]:
            try:
                cur.execute(f"USE {c['default_database']}")
            except Exception:
                pass
        cur.execute(sql)
        columns: list = []
        rows: list = []
        if fetch:
            try:
                desc = cur.description or []
                columns = [d[0] for d in desc]
                rows = [list(r) for r in cur.fetchall()]
            except Exception:
                # 非结果集语句（DDL 等）
                pass
        return {"success": True, "error": "", "columns": columns, "rows": rows}
    except Exception as e:
        return {"success": False, "error": str(e), "columns": [], "rows": []}
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def _spark_emr_cfg() -> dict:
    """EMR Serverless Spark 连接参数，dryrun 和 execute_sql 统一复用。

    优先级：环境变量 > ~/.lhm/credentials.json (spark_emr) > 仅 endpoint/region_id/database 有硬编码公共默认。
    凭证类配置（ak/sk/workspace_id/sql_compute_id）禁止硬编码。
    """
    cfg = _load_json()
    spark_cfg = cfg.get("spark_emr", {}) if isinstance(cfg, dict) else {}
    return {
        "ak_id":            os.environ.get("SQLT_SPARK_EMR_ACCESS_KEY_ID") or spark_cfg.get("access_key_id") or "",
        "ak_secret":        os.environ.get("SQLT_SPARK_EMR_ACCESS_KEY_SECRET") or spark_cfg.get("access_key_secret") or "",
        "endpoint":         os.environ.get("SQLT_SPARK_EMR_ENDPOINT") or spark_cfg.get("endpoint") or "emr-serverless-spark.cn-hangzhou.aliyuncs.com",
        "region_id":        os.environ.get("SQLT_SPARK_EMR_REGION_ID") or spark_cfg.get("region_id") or "cn-hangzhou",
        "workspace_id":     os.environ.get("SQLT_SPARK_EMR_WORKSPACE_ID") or spark_cfg.get("workspace_id") or "",
        "sql_compute_id":   os.environ.get("SQLT_SPARK_EMR_SQL_COMPUTE_ID") or spark_cfg.get("sql_compute_id") or "",
        "default_catalog":  os.environ.get("SQLT_SPARK_EMR_DEFAULT_CATALOG") or spark_cfg.get("default_catalog") or "",
        "default_database": os.environ.get("SQLT_SPARK_EMR_DEFAULT_DATABASE") or spark_cfg.get("default_database") or "default",
    }


def _spark_emr_run(sql: str, timeout_sec: int = 600) -> dict:
    """向 EMR Serverless Spark 提交 SQL 并轮询完成，dryrun/execute_sql 共用。

    返回：{"success": bool, "error": str, "state": str}。结果行由 EMR Serverless 写回存储
    （OSS等），SDK 并不直接返回行集；如需结果行对比请切换为其他后端。
    """
    import time
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig
    from alibabacloud_emr_serverless_spark20230808 import client as emr_client_mod, models as emr_models

    c = _spark_emr_cfg()
    if not all([c["ak_id"], c["ak_secret"], c["workspace_id"], c["sql_compute_id"]]):
        return {"success": False, "error": "spark_emr config incomplete: need access_key_id, access_key_secret, workspace_id, sql_compute_id", "state": ""}

    try:
        emr = emr_client_mod.Client(OpenApiConfig(
            access_key_id=c["ak_id"], access_key_secret=c["ak_secret"],
            endpoint=c["endpoint"], region_id=c["region_id"],
        ))
        req = emr_models.CreateSqlStatementRequest(
            code_content=sql,
            default_catalog=c["default_catalog"],
            default_database=c["default_database"],
            limit=100,
            sql_compute_id=c["sql_compute_id"],
            region_id=c["region_id"],
        )
        resp = emr.create_sql_statement(c["workspace_id"], req)
        statement_id = resp.body.data.statement_id

        # 轮询，最长 timeout_sec 秒；渐进式间隔避免短语句白等
        _POLL_SCHEDULE = [1, 1, 2, 2, 3]
        elapsed = 0
        poll_idx = 0
        while elapsed < timeout_sec:
            wait = _POLL_SCHEDULE[poll_idx] if poll_idx < len(_POLL_SCHEDULE) else 3
            time.sleep(wait)
            elapsed += wait
            poll_idx += 1
            get_req = emr_models.GetSqlStatementRequest(region_id=c["region_id"])
            get_resp = emr.get_sql_statement(c["workspace_id"], statement_id, get_req)
            data = get_resp.body.data
            if data.state == "available":
                return {"success": True, "error": "", "state": data.state,
                        "sql_outputs": data.sql_outputs or []}
            if data.state in ("error", "cancelled"):
                return {"success": False, "error": data.sql_error_message or "Unknown error", "state": data.state}
        return {"success": False, "error": f"Timeout waiting for EMR Spark result ({timeout_sec}s)", "state": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "state": ""}


def _split_statements(sql: str) -> list[str]:
    """将多语句 SQL 按分号拆分为单语句列表（跳过注释行和空段）。

    字符串感知：跳过单引号内的分号（如 SPLIT(col, '[;,|]')），避免把
    字符串字面量中的 ';' 误认为语句分隔符。支持 '' 转义引号。
    """
    # 字符串感知按 ';' 分割
    parts: list[str] = []
    current: list[str] = []
    in_string = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if in_string:
            if ch == "'" and i + 1 < len(sql) and sql[i + 1] == "'":
                current.append("''")
                i += 2
                continue
            elif ch == "'":
                in_string = False
        elif ch == "'":
            in_string = True
        elif ch == ';':
            parts.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    if current:
        parts.append("".join(current))

    stmts = []
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        # 跳过纯注释块（每行都是注释）
        lines = [l.strip() for l in stripped.splitlines()]
        if all(l == "" or l.startswith("--") for l in lines):
            continue
        stmts.append(part)
    return stmts


def _dryrun_spark(sql: str) -> dict:
    """Spark dryrun。默认走 Kyuubi Gateway（EXPLAIN）；可经 SQLT_SPARK_BACKEND=emr_serverless 切回 EMR API。

    Spark EXPLAIN 不支持多语句 SQL；检测到 ';' 时自动逐条验证。
    """
    backend = _spark_backend()

    # 多语句拆分：Spark EXPLAIN 仅支持单条 SQL
    stmts = _split_statements(sql)
    if len(stmts) > 1:
        for i, stmt in enumerate(stmts):
            stmt_clean = stmt.strip()
            # 去掉该语句末尾的分号（上游已去总尾分号，但拆分后中间语句仍可能带 ';'）
            while stmt_clean.rstrip().endswith(";"):
                stmt_clean = stmt_clean.rstrip().rstrip(";")
            if backend == "emr_serverless":
                r = _spark_emr_run("EXPLAIN " + stmt_clean, timeout_sec=600)
            else:
                r = _kyuubi_run("EXPLAIN " + stmt_clean, fetch=False, timeout_sec=600)
            if not r["success"]:
                return {"success": False, "error": r["error"], "error_line": _extract_error_line(sql, r["error"])}
        return {"success": True, "error": ""}

    # 单语句路径
    if backend == "emr_serverless":
        r = _spark_emr_run("EXPLAIN " + sql, timeout_sec=600)
        if r["success"]:
            return {"success": True, "error": ""}
        return {"success": False, "error": r["error"], "error_line": _extract_error_line(sql, r["error"])}
    # 默认 kyuubi
    r = _kyuubi_run("EXPLAIN " + sql, fetch=False, timeout_sec=600)
    if r["success"]:
        return {"success": True, "error": ""}
    return {"success": False, "error": r["error"], "error_line": _extract_error_line(sql, r["error"])}


def _dryrun_redshift(sql: str) -> dict:
    """Redshift dryrun via Data API (EXPLAIN)。"""
    result = _redshift_execute_stmt("EXPLAIN " + sql)
    if result["success"]:
        return {"success": True, "error": ""}
    return {"success": False, "error": result["error"], "error_line": _extract_error_line(sql, result["error"])}


def _dryrun_mysql(sql: str) -> dict:
    """MySQL dryrun via MySQL 协议 EXPLAIN。"""
    import pymysql
    c = _mysql_cfg()
    try:
        conn = pymysql.connect(
            host=c["host"], port=c["port"],
            user=c["user"], password=c["password"],
            database=c["database"], connect_timeout=10, read_timeout=60,
        )
        try:
            cur = conn.cursor()
            cur.execute("EXPLAIN " + sql)
            cur.fetchall()
            return {"success": True, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _dryrun_sqlserver(sql: str) -> dict:
    """SQL Server dryrun via TDS 协议（SET FMTONLY ON）。"""
    import pymssql
    c = _sqlserver_cfg()
    try:
        conn = pymssql.connect(
            server=c["host"], port=str(c["port"]),
            user=c["user"], password=c["password"],
            database=c["database"], timeout=60, login_timeout=10,
        )
        try:
            cur = conn.cursor()
            cur.execute("SET FMTONLY ON; " + sql + "; SET FMTONLY OFF;")
            cur.fetchall()
            return {"success": True, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _dryrun_starrocks(sql: str) -> dict:
    """StarRocks dryrun via MySQL 协议 EXPLAIN。"""
    import pymysql
    c = _starrocks_cfg()
    try:
        conn = pymysql.connect(
            host=c["host"], port=c["port"],
            user=c["user"], password=c["password"],
            database=c["database"], connect_timeout=10, read_timeout=60,
        )
        try:
            cur = conn.cursor()
            cur.execute("EXPLAIN " + sql)
            cur.fetchall()
            return {"success": True, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def _get_bigquery_client():
    """构造 BigQuery Client，支持 service account JSON、authorized_user JSON 或 gcloud 默认凭证。"""
    from google.cloud import bigquery as _bq
    c = _bigquery_cfg()
    kwargs = {}
    if c["project"]:
        kwargs["project"] = c["project"]
    if c["credentials_file"]:
        import json as _json
        with open(c["credentials_file"]) as _f:
            cred_data = _json.load(_f)
        cred_type = cred_data.get("type", "")
        if cred_type == "service_account":
            from google.oauth2 import service_account as _sa
            credentials = _sa.Credentials.from_service_account_file(
                c["credentials_file"],
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
            if not kwargs.get("project"):
                kwargs["project"] = credentials.project_id
        elif cred_type == "authorized_user":
            from google.oauth2 import credentials as _creds
            from google.auth.transport.requests import Request as _Request
            credentials = _creds.Credentials(
                token=None,
                refresh_token=cred_data["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=cred_data["client_id"],
                client_secret=cred_data["client_secret"],
            )
            credentials.refresh(_Request())
        else:
            raise ValueError(f"不支持的 BigQuery 凭证类型: {cred_type}")
        kwargs["credentials"] = credentials
    if c["location"]:
        kwargs["location"] = c["location"]
    return _bq.Client(**kwargs)


def _dryrun_bigquery(sql: str) -> dict:
    """BigQuery dryrun via google-cloud-bigquery dry_run 模式。"""
    from google.cloud import bigquery as _bq
    try:
        client = _get_bigquery_client()
        c = _bigquery_cfg()
        job_config = _bq.QueryJobConfig(dry_run=True, use_legacy_sql=False)
        if c["dataset"]:
            job_config.default_dataset = f"{client.project}.{c['dataset']}"
        client.query(sql, job_config=job_config)
        return {"success": True, "error": ""}
    except Exception as e:
        msg = str(e)
        return {"success": False, "error": msg, "error_line": _extract_error_line(sql, msg)}


def dryrun(sql: str, target: str) -> dict:
    """
    对目标库执行 EXPLAIN，返回 {"success": bool, "error": str, "error_line": str}。
    target: "odps" | "hologres" | "presto" | "trino" | "maxcompute" | "spark" | "clickhouse" | "redshift" | "mysql" | "sqlserver" | "bigquery"

    统一兑底（与方言无关）：不论各 _dryrun_* 在 import / 配置加载（_*_cfg()）/
    SDK 调用 任一阶段抛什么异常，都包装为带方言名前缀的 dict 返回，
    避免上游只看到 "Exit code 1" + 空 error 字段的沉默退出现象。对 8 种 target 一致生效。
    """
    try:
        if target in ("odps", "maxcompute"):
            return _dryrun_odps(sql)
        elif target == "hologres":
            return _dryrun_hologres(sql)
        elif target in ("presto", "trino"):
            return _dryrun_presto(sql)
        elif target == "spark":
            return _dryrun_spark(sql)
        elif target == "clickhouse":
            return _dryrun_clickhouse(sql)
        elif target == "redshift":
            return _dryrun_redshift(sql)
        elif target == "mysql":
            return _dryrun_mysql(sql)
        elif target in ("sqlserver", "mssql", "t-sql"):
            return _dryrun_sqlserver(sql)
        elif target in ("bigquery", "bq"):
            return _dryrun_bigquery(sql)
        else:
            raise ValueError(f"不支持的 target: {target}")
    except ImportError as e:
        return {"success": False,
                "error": f"[{target}] DryRun SDK 缺失: {e}",
                "error_line": ""}
    except Exception as e:  # noqa: BLE001
        import traceback as _tb
        msg = str(e) or e.__class__.__name__
        return {"success": False,
                "error": f"[{target}] DryRun 配置/执行异常: {msg}\n{_tb.format_exc()}",
                "error_line": ""}


# ═════════════════════════════════════════════════════════════════════════════
# SQL 真实执行（返回结果行，用于双端对比验证）
# ═════════════════════════════════════════════════════════════════════════════

def _normalize_value(v):
    """将结果值统一为可比较的 Python 基础类型。"""
    if v is None:
        return None
    from decimal import Decimal
    if isinstance(v, Decimal):
        # 去掉尾零，保留有效精度
        return float(v.normalize())
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    # datetime / date / time 等统一转字符串
    return str(v)


def _exec_odps(sql: str) -> dict:
    from odps import ODPS
    p = get_mc_cfg()
    o = ODPS(
        access_id=p["access_id"],
        secret_access_key=p["access_key"],
        project=p["project"],
        endpoint=p["end_point"],
    )
    # 使用脚本模式提交，确保 SET 语句和多语句 SQL 被正确解析
    # 与 eval/db/db_executor.py 中 execute_target 的行为对齐
    hints = {
        "odps.dynamic.partition.mode": "nonstrict",
        "odps.sql.allow.fullscan": "true",
        "odps.sql.type.system.odps2": "true",
        "odps.sql.allow.cartesian": "true",
        "odps.sql.hive.compatible": "true",
        "odps.namespace.schema": "true",
        "odps.sql.submit.mode": "script",
        "odps.sql.step.script.mode": "true",
    }
    try:
        inst = o.run_sql(sql, hints=hints)
        inst.wait_for_success()
        reader = inst.open_reader()
        columns = [col.name for col in reader._schema.columns]
        rows = []
        for record in reader:
            rows.append([_normalize_value(record[i]) for i in range(len(columns))])
        return {"success": True, "columns": columns, "rows": rows, "error": ""}
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_presto_curl(sql: str, host: str, port: int, user: str,
                      catalog: str, schema: str) -> dict:
    """通过 curl 真实执行 Presto SQL 并收集结果行，作为 prestodb 客户端的 fallback。"""
    import time
    base_url = f"http://{host}:{port}"

    submit = subprocess.run(
        ["curl", "-s", "-w", "\n%{http_code}", "-X", "POST",
         f"{base_url}/v1/statement",
         "-H", f"X-Presto-User: {user}",
         "-H", f"X-Presto-Catalog: {catalog}",
         "-H", f"X-Presto-Schema: {schema}",
         "-d", sql, "--max-time", "60"],
        capture_output=True, text=True,
    )
    if submit.returncode != 0:
        return {"success": False, "columns": [], "rows": [],
                "error": f"curl submit failed: {submit.stderr.strip()}"}

    lines = submit.stdout.strip().rsplit("\n", 1)
    body_str = lines[0] if len(lines) == 2 else submit.stdout.strip()
    try:
        body = json.loads(body_str)
    except json.JSONDecodeError:
        return {"success": False, "columns": [], "rows": [],
                "error": f"Invalid JSON from Presto: {body_str[:500]}"}

    if "error" in body and body["error"]:
        return {"success": False, "columns": [], "rows": [],
                "error": body["error"].get("message", str(body["error"]))}

    all_columns = []
    all_rows = []
    # 从首次响应中提取列和数据
    if "columns" in body:
        all_columns = [c["name"] for c in body["columns"]]
    if "data" in body:
        all_rows.extend(body["data"])

    next_uri = body.get("nextUri")
    for _ in range(120):
        if not next_uri:
            break
        time.sleep(0.3)
        poll = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-X", "GET", next_uri,
             "-H", f"X-Presto-User: {user}", "--max-time", "60"],
            capture_output=True, text=True,
        )
        if poll.returncode != 0:
            return {"success": False, "columns": all_columns, "rows": all_rows,
                    "error": f"curl poll failed: {poll.stderr.strip()}"}
        poll_lines = poll.stdout.strip().rsplit("\n", 1)
        poll_body_str = poll_lines[0] if len(poll_lines) == 2 else poll.stdout.strip()
        try:
            body = json.loads(poll_body_str)
        except json.JSONDecodeError:
            return {"success": False, "columns": all_columns, "rows": all_rows,
                    "error": f"Invalid JSON: {poll_body_str[:500]}"}
        if "error" in body and body["error"]:
            return {"success": False, "columns": all_columns, "rows": all_rows,
                    "error": body["error"].get("message", str(body["error"]))}
        if "columns" in body and not all_columns:
            all_columns = [c["name"] for c in body["columns"]]
        if "data" in body:
            all_rows.extend(body["data"])
        next_uri = body.get("nextUri")

    state = body.get("stats", {}).get("state", "")
    if state == "FAILED":
        return {"success": False, "columns": all_columns, "rows": all_rows,
                "error": body.get("error", {}).get("message", "Unknown Presto error")}

    rows = [[_normalize_value(v) for v in row] for row in all_rows]
    return {"success": True, "columns": all_columns, "rows": rows, "error": ""}


def _exec_presto(sql: str) -> dict:
    host = os.environ.get("SQLT_PRESTO_HOST") or "localhost"
    port = int(os.environ.get("SQLT_PRESTO_PORT") or 8889)
    user = os.environ.get("SQLT_PRESTO_USER") or "admin"
    catalog = os.environ.get("SQLT_PRESTO_CATALOG") or "hive"
    schema = os.environ.get("SQLT_PRESTO_SCHEMA") or "default"
    try:
        import prestodb
        conn = prestodb.dbapi.connect(
            host=host, port=port, user=user,
            catalog=catalog, schema=schema,
            http_scheme="http",
        )
        try:
            cur = conn.cursor()
            cur.execute(sql)
            raw_rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [[_normalize_value(v) for v in row] for row in raw_rows]
            return {"success": True, "columns": columns, "rows": rows, "error": ""}
        except Exception as e:
            msg = str(e)
            if "ConnectionError" in msg or "Bad file descriptor" in msg or "NewConnectionError" in msg:
                return _exec_presto_curl(sql, host, port, user, catalog, schema)
            return {"success": False, "columns": [], "rows": [], "error": msg}
        finally:
            conn.close()
    except ImportError:
        return _exec_presto_curl(sql, host, port, user, catalog, schema)
    except Exception as e:
        msg = str(e)
        if "ConnectionError" in msg or "Bad file descriptor" in msg:
            return _exec_presto_curl(sql, host, port, user, catalog, schema)
        return {"success": False, "columns": [], "rows": [], "error": msg}


def _exec_clickhouse(sql: str) -> dict:
    """ClickHouse 真实执行 via clickhouse-connect（HTTP 协议）。"""
    import clickhouse_connect
    c = _ck_cfg()
    try:
        client = clickhouse_connect.get_client(
            host=c["host"], port=c["port"],
            username=c["user"], password=c["password"],
            database=c["database"],
        )
        result = client.query(sql)
        columns = list(result.column_names)
        rows = [[_normalize_value(v) for v in row] for row in result.result_rows]
        client.close()
        return {"success": True, "columns": columns, "rows": rows, "error": ""}
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_hologres(sql: str) -> dict:
    import psycopg2
    p = _holo_cfg()
    host, port = p["end_point"].rsplit(":", 1)
    try:
        conn = psycopg2.connect(host=host, port=int(port),
                                user=p["access_id"], password=p["access_key"],
                                dbname=p["db_name"])
        cur = conn.cursor()
        cur.execute(sql)
        raw_rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [[_normalize_value(v) for v in row] for row in raw_rows]
        conn.close()
        return {"success": True, "columns": columns, "rows": rows, "error": ""}
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_spark(sql: str) -> dict:
    """Spark 真实执行。默认走 Kyuubi Gateway（pyhive 直接 fetchall）；可切回 EMR API。

    与 _dryrun_spark 共享后端和配置。
    """
    if _spark_backend() != "emr_serverless":
        r = _kyuubi_run(sql, fetch=True, timeout_sec=600)
        return {"success": r["success"], "columns": r.get("columns", []), "rows": r.get("rows", []), "error": r.get("error", "")}
    r = _spark_emr_run(sql, timeout_sec=600)
    if not r["success"]:
        return {"success": False, "columns": [], "rows": [], "error": r["error"]}

    # 解析 sql_outputs 中的 schema 和 rows
    columns = []
    rows = []
    sql_outputs = r.get("sql_outputs", [])
    if sql_outputs and hasattr(sql_outputs[0], "schema") and hasattr(sql_outputs[0], "rows"):
        output = sql_outputs[0]
        try:
            schema = json.loads(output.schema) if output.schema else {}
            columns = [f["name"] for f in schema.get("fields", [])]
        except (json.JSONDecodeError, KeyError):
            pass
        if output.rows:
            try:
                # rows 是单个 JSON 字符串，如 '[{"values":["14"]},{"values":["b"]}]'
                parsed_rows = json.loads(output.rows) if isinstance(output.rows, str) else output.rows
                if isinstance(parsed_rows, list):
                    for item in parsed_rows:
                        if isinstance(item, dict) and "values" in item:
                            rows.append(item["values"])
                        else:
                            rows.append([item])
            except (json.JSONDecodeError, TypeError):
                pass
    return {"success": True, "columns": columns, "rows": rows, "error": ""}


def _exec_redshift(sql: str) -> dict:
    """Redshift 真实执行 via Data API。"""
    return _redshift_execute_stmt(sql)


def _exec_starrocks(sql: str) -> dict:
    """StarRocks 真实执行 via MySQL 协议（pymysql）。"""
    import pymysql
    c = _starrocks_cfg()
    try:
        conn = pymysql.connect(
            host=c["host"], port=c["port"],
            user=c["user"], password=c["password"],
            database=c["database"], connect_timeout=10, read_timeout=120,
        )
        try:
            cur = conn.cursor()
            cur.execute(sql)
            raw_rows = cur.fetchall() if cur.description else []
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [[_normalize_value(v) for v in row] for row in raw_rows]
            return {"success": True, "columns": columns, "rows": rows, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_hive(sql: str) -> dict:
    """Hive 真实执行 via HiveServer2 (pyhive)。"""
    from pyhive import hive
    c = _hive_cfg()
    try:
        connect_kwargs = {
            "host": c["host"],
            "port": c["port"],
            "username": c["username"],
            "database": c["database"],
            "auth": c["auth"],
        }
        # NOSASL 模式不传 password，否则 pyhive 会报错
        if c["auth"] not in ("NOSASL", "NONE") and c.get("password"):
            connect_kwargs["password"] = c["password"]
        conn = hive.connect(**connect_kwargs)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            raw_rows = cur.fetchall() if cur.description else []
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [[_normalize_value(v) for v in row] for row in raw_rows]
            return {"success": True, "columns": columns, "rows": rows, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_mysql(sql: str, max_retries: int = 3, retry_delay: float = 2.0) -> dict:
    """MySQL 真实执行 via MySQL 协议（pymysql）。

    对连接超时类错误（Lost connection / Operation timed out / errno 2013）自动重试。
    """
    import time
    import pymysql
    c = _mysql_cfg()

    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            conn = pymysql.connect(
                host=c["host"], port=c["port"],
                user=c["user"], password=c["password"],
                database=c["database"], connect_timeout=10, read_timeout=120,
                autocommit=True,
            )
            try:
                cur = conn.cursor()
                cur.execute(sql)
                raw_rows = cur.fetchall() if cur.description else []
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = [[_normalize_value(v) for v in row] for row in raw_rows]
                return {"success": True, "columns": columns, "rows": rows, "error": ""}
            finally:
                conn.close()
        except Exception as e:
            last_error = str(e)
            error_str = last_error.lower()
            is_retryable = (
                "lost connection" in error_str
                or "operation timed out" in error_str
                or "errno 60" in error_str
                or "2013" in last_error
            )
            if is_retryable and attempt < max_retries:
                logger.warning(
                    "_exec_mysql: retryable error on attempt %d/%d: %s",
                    attempt, max_retries, last_error,
                )
                time.sleep(retry_delay * attempt)
                continue
            return {"success": False, "columns": [], "rows": [], "error": last_error}

    return {"success": False, "columns": [], "rows": [], "error": last_error}


def _exec_sqlserver(sql: str) -> dict:
    """SQL Server 真实执行 via TDS 协议（pymssql）。"""
    import pymssql
    c = _sqlserver_cfg()
    try:
        conn = pymssql.connect(
            server=c["host"], port=str(c["port"]),
            user=c["user"], password=c["password"],
            database=c["database"], timeout=120, login_timeout=10,
            autocommit=True,
        )
        try:
            cur = conn.cursor()
            cur.execute(sql)
            raw_rows = cur.fetchall() if cur.description else []
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = [[_normalize_value(v) for v in row] for row in raw_rows]
            return {"success": True, "columns": columns, "rows": rows, "error": ""}
        finally:
            conn.close()
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def _exec_bigquery(sql: str) -> dict:
    """BigQuery 真实执行 via google-cloud-bigquery SDK。"""
    try:
        client = _get_bigquery_client()
        c = _bigquery_cfg()
        from google.cloud import bigquery as _bq
        job_config = _bq.QueryJobConfig(use_legacy_sql=False)
        if c["dataset"]:
            job_config.default_dataset = f"{client.project}.{c['dataset']}"
        query_job = client.query(sql, job_config=job_config)
        result = query_job.result(timeout=120)
        columns = [field.name for field in result.schema]
        rows = [[_normalize_value(v) for v in row.values()] for row in result]
        return {"success": True, "columns": columns, "rows": rows, "error": ""}
    except Exception as e:
        return {"success": False, "columns": [], "rows": [], "error": str(e)}


def execute_sql(sql: str, dialect: str) -> dict:
    """
    真实执行 SQL 并返回结果行。
    返回: {"success": bool, "columns": [str], "rows": [[...]], "error": str}
    dialect: "odps" | "maxcompute" | "hologres" | "presto" | "trino" | "spark" | "clickhouse" | "redshift" | "starrocks" | "hive" | "mysql" | "sqlserver" | "bigquery"
    """
    if dialect in ("odps", "maxcompute"):
        return _exec_odps(sql)
    elif dialect == "hologres":
        return _exec_hologres(sql)
    elif dialect in ("presto", "trino"):
        return _exec_presto(sql)
    elif dialect == "spark":
        return _exec_spark(sql)
    elif dialect == "clickhouse":
        return _exec_clickhouse(sql)
    elif dialect == "redshift":
        return _exec_redshift(sql)
    elif dialect == "starrocks":
        return _exec_starrocks(sql)
    elif dialect == "hive":
        return _exec_hive(sql)
    elif dialect == "mysql":
        return _exec_mysql(sql)
    elif dialect in ("sqlserver", "mssql"):
        return _exec_sqlserver(sql)
    elif dialect in ("bigquery", "bq"):
        return _exec_bigquery(sql)
    else:
        raise ValueError(f"不支持的 dialect: {dialect}")


# ═════════════════════════════════════════════════════════════════════════════
# 表结构查询
# ═════════════════════════════════════════════════════════════════════════════

def _schema_odps(tables: list) -> dict:
    import jaydebeapi
    p = get_mc_cfg()
    url = (f"jdbc:odps:{p['end_point']}?project={p['project']}"
           f"&accessId={p['access_id']}&accessKey={p['access_key']}")
    conn = jaydebeapi.connect("com.aliyun.odps.jdbc.OdpsDriver", url, {})
    result = {}
    try:
        cur = conn.cursor()
        for tbl in tables:
            try:
                cur.execute(f"DESC {tbl}")
                result[tbl] = [{"column": r[0], "type": r[1]}
                               for r in cur.fetchall() if r[0]]
            except Exception as e:
                result[tbl] = {"error": str(e)}
    finally:
        conn.close()
    return result


def _schema_hologres(tables: list) -> dict:
    import psycopg2
    p = _holo_cfg()
    host, port = p["end_point"].rsplit(":", 1)
    conn = psycopg2.connect(host=host, port=int(port),
                            user=p["access_id"], password=p["access_key"],
                            dbname=p["db_name"])
    result = {}
    try:
        cur = conn.cursor()
        for tbl in tables:
            parts = tbl.split(".")
            schema, tname = (parts[0], parts[1]) if len(parts) == 2 else ("public", parts[0])
            try:
                cur.execute("""
                    SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod)
                    FROM pg_catalog.pg_attribute a
                    JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                    WHERE a.attnum > 0 AND NOT a.attisdropped
                      AND n.nspname = %s AND c.relname = %s
                    ORDER BY a.attnum
                """, (schema, tname))
                result[tbl] = [{"column": r[0], "type": r[1]} for r in cur.fetchall()]
            except Exception as e:
                result[tbl] = {"error": str(e)}
    finally:
        conn.close()
    return result


def get_table_schema(tables: list, target: str) -> dict:
    """
    查询目标库表结构，返回 {"table_name": [{"column": str, "type": str}, ...], ...}。
    target: "odps" | "hologres"
    """
    if target == "odps":
        return _schema_odps(tables)
    elif target == "hologres":
        return _schema_hologres(tables)
    else:
        raise ValueError(f"不支持的 target: {target}")


# ═════════════════════════════════════════════════════════════════════════════
# 审计记录保存（SQL 转换技能）
#
# 统一通过 aliyun CLI 的 lhm 插件 `save-skill-audit-record`（API SaveSkillAuditRecord）
# 上报，复用 lookup_rules.py 的 endpoint/region/UA/凭证前置检查等请求实现。
# ═════════════════════════════════════════════════════════════════════════════

def _load_rules_backend():
    """惰性导入同目录的 lookup_rules，复用其 endpoint/region/UA 与请求通道实现。

    client.py 可能被从任意工作目录导入，这里显式把脚本目录加入 sys.path 兜底。
    """
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import lookup_rules  # noqa: E402  同目录脚本
    return lookup_rules


def save_skill_audit_record(
    source_dialect: str,
    target_dialect: str,
    source_sql_script: str,
    dry_run_status: str = "",
    script_transform_result: str = "",
    script_transform_status: str = "",
    skill: str = "",
    batch_id: str = "",
    record_type: str = "",
    ext_info: str = "",
) -> dict:
    """保存 SQL 转换技能审计记录（best-effort，绝不中断主流程）。

    通过 aliyun CLI 的 lhm 插件 `save-skill-audit-record` 上报（API SaveSkillAuditRecord）。

    参数：
      - source_dialect / target_dialect / source_sql_script：源方言、目标方言、源 SQL（必填）
      - dry_run_status：DryRun 状态，success|failed|skipped
      - script_transform_result：转换结果脚本
      - script_transform_status：转换状态，success|failed
      - skill：技能名，写入审计记录的 recordType（当 record_type 为空时生效）
      - batch_id：批次 ID（批量转换时传入）
      - record_type：记录类型；显式传入时优先于 skill
      - ext_info：扩展信息（JSON 字符串）

    返回：{"success": True, "data": <服务端响应>} 或 {"success": False, "error": <原因>}。
    审计属副作用操作：任何失败（CLI/插件/凭证缺失、网络错误、服务端拒绝）都只记
    warning 并返回失败态，不抛异常、不 sys.exit，避免影响已完成的转换结果与后续汇总。
    """
    rules = _load_rules_backend()

    effective_record_type = record_type or skill

    # aliyun lhm 插件参数名用 kebab-case（映射到 API SaveSkillAuditRecord）
    params = {
        "source-dialect": source_dialect,
        "target-dialect": target_dialect,
        "source-sql-script": source_sql_script,
    }
    # 可选字段：仅填充非空值
    for key, val in [
        ("dry-run-status", dry_run_status),
        ("script-transform-result", script_transform_result),
        ("script-transform-status", script_transform_status),
        ("record-type", effective_record_type),
        ("batch-id", batch_id),
        ("ext-info", ext_info),
    ]:
        if val:
            params[key] = val

    try:
        data = rules._aliyun_call("save-skill-audit-record", params)
        return {"success": True, "data": data}
    except (SystemExit, Exception) as e:  # noqa: BLE001  审计失败不得中断主流程
        logger.warning("save_skill_audit_record 失败（已忽略，不影响转换结果）: %s", e)
        return {"success": False, "error": str(e)}