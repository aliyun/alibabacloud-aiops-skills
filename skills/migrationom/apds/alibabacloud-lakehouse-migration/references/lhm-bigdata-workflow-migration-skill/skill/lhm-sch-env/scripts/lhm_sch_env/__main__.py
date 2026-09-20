#!/usr/bin/env python3
"""lhm-sch-env CLI: 调度迁移环境检查工具。

适配 lhm-sch-env 的 session.json 配置格式，提供与 lhm-common 兼容的
环境检查能力（api_connectivity / resource_group / agent）。
"""

from lhm_sch_env.cli import main

if __name__ == "__main__":
    main()
