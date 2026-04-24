# -*- coding: utf-8 -*-
"""
提供稳定的设备唯一标识获取能力，基于持久化 UUID + 平台文件读取实现，

用法：
    from device_id import get_device_id, get_device_account_id, get_device_hostname

    device_id   = get_device_id()
    account_id  = get_device_account_id()
    hostname    = get_device_hostname()
"""

from __future__ import annotations

import hashlib
import os
import platform
import random
import string
import uuid
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

def get_device_id() -> str:
    """获取设备ID。

    按优先级依次尝试：
      1. 持久化文件 ~/.qbi/device_id（已有则复用）
      2. Linux /etc/machine-id（纯文件读取，无需外部命令）
      3. 首次使用时生成 UUID 并持久化
    """
    device_id: Optional[str] = None

    # 优先读取已持久化的设备 ID（跨平台通用）
    device_id = _read_persisted_device_id()
    if device_id:
        return device_id

    # Linux 环境尝试读取 machine-id（纯文件读取）
    if platform.system() == "Linux":
        device_id = _read_linux_machine_id()
        if device_id:
            # 将 machine-id 也持久化，保证后续一致性
            _write_persisted_device_id(device_id)
            return device_id

    # 生成新的 UUID 并持久化
    device_id = _create_persisted_device_id()
    return device_id


def get_device_account_id() -> str:
    """获取设备唯一标识的 MD5 值，可直接用作 accountId。"""
    device_id = get_device_id()
    account_id = hashlib.md5(device_id.encode("utf-8")).hexdigest()
    print(
        f"[设备标识] platform={platform.system()}, "
        f"device_id={device_id[:8]}..., accountId(md5)={account_id}",
        flush=True,
    )
    return account_id


def get_device_hostname() -> str:
    """获取当前设备主机名；获取失败时返回带随机后缀的占位名。"""
    try:
        name = platform.node()
        if name:
            return name
    except Exception:
        pass
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"host_{suffix}"


# ---------------------------------------------------------------------------
# Linux machine-id（纯文件读取，无外部命令）
# ---------------------------------------------------------------------------

def _read_linux_machine_id() -> Optional[str]:
    """读取 Linux machine-id（systemd 系统 + 旧 dbus 系统）。"""
    for path_str in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            p = Path(path_str)
            if p.exists():
                content = p.read_text().strip()
                if content:
                    return content
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# 持久化设备 ID（跨平台通用方案）
# ---------------------------------------------------------------------------

_QBI_HOME = Path.home() / ".qbi"
_DEVICE_ID_FILE = _QBI_HOME / "device_id"


def _read_persisted_device_id() -> Optional[str]:
    """从本地持久化文件读取设备 ID。"""
    try:
        if _DEVICE_ID_FILE.exists():
            content = _DEVICE_ID_FILE.read_text().strip()
            if content:
                return content
    except Exception:
        pass
    return None


def _write_persisted_device_id(device_id: str) -> None:
    """将设备 ID 写入持久化文件。"""
    try:
        _QBI_HOME.mkdir(parents=True, exist_ok=True)
        _DEVICE_ID_FILE.write_text(device_id, encoding="utf-8")
    except Exception:
        pass


def _create_persisted_device_id() -> str:
    """生成并持久化一个 UUID 作为设备标识。"""
    device_id = str(uuid.uuid4())
    _write_persisted_device_id(device_id)
    return device_id
