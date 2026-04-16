# SysOM CLI 开发指南

欢迎参与 `sysom_cli` 的开发！本文档将帮助你快速上手，了解项目架构，并学会如何添加新功能。

> **说明**：**`memory`** 子系统含 **`classify` / `memgraph` / `oom` / `javamem`**（默认**快速排查**）；可选 **`--deep-diagnosis`** 接**深度诊断**（远程专项）。非内存 Agent 主路径为 **`io` / `net` / `load`**。底层 OpenAPI 直调 CLI 不向 Agent 宣读，维护者见 [invoke-diagnosis.md](./invoke-diagnosis.md)。见 [SKILL.md](../SKILL.md)。权限引导见 [openapi-permission-guide.md](./openapi-permission-guide.md)。

## 目录

- [项目架构](#项目架构)
- [开发环境设置](#开发环境设置)
- [添加新命令](#添加新命令)
- [执行模式详解](#执行模式详解)
- [代码规范](#代码规范)
- [测试和调试](#测试和调试)
- [常见问题](#常见问题)

## 项目架构

### 目录结构

```
sysom_cli/
├── lib/                           # 【通用工具库】所有子系统共享
│   ├── schema.py                  # JSON 信封格式定义
│   ├── specialty_args.py          # io/net/load 共用的 OpenAPI 侧参数（与 invoke 实现同源）
│   ├── specialty_command.py       # BaseServiceSpecialtyCommand（薄封装 service_name）
│   ├── diagnosis_backend.py       # 可插拔 SysOM 专项后端（默认 DiagnosisInvokeCommand）
│   ├── kernel_log.py              # 内核日志采集工具
│   ├── log_plugin.py              # 简单日志扫描插件框架
│   ├── log_parser.py              # 复杂日志解析引擎框架
│   └── auth.py                    # 阿里云认证工具
│
├── core/                          # 【核心框架】所有子系统共享
│   ├── base.py                    # BaseCommand 抽象基类
│   ├── registry.py                # 命令自动发现与注册（支持多级）
│   └── executor.py                # 统一执行器
│
├── precheck/                      # 【顶层命令】环境预检查
│   └── command.py                 # 命令入口（@command_metadata）
│
├── memory/                        # 【子系统】内存快速排查子命令
│   ├── lib/                       # classify_engine、oom_quick、oom_log_extract、envelope_memory、invoke_bridge…
│   ├── classify/                  # memory classify
│   ├── memgraph/                  # memory memgraph（内存全景）
│   ├── oom/                       # memory oom
│   └── javamem/                   # memory javamem（骨架）
│
├── io/                            # 【子系统】磁盘与 IO 专项（iofsstat、iodiagnose）
├── net/                           # 【子系统】网络专项（packetdrop、netjitter）
├── load/                          # 【子系统】负载与调度专项（delay、loadtask）
│
├── diagnosis/                     # 【子系统】SysOM 远程诊断（InvokeDiagnosis）
│   └── invoke/
│       └── command.py             # @command_metadata(subsystem="diagnosis")
│
└── __main__.py                    # CLI 入口（统一调度所有命令）
```

### 命令层级结构

`sysom_cli` 支持两种命令类型：

1. **顶层命令**（Top-Level Command）
   - 直接在 `sysom_cli/` 下有自己的目录
   - 目录中包含 `command.py` 文件
   - 示例：`precheck`
   - 使用方式：`osops precheck`

2. **子系统命令**（Subsystem Command）
   - 属于某个子系统，子系统下有多个子命令
   - 子系统目录下的各个命令目录中包含 `command.py`
   - 示例：`diagnosis` 子系统包含 `invoke`
   - 使用方式：非内存 `osops io|net|load <service_name> ...`；维护者 OpenAPI 直调见 [invoke-diagnosis.md](./invoke-diagnosis.md)

### 核心组件

#### 1. BaseCommand 抽象基类

所有子命令必须继承此类：

```python
from sysom_cli.core.base import BaseCommand, ExecutionMode

class MyCommand(BaseCommand):
    @property
    def command_name(self) -> str:
        return "mycmd"
    
    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }
    
    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        # 实现 local 模式逻辑
        pass
```

#### 2. CommandRegistry 命令注册中心

自动发现和注册命令：

- 支持两种发现模式：
  - `discover_commands(top_level=True)`: 扫描顶层命令
  - `discover_commands(subsystem="diagnosis")`: 扫描子系统的子命令
- 自动导入 `command.py` 模块
- 通过 `@command_metadata` 装饰器注册

#### 3. CommandExecutor 统一执行器

- 从环境变量 `MEMORY_MODE` 获取执行模式
- 路由到对应命令的执行方法

## 开发环境设置

### 1. 安装依赖

```bash
cd /path/to/sysom-diagnosis
./scripts/init.sh
```

### 2. 设置 PYTHONPATH

```bash
export PYTHONPATH="/path/to/sysom-diagnosis/scripts:$PYTHONPATH"
```

### 3. 验证安装

```bash
python3 -m sysom_cli --list-capabilities
```

## 添加新命令

添加新命令只需 3 步，**无需修改任何其他文件**！

### 添加子系统命令（如 memory leak）

#### 步骤 1: 创建命令目录

例如，在 `memory` 子系统下添加 `leak` 命令：

```bash
mkdir -p scripts/sysom_cli/memory/leak
touch scripts/sysom_cli/memory/leak/__init__.py
```

#### 步骤 2: 创建 command.py

创建 `scripts/sysom_cli/memory/leak/command.py`：

```python
# -*- coding: utf-8 -*-
"""
Memory leak 检测命令
"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata


@command_metadata(
    name="leak",
    help="内存泄漏检测和分析",
    subsystem="memory",  # 重要：标记这是 memory 子系统的命令
    args=[
        (["--pid"], {"type": int, "help": "进程 PID"}),
        (["--duration"], {"type": int, "default": 60, "help": "监控时长（秒）"}),
        (["--threshold"], {"type": float, "default": 10.0, "help": "泄漏阈值（MB/s）"}),
    ]
)
class LeakCommand(BaseCommand):
    """内存泄漏检测命令"""
    
    @property
    def command_name(self) -> str:
        return "leak"
    
    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }
    
    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        """Local 模式：本地监控和分析"""
        from sysom_cli.lib.schema import envelope, agent_block
        
        # 你的实现逻辑
        pid = getattr(ns, "pid", None)
        duration = getattr(ns, "duration", 60)
        
        # TODO: 实现泄漏检测逻辑
        result_data = {
            "pid": pid,
            "leak_detected": False,
            "leak_rate_mb_s": 0.0,
        }
        
        return envelope(
            action="memory_leak",
            ok=True,
            agent=agent_block(
                "normal",
                f"进程 {pid} 监控 {duration}s，未检测到泄漏。"
            ),
            data=result_data,
            execution={"mode": "local", "stage": "leak"}
        )
```

#### 步骤 3: 直接使用

**无需修改任何其他文件！** 命令自动注册。

```bash
# 查看帮助
./scripts/osops.sh memory leak --help

# 执行命令
./scripts/osops.sh memory leak --pid 1234 --duration 120
```

### 添加顶层命令（如 version）

#### 步骤 1: 创建命令目录

```bash
mkdir -p scripts/sysom_cli/version
touch scripts/sysom_cli/version/__init__.py
```

#### 步骤 2: 创建 command.py

创建 `scripts/sysom_cli/version/command.py`：

```python
# -*- coding: utf-8 -*-
"""
版本信息命令
"""
from __future__ import annotations

from argparse import Namespace
from typing import Any, Dict

from sysom_cli.core.base import BaseCommand, ExecutionMode
from sysom_cli.core.registry import command_metadata


@command_metadata(
    name="version",
    help="显示 sysom_cli 版本信息",
    # 注意：顶层命令不需要指定 subsystem 参数
    args=[]
)
class VersionCommand(BaseCommand):
    """版本信息命令"""
    
    @property
    def command_name(self) -> str:
        return "version"
    
    @property
    def supported_modes(self) -> Dict[str, bool]:
        return {
            ExecutionMode.LOCAL: True,
            ExecutionMode.REMOTE: False,
            ExecutionMode.HYBRID: False,
        }
    
    def execute_local(self, ns: Namespace) -> Dict[str, Any]:
        """返回版本信息"""
        from sysom_cli.lib.schema import envelope, agent_block
        
        return envelope(
            action="version",
            ok=True,
            agent=agent_block("normal", "SysOM CLI v1.0.0"),
            data={"version": "1.0.0", "build": "20260319"}
        )
```

#### 步骤 3: 注册到顶层命令列表

编辑 `scripts/sysom_cli/__main__.py`，在 `TOP_COMMANDS` 列表中添加：

```python
TOP_COMMANDS: List[Dict[str, Any]] = [
    {"name": "memory", "help": "内存诊断", "is_subsystem": True},
    {"name": "version", "help": "显示版本信息", "is_subsystem": False},  # 新增
    {"name": "precheck", "help": "环境预检查", "is_subsystem": False},
    {"name": "am", "help": "活动监控 [WIP]", "is_subsystem": False, "not_implemented": True},
]
```

#### 步骤 4: 使用

```bash
# 查看帮助
./scripts/osops.sh version --help

# 执行命令
./scripts/osops.sh version
```

## 执行模式详解

`sysom_cli` 支持三种执行模式，通过环境变量 `MEMORY_MODE` 控制：

### Local 模式 (default)

```bash
# 默认就是 local 模式
./scripts/osops.sh memory oom

# 或显式指定
MEMORY_MODE=local ./scripts/osops.sh memory oom
```

**特点**：
- 本地生成命令
- 本地执行采集
- 本地分析处理

**实现示例**：

```python
def execute_local(self, ns: Namespace) -> Dict[str, Any]:
    # 1. 采集数据
    data = collect_data(ns)
    
    # 2. 分析数据
    analysis = analyze_data(data)
    
    # 3. 返回结果
    return envelope(
        action="memory_oom",
        ok=True,
        agent=agent_block("normal", "OOM 分析完成"),
        data=analysis
    )
```

### Remote 模式

```bash
MEMORY_MODE=remote ./scripts/osops.sh memory cache
```

**特点**：
- 直接调用远程 API
- API 返回最终结果
- 不做本地处理

**实现示例**：

```python
def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
    # 返回执行计划，由网关在节点执行
    plan = build_execution_plan(ns)
    
    return envelope(
        action="memory_cache_plan",
        ok=True,
        agent=agent_block(
            "normal",
            "已生成执行计划，由网关执行。",
            next_steps=[{
                "tool": "sysom_cli memory cache --raw-file <path>",
                "reason": "解析网关回传的结果"
            }]
        ),
        data={"phase": "remote_plan", "plan": plan}
    )
```

### Hybrid 模式

```bash
MEMORY_MODE=hybrid ./scripts/osops.sh memory oom
```

**特点**：
- 调用 OpenAPI（可能是异步接口）
- 轮询任务状态
- 本地处理数据
- 转换为 Agent 标准格式

**实现示例**：

```python
def execute_hybrid(self, ns: Namespace) -> Dict[str, Any]:
    from sysom_cli.memory.oom.api_client import OomApiClient
    
    client = OomApiClient()
    
    # 1. 提交诊断任务
    task_id = client.submit_oom_diagnosis(
        instance_id=getattr(ns, "instance_id", None)
    )
    
    # 2. 轮询任务状态
    raw_result = client.poll_task_result(task_id, timeout=300)
    
    # 3. 本地格式化
    return format_api_result(raw_result, ns)
```

## 代码规范

### 0. 通用库说明

`sysom_cli/lib/` 提供了多个通用工具库，所有命令都可以使用：

#### `schema.py` - JSON 信封格式

```python
from sysom_cli.lib.schema import envelope, agent_block, dumps

# 创建标准响应信封
result = envelope(
    action="memory_oom",
    ok=True,
    agent=agent_block("normal", "分析完成"),
    data={"oom_count": 3}
)

# 输出 JSON
print(dumps(result))
```

#### `kernel_log.py` - 内核日志采集

```python
from sysom_cli.lib.kernel_log import get_kernel_log_lines

# 获取内核日志（自动选择 dmesg 或 journalctl）
lines = get_kernel_log_lines()
```

#### `log_plugin.py` - 简单日志扫描框架

适用于**全日志扫描、简单模式匹配**：

```python
from sysom_cli.lib.log_plugin import LogScanContext

# 创建上下文
ctx = LogScanContext(
    log_lines=lines,
    log_source="dmesg",
    metadata={"host": "server01"}
)

# 定义插件（简单函数）
def oom_detector(ctx: LogScanContext) -> Dict[str, Any]:
    oom_count = sum(1 for line in ctx.log_lines if "Out of memory" in line)
    return {"oom_detected": oom_count > 0, "count": oom_count}

# 执行插件
result = oom_detector(ctx)
```

#### `log_parser.py` - 复杂日志解析框架

适用于**结构化日志解析、状态管理、段落识别**：

```python
from sysom_cli.lib.log_parser import (
    LogParser, LogParserContext, LogParserPluginBase
)

# 定义插件（类，有状态）
class OomBlockPlugin(LogParserPluginBase):
    def is_start(self, line, global_context, lines, idx):
        return "invoked oom-killer" in line
    
    def is_end(self, line, global_context, lines, idx):
        return "Killed process" in line
    
    def process(self, line, global_context, lines, idx):
        self.local_context.data.append(line)
    
    def done(self, local_context, global_context):
        # 处理完整的 OOM 段落
        pass

# 使用解析器
parser = LogParser(plugin_list=[OomBlockPlugin()], context=LogParserContext())
parser.parse(lines)
```

**区别**：
- `log_plugin.py`: 简单、无状态、函数式，适合快速扫描
- `log_parser.py`: 复杂、有状态、类式，适合结构化解析

#### `auth.py` - 阿里云认证

```python
from sysom_cli.lib.auth import run_precheck

# 执行认证预检查
result = run_precheck()
# 返回：{"method": "aksk", "success": True, "access_key_id": "LTAI..."}
```

### 1. 文件组织

每个子命令目录应包含：

- **`command.py`** (必需): 命令入口，继承 `BaseCommand`
- **辅助文件** (可选): 根据需要拆分逻辑
  - `run.py`: 数据采集逻辑
  - `process.py`: 数据处理和格式化
  - `api_client.py`: API 客户端（hybrid 模式）
  - 其他业务逻辑文件

### 2. 命令元数据

使用 `@command_metadata` 装饰器声明命令信息：

```python
@command_metadata(
    name="cmdname",           # 命令名称
    help="命令描述",           # 帮助信息
    subsystem="memory",       # 可选：标记命令所属子系统（子系统命令必需，顶层命令省略）
    args=[                    # 参数定义（argparse 格式）
        (["--param"], {"help": "参数说明", "default": "value"}),
    ]
)
class MyCommand(BaseCommand):
    pass
```

**关键区别**：
- **子系统命令**（如 `memory oom`）：必须指定 `subsystem="memory"`
- **顶层命令**（如 `precheck`）：不需要指定 `subsystem`

### 3. 返回格式

所有命令必须返回标准的 JSON 信封格式：

```python
from sysom_cli.lib.schema import envelope, agent_block

return envelope(
    action="memory_oom",              # 动作名称
    ok=True,                          # 成功/失败
    agent=agent_block(
        "normal",                     # 状态：normal/critical/warning/unknown
        "简要说明",                    # 给 Agent 的消息
        next_steps=[...]              # 可选：后续建议步骤
    ),
    data={...},                       # 数据负载
    error={...},                      # 可选：错误信息
    execution={                       # 可选：执行信息
        "mode": "local",
        "stage": "oom"
    }
)
```

### 4. 错误处理

```python
try:
    result = risky_operation()
except Exception as e:
    from sysom_cli.lib.schema import envelope, agent_block
    return envelope(
        action="memory_oom",
        ok=False,
        agent=agent_block("unknown", f"执行失败: {e}"),
        data={},
        error={"code": "execution_error", "message": str(e)}
    )
```

## 测试和调试

### 1. 单元测试

创建测试文件 `tests/test_leak.py`:

```python
import pytest
from argparse import Namespace
from sysom_cli.memory.leak.command import LeakCommand

def test_leak_command_local():
    cmd = LeakCommand()
    ns = Namespace(pid=1234, duration=60, threshold=10.0)
    result = cmd.execute_local(ns)
    
    assert result["ok"] == True
    assert "pid" in result["data"]
```

### 2. 手动测试

```bash
# 测试命令注册
python3 -m sysom_cli --list-capabilities

# 测试命令执行
MEMORY_MODE=local ./scripts/osops.sh memory leak --pid 1234

# 测试不同模式
MEMORY_MODE=remote ./scripts/osops.sh memory cache
MEMORY_MODE=hybrid ./scripts/osops.sh memory oom
```

### 3. 调试技巧

```bash
# 打开 Python 调试器
python3 -m pdb -m sysom_cli memory leak --pid 1234

# 查看详细日志
python3 -m sysom_cli memory leak --pid 1234 --verbose
```

### 4. 验证 JSON 输出

```bash
# 输出 JSON 并格式化
./scripts/osops.sh memory classify | python3 -m json.tool
```

## 常见问题

### Q1: 新命令没有被发现？

**原因**：
- `command.py` 文件名错误
- 缺少 `@command_metadata` 装饰器
- 目录结构不对

**解决**：
```bash
# 检查目录结构
ls -la scripts/sysom_cli/memory/mycommand/

# 应该看到：
# - __init__.py
# - command.py

# 检查 command.py 是否有装饰器
grep -n "@command_metadata" scripts/sysom_cli/memory/mycommand/command.py
```

### Q2: 如何支持多个执行模式？

在 `supported_modes` 中声明：

```python
@property
def supported_modes(self) -> Dict[str, bool]:
    return {
        ExecutionMode.LOCAL: True,
        ExecutionMode.REMOTE: True,    # 支持 remote
        ExecutionMode.HYBRID: True,    # 支持 hybrid
    }
```

然后实现对应的方法：

```python
def execute_remote(self, ns: Namespace) -> Dict[str, Any]:
    # remote 模式实现
    pass

def execute_hybrid(self, ns: Namespace) -> Dict[str, Any]:
    # hybrid 模式实现
    pass
```

### Q3: 如何添加子系统（如 `io`）？

**步骤 1**: 创建子系统目录

```bash
mkdir -p scripts/sysom_cli/io
touch scripts/sysom_cli/io/__init__.py
```

**步骤 2**: 创建子系统入口（可选）

```bash
# 如果需要子系统级配置，创建 entry.py
touch scripts/sysom_cli/io/entry.py
```

**步骤 3**: 添加子命令

```bash
mkdir -p scripts/sysom_cli/io/disk
touch scripts/sysom_cli/io/disk/__init__.py
# 创建 scripts/sysom_cli/io/disk/command.py
# 重要：在 @command_metadata 中添加 subsystem="io"
```

**步骤 4**: 更新顶层命令列表

编辑 `scripts/sysom_cli/__main__.py`，添加 `io` 到 `TOP_COMMANDS`：

```python
TOP_COMMANDS: List[Dict[str, Any]] = [
    {"name": "memory", "help": "内存诊断", "is_subsystem": True},
    {"name": "io", "help": "IO 诊断", "is_subsystem": True},  # 新增
    ...
]
```

### Q4: 如何共享代码？

**选项 1**: 放在顶层 `lib/` 目录（跨子系统共享，推荐）

```bash
# 将通用工具放到顶层 lib/
# 例如：lib/auth.py, lib/log_parser.py, lib/schema.py
```

```python
# 在任何命令中使用
from sysom_cli.lib.schema import envelope, agent_block
from sysom_cli.lib.auth import run_precheck
from sysom_cli.lib.log_parser import LogParser
```

**选项 2**: 放在子系统内部（子系统内共享）

```bash
# 只在 memory 子系统内使用的工具
mkdir -p scripts/sysom_cli/memory/lib
```

```python
# memory/oom/command.py
from sysom_cli.memory.lib.utils import memory_specific_util
```

**选项 3**: 放在命令目录内（命令内部使用）

```bash
# 只在 oom 命令内使用的辅助文件
# scripts/sysom_cli/memory/oom/collector.py
# scripts/sysom_cli/memory/oom/analyzer.py
```

### Q5: 如何处理异步 API？

使用 Python 的 `asyncio` 或同步轮询：

```python
import time

def execute_hybrid(self, ns: Namespace) -> Dict[str, Any]:
    client = ApiClient()
    
    # 提交任务
    task_id = client.submit_task()
    
    # 轮询状态
    max_attempts = 60
    for i in range(max_attempts):
        status = client.get_status(task_id)
        if status == "completed":
            return client.get_result(task_id)
        elif status == "failed":
            raise Exception("Task failed")
        time.sleep(5)
    
    raise TimeoutError("Task timeout")
```

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/my-command`)
3. 提交更改 (`git commit -am 'Add my command'`)
4. 推送到分支 (`git push origin feature/my-command`)
5. 创建 Pull Request

## 参考资源

- **核心框架代码**:
  - `sysom_cli/core/base.py` - 抽象基类定义
  - `sysom_cli/core/registry.py` - 命令注册机制
  - `sysom_cli/core/executor.py` - 执行器实现

- **示例命令**:
  - `sysom_cli/memory/oom/command.py` - 完整示例
  - `sysom_cli/memory/classify/command.py` - 简单示例
  - `sysom_cli/memory/cache/command.py` - 多模式示例

- **测试用例**: `tests/` 目录

## 联系方式

如有问题，请在 GitHub 上提 Issue 或联系维护者。

---

**Happy Coding! 🚀**
