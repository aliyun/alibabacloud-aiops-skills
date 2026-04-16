# -*- coding: utf-8 -*-
"""
日志扫描插件的通用抽象

提供基于日志扫描的插件化架构支持。

## 使用场景

任何需要扫描系统日志（内核日志、应用日志等）并提取信息的子系统都可以使用。

## 插件协议

插件需要实现以下签名的函数：

```python
def run(ctx: LogScanContext) -> Dict[str, Any]:
    \"\"\"
    扫描日志并返回提取的信息
    
    Args:
        ctx: 日志扫描上下文，包含日志行和元数据
        
    Returns:
        提取的信息字典
    \"\"\"
    pass
```

## 示例

### Memory Classify 插件

```python
from sysom_cli.lib.log_plugin import LogScanContext

def run(ctx: LogScanContext) -> Dict[str, Any]:
    oom_count = sum(1 for line in ctx.log_lines if "oom-killer" in line)
    return {"oom_count": oom_count}
```

### 未来的 IO 错误扫描插件

```python
from sysom_cli.lib.log_plugin import LogScanContext

def run(ctx: LogScanContext) -> Dict[str, Any]:
    io_errors = sum(1 for line in ctx.log_lines if "I/O error" in line)
    return {"io_error_count": io_errors}
```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LogScanContext:
    """
    日志扫描上下文
    
    为日志扫描插件提供统一的输入数据结构。
    
    Attributes:
        log_lines: 日志行列表
        log_source: 日志来源标识（如 "dmesg", "journal", "syslog"）
        log_file: 日志文件路径（如果从文件读取）
        metadata: 额外的元数据（可选）
    """
    log_lines: List[str]
    log_source: str
    log_file: Optional[str] = None
    metadata: Optional[dict] = None


# 向后兼容别名（供已有代码使用）
CollectContext = LogScanContext
