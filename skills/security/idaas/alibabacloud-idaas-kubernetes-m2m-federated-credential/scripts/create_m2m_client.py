#!/usr/bin/env python3
"""创建 M2M Client 应用（SsoType=oidc+oauth2/m2m），并确保 M2M 客户端能力已启用。

用法: create_m2m_client.py <region> <instance_id> <app_name> [description]
输出: 原始响应 + APP_ID=app_xxx + M2M_STATUS=enabled
"""
import json
import sys

from common import info, run_aliyun


def main() -> None:
    if len(sys.argv) < 4:
        die_usage()
    region, iid, name = sys.argv[1:4]
    desc = sys.argv[4] if len(sys.argv) > 4 else "由 skill idaas-kubernetes-m2m-federated-credential 创建"

    d = run_aliyun([
        "eiam", "CreateApplication", "--region", region,
        "--InstanceId", iid,
        "--ApplicationName", name,
        "--ApplicationSourceType", "urn:alibaba:idaas:app:source:standard",
        "--SsoType", "oidc+oauth2/m2m",
        "--Description", desc,
    ])
    print(json.dumps(d, ensure_ascii=False))
    app_id = d.get("ApplicationId", "")
    if not app_id:
        sys.exit("ERROR: 创建应用失败（名称重复？M2M 应用数量超 License 配额？"
                 "实例未开通 M2M 收费功能？）")

    def get_status() -> str:
        try:
            g = run_aliyun(["eiam", "GetApplication", "--region", region,
                            "--InstanceId", iid, "--ApplicationId", app_id])
            a = g.get("Application", g)
            return a.get("M2MClientStatus", "")
        except SystemExit:
            return ""

    status = get_status()
    if status != "enabled":
        info(f"M2MClientStatus={status or '未知'}，尝试启用...")
        try:
            run_aliyun(["eiam", "EnableApplicationM2MClient", "--region", region,
                        "--InstanceId", iid, "--ApplicationId", app_id])
        except SystemExit as e:
            info(f"启用调用异常: {e}")
        status = get_status()

    print(f"APP_ID={app_id}")
    print(f"M2M_STATUS={status}")
    if status != "enabled":
        info("WARNING: M2M Client 状态非 enabled，Token 请求可能失败，请到控制台检查")


def die_usage() -> None:
    sys.exit("用法: create_m2m_client.py <region> <instance_id> <app_name> [description]")


if __name__ == "__main__":
    main()
