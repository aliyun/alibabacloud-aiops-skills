#!/usr/bin/env python
# coding=utf-8

# ====================================================================
# E-HPC Instant SDK - 通用输入校验库
# ====================================================================
# 目的:
#   与 scripts/cli/_lib_validate.sh 保持一致的白名单校验逻辑，
#   防止来自 sys.argv / 环境变量等不可信来源的恶意字符（双引号、
#   反斜杠、控制字符等）被直接拼接进 JSON 字符串后引发 JSON/命令注入。
#
# 用法:
#   from _lib_validate import validate_job_id, validate_vm_password, ...
#   job_id = validate_job_id(sys.argv[1])
#
# 校验失败行为:
#   抛出 ValidationError，调用方可用 require_argv 等包装函数自动退出。
# ====================================================================

import re
import sys


class ValidationError(ValueError):
    """输入校验失败时抛出的异常。"""


def _fail(message, hint=None):
    msg = "❌ 输入校验失败: {0}".format(message)
    if hint:
        msg += "\n   正确格式: {0}".format(hint)
    raise ValidationError(msg)


def validate_pattern(name, value, regex, hint):
    """通用：按正则白名单校验。"""
    if value is None or value == "":
        _fail("{0} 不能为空".format(name), hint)
    if not isinstance(value, str):
        _fail("{0} 类型必须为字符串".format(name), hint)
    if not re.match(regex, value):
        _fail("{0} 格式无效: '{1}'".format(name, value), hint)
    return value


# ---- 资源 ID 校验（严格白名单字符）----

def validate_job_id(value):
    return validate_pattern(
        "JobId", value, r"^job-[a-zA-Z0-9]+$", "job- 后跟字母数字"
    )


def validate_job_name(value):
    return validate_pattern(
        "JobName", value, r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$",
        "1-64 位字母/数字/下划线/连字符",
    )


def validate_image_id(value):
    return validate_pattern(
        "ImageId", value, r"^m-[a-zA-Z0-9]+$", "m- 后跟字母数字"
    )


def validate_vswitch_id(value):
    return validate_pattern(
        "VSwitchId", value, r"^vsw-[a-zA-Z0-9]+$", "vsw- 后跟字母数字"
    )


def validate_security_group_id(value):
    return validate_pattern(
        "SecurityGroupId", value, r"^sg-[a-zA-Z0-9]+$", "sg- 后跟字母数字"
    )


def validate_region(value):
    return validate_pattern(
        "Region", value, r"^[a-z][a-z0-9-]*[a-z0-9]$",
        "小写字母/数字/连字符，如 cn-shanghai",
    )


# ---- 域名/主机名（NAS Server 等）----

def validate_hostname(name, value):
    if value is None or value == "":
        _fail("{0} 不能为空".format(name))
    if not isinstance(value, str):
        _fail("{0} 类型必须为字符串".format(name))
    if len(value) > 253:
        _fail("{0} 长度超过 253".format(name))
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$", value):
        _fail(
            "{0} 格式无效: '{1}'".format(name, value),
            "合法的主机名/域名（字母数字、点、连字符）",
        )
    return value


# ---- 容器镜像引用 ----

def validate_container_image(value):
    if value is None or value == "":
        _fail("ContainerImage 不能为空")
    if not isinstance(value, str):
        _fail("ContainerImage 类型必须为字符串")
    if len(value) > 512:
        _fail("ContainerImage 长度超过 512")
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._:/@-]*$", value):
        _fail(
            "ContainerImage 包含非法字符: '{0}'".format(value),
            "仅允许 字母数字 . _ : / @ -",
        )
    return value


# ---- 自由文本字段（JOB_DESCRIPTION 等）----

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def validate_json_safe_text(name, value, maxlen=256):
    if value is None or value == "":
        _fail("{0} 不能为空".format(name))
    if not isinstance(value, str):
        _fail("{0} 类型必须为字符串".format(name))
    if len(value) > maxlen:
        _fail("{0} 长度超过 {1}".format(name, maxlen))
    if '"' in value:
        _fail("{0} 不允许包含双引号 (\")".format(name))
    if "\\" in value:
        _fail("{0} 不允许包含反斜杠 (\\)".format(name))
    if _CTRL_RE.search(value):
        _fail("{0} 包含非法控制字符".format(name))
    return value


# ---- VM 登录密码 ----

def validate_vm_password(value):
    if value is None or value == "":
        _fail("VM_PASSWORD 不能为空", "请先 export VM_PASSWORD=<your-password>")
    if not isinstance(value, str):
        _fail("VM_PASSWORD 类型必须为字符串")
    if len(value) < 8 or len(value) > 30:
        _fail("VM_PASSWORD 长度必须为 8-30")
    if '"' in value or "\\" in value:
        _fail("VM_PASSWORD 不允许包含 \" 或 \\")
    if _CTRL_RE.search(value):
        _fail("VM_PASSWORD 包含非法控制字符")
    return value


# ---- 命令行包装 ----

def require_argv(argv, index, validator, usage):
    """从 sys.argv 取第 index 个参数并交给 validator 校验，失败时打印用法并退出。"""
    if len(argv) <= index:
        sys.stderr.write("❌ 错误: 缺少参数\n")
        sys.stderr.write(usage + "\n")
        sys.exit(2)
    try:
        return validator(argv[index])
    except ValidationError as e:
        sys.stderr.write(str(e) + "\n")
        sys.stderr.write(usage + "\n")
        sys.exit(2)
