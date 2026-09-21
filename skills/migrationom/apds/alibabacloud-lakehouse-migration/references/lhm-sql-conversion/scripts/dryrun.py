#!/usr/bin/env python3
"""
[评测工具] dryrun - 对目标 DB 执行 EXPLAIN，验证 SQL 语法

本文件是 atomic skill 暴露给 LLM 的 CLI 入口。
**底层严格依赖 scripts/client.py 中的 dryrun()**，
本文件只负责命令行参数解析、文件读取、JSON 输出与退出码，**不重复实现任何
target 适配逻辑**。新增/修改任何 target 行为请去改 client.py。

Usage:
    python3 scripts/dryrun.py --sql <file> --target <target>

支持 target（与 client.dryrun 完全一致）:
    odps / maxcompute / hologres / presto / trino / spark / clickhouse / redshift

Output:
    JSON: {"success": true|false, "error": "...", "error_line": "..."}
    exit code: 0=通过, 1=失败

Examples:
    python3 scripts/dryrun.py --sql current.sql --target spark
    python3 scripts/dryrun.py --sql current.sql --target maxcompute

Environment:
    SQLT_*  / ALIBABA_CLOUD_*  / HOLOGRES_*  / CK_*  / REDSHIFT_*  / SPARK_EMR_*
    见 client.py 中各 _*_cfg() 函数定义；亦可在 ~/.lhm/credentials.json 中集中配置。

    SQLT_DRYRUN_HEARTBEAT_SEC: 心跳间隔（秒），默认 30。设为 0 关闭心跳。
        作用：在 client.dryrun() 长时间轮询期间向 stderr 周期性输出，避免上游
        Bash tool runtime 因"无输出"判定超时把进程转后台、丢失 dryrun 结果。
        与方言无关，对 8 种 target 全部生效。

    SQLT_DRYRUN_EXPECTED_JOB_DIR: 期望的 job 输出目录绝对路径（例如 case_runner 注入的
        临时 .migration-state/<job_id>/）。一旦设置，--sql 必须在该目录下，
        否则 dryrun 拒绝执行并返回明确的路径越权指引（治理 claude 自己 mkdir/
        uuid 导致的路径错配、源 SDK 报 "config incomplete" 等假错）。与方言无关。
"""
import argparse
import json
import os
import sys
import threading
import time
import traceback


# 与 client.dryrun() 完全对齐的 target 列表（含别名）
_SUPPORTED_TARGETS = (
    "odps", "maxcompute",
    "hologres",
    "presto", "trino",
    "spark",
    "clickhouse",
    "redshift",
    "mysql",
    "sqlserver", "mssql", "t-sql",
    "bigquery", "bq",
)


def _import_client_dryrun():
    """动态导入 client.dryrun，避免依赖调用方 cwd / PYTHONPATH。"""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    from client import dryrun as _dryrun  # noqa: E402
    return _dryrun


