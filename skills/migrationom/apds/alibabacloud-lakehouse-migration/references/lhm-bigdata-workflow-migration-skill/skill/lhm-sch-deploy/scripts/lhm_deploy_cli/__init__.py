"""LHM 调度迁移部署 CLI。

包结构：
- cli.py    : 命令行入口与阶段编排（触发 → 轮询 → 取结果 → 报告）
- client.py : LHM SDK 客户端工厂与 API 封装
- report.py : 结果包下载解析与 JSON / Markdown 报告生成
- ui.py     : 终端输出、状态映射等展示辅助
"""

__version__ = "0.1.0"
