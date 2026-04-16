# -*- coding: utf-8 -*-
"""
通用日志解析器框架

提供基于状态机和插件的日志解析架构。适用于需要从结构化日志中提取信息的场景。

## 核心组件

1. **LogParserContext**: 解析上下文，用于在插件间共享数据
2. **LogParserResult**: 解析结果容器
3. **LogParserPluginBase**: 插件基类，实现start/end/filter/process模式
4. **LogParser**: 解析器主类，管理插件并协调解析过程

## 插件模式

插件通过 start/end 标记定义感兴趣的日志段，支持：
- 嵌套插件（sub_plugins）
- 可重复解析（repeat）
- 过滤器（filter）
- 生命周期钩子（is_start, is_end, process, done）

## 使用示例

```python
from sysom_cli.lib.log_parser import LogParser, LogParserPluginBase, LogParserContext

class MyPlugin(LogParserPluginBase):
    def is_start(self, line, global_context, lines, idx):
        return "START MARKER" in line
    
    def is_end(self, line, global_context, lines, idx):
        return "END MARKER" in line
    
    def process(self, line, global_context, lines, idx):
        # 处理每一行
        pass
    
    def done(self, local_context, global_context):
        # 解析完成，保存结果
        self.set("result", "parsed_value")

# 使用
parser = LogParser()
parser.register_plugin("my_plugin", MyPlugin())
parser.parse_lines(log_lines)
result = parser.get_result()
```

## 与 LogScanContext 的区别

- **LogScanContext**: 简单的日志扫描，一次性处理所有日志行（无状态）
- **LogParserPluginBase**: 有状态的解析器，支持 start/end 标记、子插件、重复解析

适用场景：
- 简单扫描 → 使用 `LogScanContext` + 插件函数
- 复杂结构化解析 → 使用 `LogParserPluginBase` + `LogParser`
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional

__all__ = [
    "LogParserContext",
    "LogParserResult",
    "LogParserPluginBase",
    "LogParser",
]


class LogParserContext:
    """
    日志解析上下文
    
    用于在插件间共享数据和状态。
    """
    
    def __init__(self, context: dict = None):
        if context is None:
            context = {}
        self.context = context

    def get(self, key):
        """获取上下文值"""
        return self.context.get(key)

    def set(self, key, value):
        """设置上下文值"""
        self.context[key] = value

    def clear(self):
        """清空上下文"""
        self.context.clear()

    def dict(self):
        """返回上下文字典"""
        return self.context

    def copy(self):
        """复制上下文"""
        return LogParserContext(self.context.copy())


class LogParserResult:
    """
    日志解析结果
    
    包含全局上下文和所有插件的解析结果。
    """
    
    def __init__(self, context: LogParserContext, plugins: dict):
        self.context = context
        self.plugins = plugins

    def __getattr__(self, item):
        # 支持通过属性访问上下文和插件结果
        if item in self.context.context:
            return self.context.context[item]
        if item in self.plugins:
            return self.plugins[item]
        return None

    def __str__(self):
        return str(self.context.context) + str(self.plugins)


class LogParserPluginBase:
    """
    日志解析插件基类
    
    提供基于状态机的日志解析框架。每个插件定义：
    1. is_start: 判断起始标记
    2. is_end: 判断结束标记
    3. filter: 过滤 [start, end] 之间的日志
    4. process: 处理通过过滤的日志
    5. done: 解析完成时的回调
    
    支持：
    - 子插件（sub_plugins）：嵌套解析
    - 可重复解析（repeat）：解析多个段落
    - 历史记录（history）：保存重复解析的所有结果
    
    Attributes:
        start: 是否已开始解析
        end: 是否已结束解析
        local_context: 插件私有上下文
        sub_plugins: 子插件字典
        history: 历史解析结果（repeat=True 时）
        repeat: 是否允许重复解析
        process_contains_start_end: 是否处理 start/end 行
    """

    def __init__(self, **kwargs):
        self.start = False
        self.end = False
        self.local_context = LogParserContext()
        self.sub_plugins = {}
        self.history = []
        self.start_line = ""
        self.end_line = ""
        self.repeat = kwargs.get("repeat", False)
        self.process_contains_start_end = kwargs.get("process_contains_start_end", True)

    def register_sub_plugin(self, plugin_id: str, plugin: "LogParserPluginBase"):
        """注册子插件"""
        if plugin_id in self.sub_plugins:
            raise Exception("plugin id already exists")
        if plugin_id == "context_value":
            raise Exception("plugin id can't be global")
        self.sub_plugins[plugin_id] = plugin

    def process_wrapper(
        self,
        line: str,
        global_context: LogParserContext,
        lines: List[str] = None,
        idx: int = None,
    ):
        """处理单行日志（状态机主逻辑）"""
        def _process_wrapper_after_filter(_line: str):
            if self.filter(_line, global_context, lines, idx):
                self.process(_line, global_context, lines, idx)
                for plugin in self.sub_plugins.values():
                    plugin.process_wrapper(_line, global_context, lines, idx)

        # 如果不允许重复解析，并且已经解析过了，直接返回
        if not self.repeatable() and self.end:
            return

        # 如果没有开始解析，判断是否包含起始标记
        if not self.start:
            if self.is_start(line, global_context, lines, idx):
                self.start = True
                self.start_line = line.strip()
                self.set("start_line", self.start_line)
                if self.process_contains_start_end:
                    _process_wrapper_after_filter(line)
            return

        # 如果已经开始解析，判断是否包含结束标记
        elif not self.end:
            if self.is_end(line, global_context, lines, idx):
                self.end = True
                self.end_line = line.strip()
                self.set("end_line", self.end_line)
                if self.process_contains_start_end:
                    _process_wrapper_after_filter(line)
                self.done(self.local_context, global_context)
                if self.repeatable():
                    # 如果支持重复解析，并且已经解析到结束标记，重置状态
                    for plugin in self.sub_plugins.values():
                        plugin.done(plugin.local_context, global_context)
                    self.history.append(self._get_single_result())
                    self.reset()
                    for plugin in self.sub_plugins.values():
                        plugin.reset()
                return

        # 如果在[start,end]之间，通过filter过滤后的日志，调用 process 方法进行处理
        if self.start and not self.end:
            _process_wrapper_after_filter(line)

    def repeatable(self) -> bool:
        """是否允许重复解析"""
        return self.repeat

    def set(self, key, value):
        """设置插件本地上下文"""
        self.local_context.set(key, value)

    def get(self, key):
        """获取插件本地上下文"""
        return self.local_context.get(key)

    @abstractmethod
    def is_start(
        self, line: str, global_context: LogParserContext, lines: List[str], idx: int
    ) -> bool:
        """判断是否包含起始标记"""
        pass

    @abstractmethod
    def is_end(
        self, line: str, global_context: LogParserContext, lines: List[str], idx: int
    ) -> bool:
        """判断是否包含结束标记"""
        pass

    def filter(
        self, line: str, global_context: LogParserContext, lines: List[str], idx: int
    ) -> bool:
        """对在[start,end]之间的日志进行过滤（默认全部通过）"""
        return True

    @abstractmethod
    def process(
        self, line: str, global_context: LogParserContext, lines: List[str], idx: int
    ):
        """处理日志，在 (start,end) 之间，并且通过filter过滤后的日志在这里进行处理"""
        pass

    @abstractmethod
    def done(self, local_context: LogParserContext, global_context: LogParserContext):
        """处理结束，在此处更新提取的结果到 local_context 中"""
        pass

    def reset(self):
        """重置插件状态，如果插件支持重复解析，则会调用本函数重置插件状态"""
        self.start = False
        self.end = False
        self.start_line = ""
        self.end_line = ""
        self.local_context.clear()

    def _get_single_result(self) -> LogParserResult:
        """获取单次解析结果"""
        sub_plugins_result = {}
        for plugin_id, plugin in self.sub_plugins.items():
            sub_plugins_result[plugin_id] = plugin.get_result()
        return LogParserResult(self.local_context.copy(), sub_plugins_result)

    def get_result(self):
        """获取解析结果"""
        # 如果是可重复的插件，返回多组处理结果
        if self.repeatable():
            return self.history
        return self._get_single_result()


class LogParser:
    """
    日志解析器主类
    
    管理多个插件并协调解析过程。
    
    使用示例：
    ```python
    parser = LogParser()
    parser.register_plugin("plugin1", MyPlugin1())
    parser.register_plugin("plugin2", MyPlugin2())
    parser.parse_lines(log_lines)
    result = parser.get_result()
    ```
    """

    def __init__(self):
        self.plugins = {}
        self.global_context = LogParserContext()

    def __getattr__(self, item):
        # 支持通过属性访问插件和全局上下文
        if item in self.plugins:
            return self.plugins[item]
        if item in self.global_context.context:
            return self.global_context.context[item]
        return None

    def register_plugin(self, plugin_id: str, plugin: LogParserPluginBase):
        """注册插件"""
        if plugin_id in self.plugins:
            raise Exception("plugin id already exists")
        if plugin_id == "global":
            raise Exception("plugin id can't be global")
        self.plugins[plugin_id] = plugin

    def parse_lines(self, lines: List[str]):
        """解析多行日志"""
        for idx, line in enumerate(lines):
            self.parse(line, lines, idx)

    def parse(self, line: str, lines: List[str] = None, idx: int = None):
        """解析单行日志"""
        for plugin in self.plugins.values():
            plugin.process_wrapper(line, self.global_context, lines, idx)

    def get_result(self):
        """获取所有插件的解析结果"""
        sub_plugins_result = {}
        for plugin_id, plugin in self.plugins.items():
            sub_plugins_result[plugin_id] = plugin.get_result()
        return LogParserResult(self.global_context, sub_plugins_result)