def main() -> int:
    p = argparse.ArgumentParser(
        description="对目标 DB 执行 EXPLAIN（严格调用 client.dryrun，不重复实现 target 适配）",
    )
    p.add_argument("--sql", required=True, help="SQL 文件路径")
    p.add_argument("--target", required=True, choices=_SUPPORTED_TARGETS,
                   help="目标方言；与 client.dryrun 支持的 target 一致")
    args = p.parse_args()

    if not os.path.exists(args.sql):
        # 带上下一步指引，避免上游 LLM 反复在错误路径上踩坑
        hint = ("请确认： (1) 已 Write/生成该 SQL 文件后再调用 dryrun；"
                "(2) 路径同 case_runner 注入的 SQLT_DRYRUN_EXPECTED_JOB_DIR 一致（如设置）")
        print(json.dumps({"success": False,
                          "error": f"SQL 文件不存在: {args.sql}。{hint}",
                          "error_line": ""},
                         ensure_ascii=False))
        return 1

    # 路径越权预检（与方言无关）：若 case_runner 下发了期望的 job 目录，
    # --sql 必须在该目录下；避免 claude 自己 mkdir+uuid 后 Write 到 sidecar 配置覆盖不
    # 到的路径，进而踩到 SDK 报 "config incomplete" 类误导。
    expected_job_dir = os.environ.get("SQLT_DRYRUN_EXPECTED_JOB_DIR", "").strip()
    if expected_job_dir:
        try:
            sql_abs = os.path.realpath(args.sql)
            expected_abs = os.path.realpath(expected_job_dir)
        except OSError as e:
            sql_abs, expected_abs = args.sql, expected_job_dir
            _path_check_warn = str(e)
        else:
            _path_check_warn = ""
        # os.path.commonpath 跳过，用前缀匹配（严要求）
        if not sql_abs.startswith(expected_abs.rstrip(os.sep) + os.sep) and sql_abs != expected_abs:
            print(json.dumps({
                "success": False,
                "error": (
                    f"路径越权：--sql 必须在 SQLT_DRYRUN_EXPECTED_JOB_DIR 目录内。"
                    f"期望前缀={expected_abs}，实际={sql_abs}。"
                    f"请使用 $SQLT_DRYRUN_EXPECTED_JOB_DIR/result.sql。"
                ),
                "error_line": "",
            }, ensure_ascii=False))
            return 1

    with open(args.sql, encoding="utf-8") as f:
        sql = f.read().strip()
    if not sql:
        print(json.dumps({"success": False,
                          "error": "SQL 文件为空",
                          "error_line": ""},
                         ensure_ascii=False))
        return 1

    # 去掉末尾分号（client.dryrun 内部 EXPLAIN 拼接对分号敏感）
    if sql.rstrip().endswith(";"):
        sql = sql.rstrip().rstrip(";")

    # 心跳：避免上游 Bash tool runtime 因长时间无 stdout 输出判定超时转后台
    # （现象：上游收到 "Command running in background with ID: ..." 而非 dryrun 真实结果）
    # 间隔可通过 SQLT_DRYRUN_HEARTBEAT_SEC 环境变量调节；设为 0 关闭。与方言无关。
    try:
        heartbeat_sec = int(os.environ.get("SQLT_DRYRUN_HEARTBEAT_SEC", "30"))
    except ValueError:
        heartbeat_sec = 30
    _hb_stop = threading.Event()

    def _heartbeat():
        start = time.monotonic()
        while not _hb_stop.wait(heartbeat_sec):
            elapsed = int(time.monotonic() - start)
            # 写到 stderr 而非 stdout，避免污染最终 JSON 结果
            sys.stderr.write(f"[dryrun-heartbeat] target={args.target} elapsed={elapsed}s\n")
            sys.stderr.flush()

    hb_thread = None
    if heartbeat_sec > 0:
        hb_thread = threading.Thread(target=_heartbeat, name="dryrun-heartbeat", daemon=True)
        hb_thread.start()

    try:
        dryrun = _import_client_dryrun()
        result = dryrun(sql, args.target)
    except ImportError as e:
        # 缺依赖时给出明确指引，避免 LLM 误判为"语法报错"
        result = {
            "success": False,
            "error": f"DryRun 依赖缺失（请安装对应 target 的 SDK）: {e}",
            "error_line": "",
        }
    except Exception as e:  # noqa: BLE001
        result = {
            "success": False,
            "error": f"DryRun 执行异常: {e}\n{traceback.format_exc()}",
            "error_line": "",
        }
    finally:
        _hb_stop.set()
        if hb_thread is not None:
            hb_thread.join(timeout=1.0)

    # 兼容 client.dryrun 在某些分支返回 dict 缺 error_line 的情况
    result.setdefault("error_line", "")
    # 兜底归一化：失败必须带可分类的 error。若 success=false 但 error 为空，
    # 说明真实失败原因丢失（典型：上游 Bash runtime 超时把进程转后台、stdout/stderr
    # 被截断）。此时绝不能让下游把"空错误"误判成"连接错误"而降级 SKIP，
    # 统一打上明确的不可判定标记，下游须重跑而非降级。
    if not result.get("success") and not (result.get("error") or "").strip():
        result["error"] = ("DRYRUN_INCONCLUSIVE: dryrun 失败但未捕获到任何错误信息"
                           "（疑似进程超时被转后台/输出被截断）。请勿据此判定为连接错误，"
                           "应调大 timeout 并加 2>&1 重跑以获取真实 error。")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
