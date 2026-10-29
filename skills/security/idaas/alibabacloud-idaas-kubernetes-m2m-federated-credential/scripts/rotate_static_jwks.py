#!/usr/bin/env python3
"""静态填充(static)信任源的 JWKS 轮换更新（集群换 SA 签名密钥后的救火命令，全自动回填参数）。

用法: rotate_static_jwks.py <region> <instance_id> <fcp_id> <new_jwks_file>

流程:
1. List 回读该信任源现状（名称/NAE/Issuer/Audiences/JwksSource/旧kid）
2. 校验新 JWKS 文件；JwksSource 非 static 则拒绝（动态模式应等定时刷新或调 refresh API）
3. UpdateFederatedCredentialProvider 全量提交（新 StaticJwks + 原样回填其余参数）

⚠️ 关键坑（2026-10-26 用户生产实测）：Update 是**全量覆盖语义**，
   --FederatedCredentialProviderName 与 --NetworkAccessEndpointId 为必填
   （漏传分别报 MissingFederatedCredentialProviderName / MissingParameter.NetworkAccessEndpoint），
   OidcProviderConfig 各字段也须完整带上（Issuer 服务端会强制保留 DB 旧值）。
   本脚本自动回读回填，避免故障现场手工拼参试错。

输出末行: ROTATED=yes + KIDS_NEW=<逗号分隔> + KIDS_OLD=<逗号分隔>
"""
import json
import sys

from common import die, info, read_jwks_file, run_aliyun


def jwks_kids(jwks_str: str) -> list:
    try:
        d = json.loads(jwks_str)
        return [k.get("kid", "?") for k in d.get("keys", [])]
    except (json.JSONDecodeError, AttributeError):
        return []


def main() -> None:
    if len(sys.argv) < 5:
        die("用法: rotate_static_jwks.py <region> <instance_id> <fcp_id> <new_jwks_file>")
    region, iid, fcp_id, jwks_file = sys.argv[1:5]

    # 1. 回读现状
    d = run_aliyun(["eiam", "ListFederatedCredentialProviders", "--region", region,
                    "--InstanceId", iid, "--MaxResults", "100"])
    target = next((p for p in d.get("FederatedCredentialProviders", [])
                   if p.get("FederatedCredentialProviderId") == fcp_id), None)
    if not target:
        die(f"未找到信任源 {fcp_id}（实例 {iid}）")
    cfg = target.get("OidcProviderConfig") or {}
    src = cfg.get("JwksSource", "")
    if src != "static":
        die(f"该信任源是「{src}」模式，不适用本脚本——动态模式由 IDaaS 定时任务自动刷新；"
            f"急需刷新可调控制台/refresh API（refreshOidcProviderJwks）")
    name = target.get("FederatedCredentialProviderName", "")
    nae = target.get("NetworkAccessEndpointId", "") or "inae_public"
    issuer = cfg.get("Issuer", "")
    auds = cfg.get("Audiences") or []
    old_kids = jwks_kids(cfg.get("StaticJwks", ""))
    info(f"信任源: {name} ({fcp_id}) | NAE={nae} | 旧kid={old_kids}")

    # 2. 校验新 JWKS
    new_jwks = read_jwks_file(jwks_file)
    new_kids = jwks_kids(new_jwks)
    if set(new_kids) == set(old_kids) and old_kids:
        info("⚠️ 新旧 JWKS 的 kid 完全相同——确认导出的是轮换后的新公钥集？仍继续提交")

    # 3. 全量提交 Update
    args = [
        "eiam", "UpdateFederatedCredentialProvider",
        "--force", "--method", "POST",
        "--region", region,
        "--InstanceId", iid,
        "--FederatedCredentialProviderId", fcp_id,
        "--FederatedCredentialProviderName", name,          # 必填！漏传报 MissingFederatedCredentialProviderName
        "--NetworkAccessEndpointId", nae,                   # 必填！漏传报 MissingParameter.NetworkAccessEndpoint
        "--OidcProviderConfig.JwksSource", "static",
        "--OidcProviderConfig.Issuer", issuer,
        "--OidcProviderConfig.StaticJwks", new_jwks,
    ]
    for i, a in enumerate(auds, 1):
        args += [f"--OidcProviderConfig.Audiences.{i}", a]
    if cfg.get("TrustCondition"):
        args += ["--OidcProviderConfig.TrustCondition", cfg["TrustCondition"]]
    args += ["--yes"]

    r = run_aliyun(args)
    print(json.dumps(r, ensure_ascii=False))
    info(f"✓ JWKS 已更新: kid {old_kids} → {new_kids}")
    print(f"KIDS_OLD={','.join(old_kids)}")
    print(f"KIDS_NEW={','.join(new_kids)}")
    print("ROTATED=yes")


if __name__ == "__main__":
    main()
