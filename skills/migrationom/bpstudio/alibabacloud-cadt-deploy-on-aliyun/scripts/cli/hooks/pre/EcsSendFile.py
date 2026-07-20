from __future__ import annotations

import base64
import os
import shutil
import sys
import tempfile
import uuid
from typing import Any, Dict

CONTENT_SIZE_LIMIT = 32000


def _info(msg: str) -> None:
    print(f"INFO:  {msg}", file=sys.stderr)


def pre_hook(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    content = args.get("content", "")
    if len(content) <= CONTENT_SIZE_LIMIT:
        return args

    _info(f"Content size ({len(content)} chars) exceeds {CONTENT_SIZE_LIMIT} limit, routing via OSS...")

    from lib.oss_upload import upload_to_oss
    from lib.runner import run_op

    name = args["name"]
    region_id = args["regionId"]
    target_dir = args["targetDir"]
    content_type = args.get("contentType", "PlainText")
    file_mode = args.get("fileMode")
    file_owner = args.get("fileOwner")
    file_group = args.get("fileGroup")
    overwrite = args.get("overwrite", False)

    if content_type == "Base64":
        raw = base64.b64decode(content)
    else:
        raw = content.encode("utf-8")

    uid_prefix = str(uuid.uuid4())[:8]
    safe_name = f"{uid_prefix}-{name}"
    tmp_dir = tempfile.mkdtemp(prefix="cadt-sendfile-")
    tmp_path = os.path.join(tmp_dir, safe_name)
    try:
        with open(tmp_path, "wb") as f:
            f.write(raw)

        _info(f"Uploading {len(raw)} bytes to OSS (region={region_id})...")
        upload_to_oss(tmp_path, "sendfile", region_id)

        object_key = f"sendfile/{safe_name}"
        _info(f"Generating presigned URL for {object_key}...")
        presign_result = run_op("OssGeneratePresignedUrl", {
            "objectKey": object_key,
            "expires": 3600,
        })

        url = (
            presign_result.get("data", {}).get("attributes", {}).get("url")
            or presign_result.get("data", {}).get("url")
        )
        if not url:
            raise RuntimeError(
                f"OssGeneratePresignedUrl did not return a URL; response: {presign_result}"
            )

        target_path = f"{target_dir.rstrip('/')}/{name}"
        lines = [
            "#!/bin/bash",
            "set -euo pipefail",
            f'mkdir -p "{target_dir}"',
        ]

        if not overwrite:
            lines.append(
                f'if [ -f "{target_path}" ]; then echo "File already exists: {target_path}" >&2; exit 1; fi'
            )

        lines.append(f'curl -sSfL -o "{target_path}" "{url}"')

        if file_mode:
            lines.append(f'chmod "{file_mode}" "{target_path}"')

        if file_owner or file_group:
            owner = file_owner or ""
            group = file_group or ""
            lines.append(f'chown "{owner}:{group}" "{target_path}"')

        command = "\n".join(lines)
        _info(f"Downloading file to {len(args['instanceIds'])} instance(s) via EcsRunCommandSync...")

        dl_args: Dict[str, Any] = {
            "regionId": region_id,
            "instanceIds": args["instanceIds"],
            "command": command,
            "type": "RunShellScript",
        }

        result = run_op("EcsRunCommandSync", dl_args)
        args["__bypass_result__"] = result

    finally:
        if tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return args
