#!/usr/bin/env python3
"""
[评测工具] check_env - 检查目标端 DryRun 环境配置是否就绪

不读取、不打印任何明文密钥。仅检查配置字段是否非空。

配置来源与 client.py 保持一致：环境变量 > ~/.lhm/credentials.json。

Usage:
    python3 scripts/check_env.py --target spark

Output:
    JSON: {"ready": true|false, "target": "...", "missing": [...], "guide": "..."}
    exit code: 0=就绪, 1=未就绪
"""
import argparse
import json
import os
import sys

# ── 动态导入 client.py 中的配置解析函数 ──────────────────────────────────────
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

try:
    from client import _get, _spark_backend
except ImportError:
    # client.py 不可用时，退化为仅检查环境变量
    def _get(section, key, env_var, default=None):  # noqa: D401
        evs = [env_var] if isinstance(env_var, str) else list(env_var)
        for ev in evs:
            v = os.environ.get(ev)
            if v is not None and v != "":
                return v
        return default if default is not None else ""

    _spark_backend = lambda: "kyuubi"  # noqa: E731


# ── 目标端 → 配置需求映射 ────────────────────────────────────────────────────
# 每个目标端定义 required 字段列表，每个字段：
#   (config_section, config_key, [env_var_names])
# 字段值非空（来自 ~/.lhm/credentials.json 或任一环境变量）即视为已配置。
# 不读取实际值，仅检查 bool(value)。

_TARGET_MAP = {
    "odps": "maxcompute",
    "maxcompute": "maxcompute",
    "hologres": "hologres",
    "clickhouse": "clickhouse",
    "presto": "presto",
    "trino": "presto",
    "redshift": "redshift",
    "mysql": "mysql",
    "sqlserver": "sqlserver",
    "mssql": "sqlserver",
    "t-sql": "sqlserver",
    "bigquery": "bigquery",
    "bq": "bigquery",
    "starrocks": "starrocks",
    "hive": "hive",
    "impala": "impala",
}

# spark 单独处理（依赖 backend 选择）

_CONFIG_REQ = {
    "maxcompute": [
        ("maxcompute", "access_id",  ["SQLT_MC_ACCESS_ID", "SQLT_TEST_MAXCOMPUTE_ACCESS_ID", "testevalmc_ak"]),
        ("maxcompute", "access_key", ["SQLT_MC_ACCESS_KEY", "SQLT_TEST_MAXCOMPUTE_ACCESS_KEY", "testevalmc_sk"]),
        ("maxcompute", "project",    ["SQLT_MC_PROJECT", "SQLT_TEST_MAXCOMPUTE_PROJECT", "testevalmc_project"]),
    ],
    "hologres": [
        # endpoint 可以直接配置，也可以由 host+port 拼接
        ("hologres", "endpoint",    ["HOLOGRES_ENDPOINT"]),
        ("hologres", "host",        ["holotesthost"]),  # endpoint 的替代方案
        ("hologres", "port",        ["holotestport"]),
        ("hologres", "access_id",   ["HOLOGRES_ACCESS_ID", "holotestuser",
                                     "SQLT_SPARK_EMR_ACCESS_KEY_ID"]),
        ("hologres", "access_key",  ["HOLOGRES_ACCESS_KEY", "holotestpasswd",
                                     "SQLT_SPARK_EMR_ACCESS_KEY_SECRET"]),
        ("hologres", "db_name",     ["HOLOGRES_DB", "holotestdb"]),
    ],
    "clickhouse": [
        ("clickhouse", "host",     ["CK_HOST", "cktesthost"]),
        ("clickhouse", "user",     ["CK_USER", "cktestuser"]),
        ("clickhouse", "password", ["CK_PASSWORD", "cktestpasswd"]),
    ],
    "presto": [
        ("presto", "host", ["SQLT_PRESTO_HOST"]),
        ("presto", "port", ["SQLT_PRESTO_PORT"]),
        ("presto", "user", ["SQLT_PRESTO_USER"]),
    ],
    "redshift": [
        ("redshift", "workgroup", ["REDSHIFT_WORKGROUP"]),
    ],
    "mysql": [
        ("mysql", "host",     ["SQLT_TEST_MYSQL_HOST"]),
        ("mysql", "user",     ["SQLT_TEST_MYSQL_USER"]),
        ("mysql", "password", ["SQLT_TEST_MYSQL_PASSWORD"]),
        ("mysql", "database", ["SQLT_TEST_MYSQL_DATABASE"]),
    ],
    "sqlserver": [
        ("sqlserver", "host",     ["SQLT_TEST_SQLSERVER_HOST"]),
        ("sqlserver", "user",     ["SQLT_TEST_SQLSERVER_USER"]),
        ("sqlserver", "password", ["SQLT_TEST_SQLSERVER_PASSWORD"]),
        ("sqlserver", "database", ["SQLT_TEST_SQLSERVER_DATABASE"]),
    ],
    "bigquery": [
        ("bigquery", "credentials_file", ["GOOGLE_APPLICATION_CREDENTIALS"]),
        ("bigquery", "project",          ["SQLT_BIGQUERY_PROJECT", "BIGQUERY_PROJECT"]),
    ],
    "starrocks": [
        ("starrocks", "host",     ["SQLT_STARROCKS_HOST"]),
        ("starrocks", "user",     ["SQLT_STARROCKS_USER"]),
        ("starrocks", "password", ["SQLT_STARROCKS_PASSWORD"]),
        ("starrocks", "database", ["SQLT_STARROCKS_DB"]),
    ],
    "hive": [
        ("hive", "host",     ["SQLT_TEST_HIVE_HOST", "SQLT_HIVE_HOST"]),
        ("hive", "user",     ["SQLT_TEST_HIVE_USER", "SQLT_HIVE_USER"]),
        ("hive", "password", ["SQLT_TEST_HIVE_PASSWORD", "SQLT_HIVE_PASSWORD"]),
        ("hive", "database", ["SQLT_TEST_HIVE_DATABASE", "SQLT_HIVE_DB"]),
    ],
    "impala": [
        ("impala", "host",     ["SQLT_TEST_IMPALA_HOST", "SQLT_IMPALA_HOST"]),
        ("impala", "database", ["SQLT_TEST_IMPALA_DATABASE", "SQLT_IMPALA_DATABASE"]),
    ],
    "kyuubi": [
        ("kyuubi", "host",     ["SQLT_KYUUBI_HOST"]),
        ("kyuubi", "username", ["SQLT_KYUUBI_USERNAME"]),
        ("kyuubi", "password", ["SQLT_KYUUBI_PASSWORD"]),
    ],
}


