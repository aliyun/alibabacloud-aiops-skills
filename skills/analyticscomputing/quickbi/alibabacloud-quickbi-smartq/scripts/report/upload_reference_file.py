# -*- coding: utf-8 -*-
"""
上传本地文件到小Q报告，并返回可用于创建会话的 resources 映射。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import UPLOAD_CHAT_TYPE, read_config, upload_files


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="上传本地文件到小Q报告")
    parser.add_argument("files", nargs="+", help="要上传的本地文件路径")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""
    args = parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    config = read_config()

    upload_result = upload_files(args.files, config=config)
    records = []
    for source_file, raw_result in zip(args.files, upload_result["uploadResults"]):
        records.append(
            {
                "sourceFile": str(Path(source_file).expanduser().resolve()),
                "fileId": raw_result.get("fileId"),
                "fileName": raw_result.get("fileName"),
                "fileType": raw_result.get("fileType"),
            }
        )

    output = {
        "chatType": UPLOAD_CHAT_TYPE,
        "fileCount": len(records),
        "files": records,
        "resources": upload_result["resources"],
        "summary": f"已上传 {len(records)} 个文件",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - 终端脚本直接输出错误
        print(f"上传文件失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
