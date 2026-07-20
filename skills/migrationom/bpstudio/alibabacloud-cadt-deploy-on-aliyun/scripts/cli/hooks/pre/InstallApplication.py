"""Pre-hook: InstallApplication parameter validation.

Locates the deployment target via regionId + instanceIds (direct ECS targeting).
Required fields: regionId, instanceIds, appName, artifactUrl (or filePath), applicationStart, applicationStop, artifactPath.

When filePath is provided, the pre-hook automatically uploads to OSS and injects artifactUrl.
"""
from __future__ import annotations

import sys
from typing import Any, Dict

from lib.errors import HookReject, PRE_HOOK_REJECTED
from lib.oss_upload import upload_to_oss

REQUIRED_FIELDS = (
    "regionId",
    "instanceIds",
    "appName",
    "applicationStart",
    "applicationStop",
    "artifactPath",
)


def pre_hook(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Validate InstallApplication preconditions.

    Rules:
    - regionId + instanceIds required (locate ECS target)
    - appName required (for installPath default + PID file naming)
    - artifactUrl OR filePath required (OSS artifact URL or local file to upload)
    - applicationStart + applicationStop + artifactPath required
    """
    missing = [f for f in REQUIRED_FIELDS if not args.get(f)]
    if missing:
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"InstallApplication missing required fields: {', '.join(missing)}",
            fix_hint=(
                "Required: regionId + instanceIds (locate ECS target)"
                " + appName (application name)"
                " + artifactUrl (OSS artifact URL, or use filePath for local upload)"
                " + applicationStart/applicationStop (script paths relative to installPath, e.g. scripts/start.sh)"
                " + artifactPath (build artifact download/extract directory, e.g. /root/my-app-deploy; independent of installPath)"
            ),
        )

    if not args.get("artifactUrl") and not args.get("filePath"):
        raise HookReject(
            PRE_HOOK_REJECTED,
            "InstallApplication requires artifactUrl (OSS URL) or filePath (local file to upload)",
            fix_hint="Provide either artifactUrl or filePath",
        )

    if args.get("filePath"):
        if args.get("artifactUrl"):
            print("WARN:  Both filePath and artifactUrl provided; filePath will be uploaded and override artifactUrl", file=sys.stderr)

        file_path = args.pop("filePath")
        oss_region = args.pop("ossRegion", None) or args.get("regionId") or "cn-hangzhou"
        app_name = args["appName"]

        print(f"INFO:  Uploading {file_path} to OSS (region={oss_region})...", file=sys.stderr)
        package_url = upload_to_oss(file_path, app_name, oss_region)
        args["artifactUrl"] = package_url

    return args