def _check_field(section: str, key: str, env_vars: list) -> bool:
    """检查单个字段是否已配置（非空）。不读取实际值。

    复用 client._get 的解析顺序：环境变量 > ~/.lhm/credentials.json，
    与 dryrun.py 实际使用的连接配置保持一致。
    """
    val = _get(section, key, env_vars)
    return val is not None and str(val).strip() != ""


def _check_target(target: str) -> dict:
    """检查目标端配置是否就绪。"""
    # spark 特殊处理：依赖 backend 选择
    if target == "spark":
        backend = _spark_backend()
        if backend == "emr_serverless":
            req_key = "spark_emr"
        else:
            req_key = "kyuubi"
    else:
        req_key = _TARGET_MAP.get(target)
        if req_key is None:
            return {"ready": False, "target": target,
                    "missing": [],
                    "guide": f"不支持的目标端: {target}"}

    required = _CONFIG_REQ.get(req_key, [])
    missing = []
    for section, key, env_vars in required:
        if not _check_field(section, key, env_vars):
            missing.append(key)

    # hologres 特殊处理：endpoint 和 host+port 二选一
    if req_key == "hologres" and missing:
        # 如果 endpoint 缺失但 host+port 都有，也算 OK
        if "endpoint" in missing and "host" not in missing and "port" not in missing:
            missing.remove("endpoint")
        # 如果 endpoint 有但 host/port 缺失，那 host/port 不算缺失
        elif "endpoint" not in missing:
            missing = [m for m in missing if m not in ("host", "port")]

    ready = len(missing) == 0
    guide = "" if ready else _build_guide(target, missing)

    return {
        "ready": ready,
        "target": target,
        "missing": missing,
        "guide": guide,
    }


def _build_guide(target: str, missing: list) -> str:
    """构建配置指引文本。"""
    lines = [
        f"目标端 [{target}] 的 DryRun 环境配置不完整。",
        f"缺少以下配置项: {', '.join(missing)}",
        "",
        "配置方法（二选一）：",
        "",
        "方法一：配置文件（推荐）",
        "  1. mkdir -p ~/.lhm",
        "  2. cp ${SKILL_HOME}/scripts/config_template.json ~/.lhm/credentials.json",
        "  3. 编辑 ~/.lhm/credentials.json，在对应 section 中填入真实连接信息",
        "",
        "方法二：设置对应的环境变量（见 config_template.json 中各字段说明）",
        "",
        "配置完成后重新运行转换即可启用 DryRun 验证。",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(
        description="检查目标端 DryRun 环境配置是否就绪（不读取明文密钥）"
    )
    p.add_argument("--target", required=True,
                   help="目标方言（spark / maxcompute / hologres / clickhouse / ...）")
    args = p.parse_args()

    result = _check_target(args.target)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
