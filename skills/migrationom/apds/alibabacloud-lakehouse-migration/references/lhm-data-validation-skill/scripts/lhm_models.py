# -*- coding: utf-8 -*-
"""轻量 request 模型层：替代已废弃、不再安装的 alibabacloud_lhm20250116 SDK。

背景：
- LHM 接口的网络调用早已改由 aliyun CLI 发出（见 aliyun_cli.invoke），原 SDK
  仅剩「构造 request 参数」这一个用途——把 snake_case 关键字参数序列化成后端
  要求的 camelCase 平铺 dict（to_map()），再由 aliyun_cli._request_params 提取
  为 `--kebab-case` 命令行参数。
- 既然该 SDK 不再安装，这里用「通用 Request 基类 + 模块级 __getattr__ 动态建类」
  的本地实现替代它：无任何第三方依赖，也无需为每个接口手写模型。

行为与原 SDK models 的 to_map() 对齐：
- 值为 None 的字段不输出（原 SDK 每个字段都包在 `if xxx is not None` 里）；
- 字段名 snake_case -> camelCase（source_table -> sourceTable，dst_ds_id -> dstDsId）；
- 嵌套 Request 对象递归调用 to_map()，list/tuple 逐项序列化；
- dict 值原样保留（如 diff_tolerate_values={"SAME": 0}，其 key 是后端约定值，不转换）。

用法与原来完全一致：
    import lhm_models
    req = lhm_models.AddDataCheckTaskRequest(task_name='x', check_type=0)
    req.to_map()  # -> {'taskName': 'x', 'checkType': 0}
"""
from __future__ import annotations

from typing import Any


def _camel(name: str) -> str:
    """snake_case -> camelCase：source_table -> sourceTable，dst_ds_id -> dstDsId。"""
    head, *rest = name.split('_')
    return head + ''.join(part[:1].upper() + part[1:] for part in rest)


def _serialize(value: Any) -> Any:
    """递归序列化字段值：Request -> to_map()，list/tuple -> 逐项，其余（含 dict）原样。"""
    if isinstance(value, LhmRequest):
        return value.to_map()
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


class LhmRequest:
    """通用 request 模型：接受任意 snake_case kwargs，to_map() 输出 camelCase dict。"""

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_map(self) -> dict:
        result: dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                continue
            result[_camel(key)] = _serialize(value)
        return result

    def __repr__(self) -> str:
        fields = ', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())
        return f'{type(self).__name__}({fields})'


def __getattr__(name: str) -> type:
    """按需动态生成任意 request 模型类（PEP 562 模块级 __getattr__）。

    所有 LHM request 模型行为一致（存字段 + to_map 转 camelCase），因此用同一个
    LhmRequest 基类动态派生即可，无需逐一枚举。仅对含 'Request' 的名字建类，其余
    属性访问照常抛 AttributeError，避免拼写错误被静默吞掉。
    """
    if 'Request' not in name:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    cls = type(name, (LhmRequest,), {})
    globals()[name] = cls  # 缓存，二次访问直接命中，不再重建
    return cls
