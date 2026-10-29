#!/usr/bin/env python3
"""PAM 功能权限授权（全自动，两段式）：
  A. RS 级：AuthorizeResourceServerToClient(iap_pam)（幂等）
  B. 权限项级：ListResourceServerScopes(--ResourceServerScopeType all) 找到
     cloud_account_role:obtain_access_credential 的 ress_id
     → AuthorizeResourceServerScopesToClient

用法: authorize_pam_scope.py <region> <instance_id> <client_app_id>
输出末行: PAM_AUTH=auto_done | already_authorized | module_disabled | scope_not_found

关键实测（2026-10，v0.4.0 修正）:
- PAM 系统应用固定 ID = iap_pam（ApplicationCreationType=system_init，
  默认 ListApplications 不返回；GetApplication 可直查）
- ⚠️ ListResourceServerScopes 不带过滤时返回 0！PAM 的 scope 类型是
  application_delegated/delegated，必须 --ResourceServerScopeType all 才可见
  （共 14 个，含目标 cloud_account_role:obtain_access_credential）
- AuthorizeResourceServerScopesToClient 需要 ress_id（scope 值当 ID 会报
  InvalidParameter.ResourceServerScopeIds），且官方姿势要 --force --method POST
- Token 端点错误状态机：未授权RS→400 invalid_request；已授权RS未授权scope→
  400 invalid_scope；RS+scope 全齐→200
"""
import sys

from common import die, info, run_aliyun

PAM_MODULE_KEY = "urn:alibaba:idaas:license:module:pam"
PAM_APP_ID = "iap_pam"
PAM_RS_IDENTIFIER = "urn:cloud:idaas:pam"
PAM_SCOPE_VALUE = "cloud_account_role:obtain_access_credential"


def check_pam_module(region: str, iid: str) -> bool:
    try:
        d = run_aliyun(["eiam", "CheckInstanceModuleStatus", "--region", region,
                        "--InstanceId", iid, "--ModuleKey", PAM_MODULE_KEY])
        return (d.get("Module") or {}).get("ModuleStatus", "") == "enabled"
    except SystemExit:
        info("PAM 模块状态查询失败，按未开通处理")
        return False


def verify_pam_app(region: str, iid: str) -> bool:
    try:
        d = run_aliyun(["eiam", "GetApplication", "--region", region,
                        "--InstanceId", iid, "--ApplicationId", PAM_APP_ID])
        a = d.get("Application", d)
        rs_id = a.get("ResourceServerIdentifier", "")
        info(f"PAM 系统应用: {a.get('ApplicationName')} | RS标识={rs_id} "
             f"| RS状态={a.get('ResourceServerStatus', '')}")
        return rs_id == PAM_RS_IDENTIFIER
    except SystemExit:
        return False


def authorize_rs(region: str, iid: str, client_id: str) -> bool:
    """RS 级授权（幂等）"""
    try:
        run_aliyun(["eiam", "AuthorizeResourceServerToClient", "--region", region,
                    "--InstanceId", iid,
                    "--ClientApplicationId", client_id,
                    "--ResourceServerApplicationId", PAM_APP_ID])
        info("✓ RS 级授权完成")
        return True
    except SystemExit as e:
        msg = str(e)
        if "exist" in msg.lower() or "Already" in msg:
            info("✓ RS 级已授权（幂等跳过）")
            return True
        info(f"RS 级授权失败: {msg[:300]}")
        return False


def find_pam_scope(region: str, iid: str):
    """⚠️ 必须带 --ResourceServerScopeType all，默认查询不返回 PAM 的 scope"""
    try:
        d = run_aliyun(["eiam", "ListResourceServerScopes", "--region", region,
                        "--InstanceId", iid, "--ApplicationId", PAM_APP_ID,
                        "--MaxResults", "50", "--ResourceServerScopeType", "all"])
        for s in d.get("ResourceServerScopes", []):
            if s.get("ResourceServerScopeValue") == PAM_SCOPE_VALUE:
                return s.get("ResourceServerScopeId")
    except SystemExit as e:
        info(f"scope 查询失败: {e}")
    return None


def authorize_scope(region: str, iid: str, client_id: str, scope_id: str) -> bool:
    try:
        run_aliyun(["eiam", "AuthorizeResourceServerScopesToClient",
                    "--force", "--method", "POST",
                    "--region", region, "--InstanceId", iid,
                    "--ClientApplicationId", client_id,
                    "--ResourceServerApplicationId", PAM_APP_ID,
                    "--ResourceServerScopeIds.1", scope_id])
        return True
    except SystemExit as e:
        msg = str(e)
        if "exist" in msg.lower() or "Already" in msg:
            return True
        info(f"scope 级授权失败: {msg[:300]}")
        return False


def main() -> None:
    if len(sys.argv) < 4:
        die("用法: authorize_pam_scope.py <region> <instance_id> <client_app_id>")
    region, iid, client_id = sys.argv[1:4]

    if not check_pam_module(region, iid):
        info("实例未开通 PAM 模块。若只需 M2M Token（不对接 PAM 换 STS），可忽略本步骤。")
        print("PAM_AUTH=module_disabled")
        return

    if not verify_pam_app(region, iid):
        die(f"固定 ID {PAM_APP_ID} 查询失败或 RS 标识不符——PAM 应用可能未初始化")

    if not authorize_rs(region, iid, client_id):
        die("RS 级授权失败，终止")

    scope_id = find_pam_scope(region, iid)
    if not scope_id:
        info(f"⚠️ 未找到 scope {PAM_SCOPE_VALUE}（确认用了 --ResourceServerScopeType all？）")
        info("兜底：控制台 权限中心→功能权限管理→Privileged Access Management→授权该Client→勾选权限项")
        print("PAM_AUTH=scope_not_found")
        return

    if authorize_scope(region, iid, client_id, scope_id):
        info(f"✓ 权限项级授权完成: {client_id} → {PAM_SCOPE_VALUE} ({scope_id})")
        info(f"Token 请求 scope 固定填: {PAM_RS_IDENTIFIER}|{PAM_SCOPE_VALUE}")
        info("提示: 换 STS 还需数据权限（权限中心→数据权限管理: 应用↔目标云角色授权规则）")
        print("PAM_AUTH=auto_done")
    else:
        print("PAM_AUTH=scope_authorize_failed")


if __name__ == "__main__":
    main()
