#!/usr/bin/env python3
"""把本地文件转成工具入参 JSON, 避免在 shell 里手写多层引号。

RunScript / RunIaC 的 script、code 参数是一整段源码。直接写在命令行里,
bash 与 PowerShell 的转义规则不同, 双引号套单引号套反斜杠极易出错; 写成
文件再用本脚本读出来最省事, 且两个 shell 的命令完全一样。

用法:
    to_json.py script /path/to/s.py      # -> {"script": "..."}
    to_json.py code   /path/to/main.tf   # -> {"code": "..."}
    to_json.py KEY    /path/to/file      # -> {"KEY": "..."}

输出到 stdout, 接管道给 mcpx:
    to_json.py script /tmp/s.py | mcpx call RunScript -

只用标准库, 不依赖系统 python —— 用 uv run 调它即可。
"""

import json
import os
import sys

EXIT_OK = 0
EXIT_USAGE = 2

USAGE = """用法: to_json.py <KEY> <文件路径>

把文件内容原样读成 JSON 字符串, 输出 {"<KEY>": "<内容>"}。

常用 KEY:
  script   RunScript 的入参
  code     RunIaC 的入参

例:
  uv run --python 3.11 scripts/to_json.py script /tmp/s.py | \\
      uv run --python 3.11 scripts/mcpx.py call RunScript -
"""


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(USAGE)
        return EXIT_USAGE

    key, path = argv[1], argv[2]

    if not os.path.isfile(path):
        sys.stderr.write("文件不存在: %s\n" % path)
        return EXIT_USAGE

    # newline="" 保留文件原有换行, 不做 \r\n -> \n 的翻译。
    # 服务端拿到什么就执行什么, Windows 上写出来的 CRLF 也照实传过去。
    with open(path, "r", encoding="utf-8", newline="") as fh:
        content = fh.read()

    sys.stdout.write(json.dumps({key: content}, ensure_ascii=False) + "\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv))
