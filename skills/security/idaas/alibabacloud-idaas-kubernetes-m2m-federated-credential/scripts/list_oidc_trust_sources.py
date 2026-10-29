#!/usr/bin/env python3
"""列出实例下 OIDC 类型的联邦信任源；传入集群 issuer/主aud/JWKS 时自动检测复用候选与 kid 陈旧。

用法: list_oidc_trust_sources.py <region> <instance_id> [issuer] [aud_primary] [jwks_file]
  issuer/aud_primary: 来自 parse_sa_token.py 的 ISS=/AUD_PRIMARY=
  jwks_file:          集群当前 JWKS 文件（私网 issuer 由用户贴回落盘；公网 issuer 由
                      check_issuer_public.py 抓取落盘）——用于比对库内公钥 kid 是否已陈旧

输出: 每行 FCP_ID | 名称 | 信任来源(控制台术语) | Issuer | Audiences | 状态 [| 匹配标记]
末行:
  REUSE_CANDIDATE=<fcp_id>|none|skipped(missing_args)
      <fcp_id>  已比对：issuer 完全一致 且 Audiences 包含主 aud → 可复用
      none      已比对：无匹配候选
      skipped(missing_args)  未传 issuer 参数，**根本没做比对**（纯列表/巡检模式）——
                Agent 不得将此结果当"无候选"用于新建决策，必须带全参数重跑
  REUSE_KID_STALE=<fcp_id>|no|unknown(<原因>)
      <fcp_id>  已比对且库内 JWKS 不含集群当前 kid（密钥已轮换）→ 复用前须先更新 JWKS：
                静态填充用 rotate_static_jwks.py；动态模式等定时刷新或调 refresh API
      no        已比对且 kid 有交集（新鲜）
      unknown(not_checked)      未传 issuer，未做比对
      unknown(no_cluster_jwks)  未提供集群 JWKS 文件，无从比对
      unknown(<jwks_source>)    库内 JWKS 未回显（动态模式经 Get 接口不回显；List 通常回显
                DynamicJwks，但可能为空），无从比对——**不得解读为"已核对且新鲜"**
（同 issuer 重复建源会加重轮换运维负担，静态填充需逐个手动更新——有候选时优先复用）
"""
import json
import sys

from common import info, run_aliyun

JWKS_SOURCE_LABELS = {
    "static": "静态填充(static)",
    "dynamic_from_issuer": "Issuer地址解析(dynamic_from_issuer)",
    "dynamic_from_jwks_uri": "验签公钥地址解析(dynamic_from_jwks_uri)",
}


def jwks_kids(jwks_str: str) -> set:
    try:
        return {k.get("kid") for k in json.loads(jwks_str).get("keys", []) if k.get("kid")}
    except (json.JSONDecodeError, AttributeError, TypeError):
        return set()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("用法: list_oidc_trust_sources.py <region> <instance_id> "
                 "[issuer] [aud_primary] [jwks_file]")
    region, iid = sys.argv[1], sys.argv[2]
    want_issuer = sys.argv[3].strip() if len(sys.argv) > 3 else ""
    want_aud = sys.argv[4].strip() if len(sys.argv) > 4 else ""
    jwks_file = sys.argv[5].strip() if len(sys.argv) > 5 else ""

    cluster_kids = set()
    if jwks_file:
        try:
            with open(jwks_file) as f:
                cluster_kids = jwks_kids(f.read())
        except OSError:
            info(f"集群 JWKS 文件不可读，跳过 kid 比对: {jwks_file}")

    d = run_aliyun(["eiam", "ListFederatedCredentialProviders", "--region", region,
                    "--InstanceId", iid, "--MaxResults", "100"])
    providers = d.get("FederatedCredentialProviders", [])
    oidc = [p for p in providers
            if p.get("FederatedCredentialProviderType") == "oidc"]
    print(f"OIDC 类型信任源 {len(oidc)} 个 (实例信任源总数 {len(providers)}):")

    candidate = "none" if want_issuer else "skipped(missing_args)"
    stale = "no" if want_issuer else "unknown(not_checked)"
    if not want_issuer:
        info("未提供 issuer 参数——本次为纯列表模式，未做复用比对"
             "（REUSE_* 输出为 skipped/unknown，不得用于新建决策）")
    for p in oidc:
        cfg = p.get("OidcProviderConfig") or {}
        auds = cfg.get("Audiences") or []
        src = cfg.get("JwksSource", "?")
        label = JWKS_SOURCE_LABELS.get(src, src)
        mark = ""
        if want_issuer and p.get("Status") == "enabled" and cfg.get("Issuer") == want_issuer:
            if not want_aud or want_aud in auds:
                fcp_id = p["FederatedCredentialProviderId"]
                stored_kids = jwks_kids(cfg.get("StaticJwks") or cfg.get("DynamicJwks") or "")
                if not cluster_kids:
                    kid_state = "unknown(no_cluster_jwks)"
                    mark = " ← 同issuer且aud覆盖；kid未核对(未提供集群JWKS文件)"
                elif not stored_kids:
                    kid_state = f"unknown({src})"
                    mark = (f" ← 同issuer且aud覆盖；kid未核对({label} 库内JWKS未回显，"
                            f"不得视为已核对新鲜)")
                    info(f"⚠️ {fcp_id} 库内 JWKS 为空无法比对 kid（动态模式 Get 不回显；"
                         f"List 的 DynamicJwks 也可能为空）——复用后若集群刚轮换过密钥且定时"
                         f"刷新未跑，验签会失败；可直接尝试换 Token 验证或查 JwksLastObtainedTime")
                elif cluster_kids & stored_kids:
                    kid_state = "no"
                    mark = " ← 同issuer且aud覆盖且kid新鲜，可复用"
                else:
                    kid_state = fcp_id
                    mark = " ← 同issuer且aud覆盖，但库内kid已陈旧(集群密钥已轮换)，复用前须先更新JWKS"
                    info(f"⚠️ {fcp_id} 库内kid={sorted(k[:12] for k in stored_kids)} "
                         f"不含集群当前kid={sorted(k[:12] for k in cluster_kids)}——"
                         f"静态填充用 rotate_static_jwks.py 更新；动态模式等定时刷新/调 refresh API")
                if candidate == "none":
                    candidate, stale = fcp_id, kid_state
            else:
                mark = " ← 同issuer但Audiences不含主aud"
                info(f"{p['FederatedCredentialProviderId']} 同 issuer 但 Audiences={auds} "
                     f"不含 '{want_aud}'（ANY-match 不命中，不可直接复用；"
                     f"可 Update 追加 Audiences 或新建）")
        print(f"{p['FederatedCredentialProviderId']} | "
              f"{p.get('FederatedCredentialProviderName', '')} | "
              f"{label} | {cfg.get('Issuer', '?')} | "
              f"aud={','.join(auds)} | {p.get('Status', '?')}{mark}")
    if not oidc:
        print("(无已有 OIDC 信任源，需新建)")
    print(f"REUSE_CANDIDATE={candidate}")
    print(f"REUSE_KID_STALE={stale}")


if __name__ == "__main__":
    main()
