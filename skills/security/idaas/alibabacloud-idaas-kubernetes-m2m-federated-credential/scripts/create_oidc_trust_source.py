#!/usr/bin/env python3
"""创建 K8s OIDC 联邦信任源，支持三种 JWKS 来源模式（JwksSource）。

用法: create_oidc_trust_source.py <region> <instance_id> <provider_name>
                                  <issuer> <audiences> <jwks_source> [jwks_value]
                                  [nae_id] [trust_condition]
  provider_name:  仅小写字母/数字/下划线/中横线，<=64 字符
  issuer:         集群 OIDC Issuer（discovery 的 issuer 字段原样，HTTPS URL；创建后不可改）
  audiences:      受众标识，逗号分隔 1-5 个；ANY-match 语义（token.aud 与配置交集非空即通过），
                  推荐只配主 aud（优先与 issuer 同值者，或 Token aud 数组第一个），勿全量照传扩大信任面
  jwks_source:    static(控制台名:静态填充) | dynamic_from_issuer(Issuer地址解析) |
                  dynamic_from_jwks_uri(验签公钥地址解析)
  jwks_value:     static → JWKS JSON 文件路径（必填）
                  dynamic_from_jwks_uri → HTTPS 的 JWKS 地址（必填）
                  dynamic_from_issuer → 忽略（创建时 IDaaS 同步试拉 {issuer}/.well-known/
                  openid-configuration → jwks_uri，不可达则创建失败=权威可达性校验）
  nae_id:         网络访问端点 ID，默认 inae_public（OIDC 类型必填；动态模式作为抓取出口，
                  缺省回落公网出口 PUBLIC_NAE）
  trust_condition: 可选信任条件 DSL，如 Equals(jwt.sub, "system:serviceaccount:ns:sa")

输出: 原始响应 + 末行 FCP_ID=fcp_xxx

模式权衡（源码 FederatedCredentialProviderFacadeImpl/Validator 反查）：
- static: 永不联网；集群轮换 SA 签名密钥后须手动 Update 换 StaticJwks（kid miss 直接认证失败，
  无自动重拉）——自建集群（issuer 私网）唯一选择
- dynamic_from_issuer / dynamic_from_jwks_uri: 创建与更新时同步试拉，另有 SchedulerX2 定时任务
  DYNAMIC_OBTAINING_JWKS 周期刷新（自动跟随密钥轮换）；认证热路径只读 DB 缓存不联网；
  抓取失败时创建/更新报错回滚，定时任务失败仅告警并保留旧 JWKS

⚠️ 调用姿势（继承 PKCS#7 实测，勿改）：--force --method POST --yes + 点分扁平参数；
  传 JSON 字符串会被拒（要求 Flat format）。
"""
import json
import re
import sys

from common import die, info, read_jwks_file, run_aliyun

JWKS_SOURCES = ("static", "dynamic_from_issuer", "dynamic_from_jwks_uri")


def main() -> None:
    if len(sys.argv) < 7:
        die("用法: create_oidc_trust_source.py <region> <instance_id> <provider_name> "
            "<issuer> <audiences> <jwks_source> [jwks_value] [nae_id] [trust_condition]")
    region, iid, name, issuer, auds, jwks_source = sys.argv[1:7]
    jwks_value = sys.argv[7] if len(sys.argv) > 7 else ""
    nae_id = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] else "inae_public"
    trust_condition = sys.argv[9] if len(sys.argv) > 9 else ""

    if not re.fullmatch(r"[a-z0-9_-]{1,64}", name):
        die(f"信任源名称仅支持小写字母/数字/下划线/中横线且<=64字符: '{name}'")
    if not re.fullmatch(r"https://.+", issuer):
        die(f"Issuer 必须是 HTTPS URL（原样使用集群 discovery 的 issuer 值）: '{issuer}'")
    aud_list = [a.strip() for a in auds.split(",") if a.strip()]
    if not 1 <= len(aud_list) <= 5:
        die(f"受众标识需 1-5 个（逗号分隔），当前 {len(aud_list)} 个")
    if jwks_source not in JWKS_SOURCES:
        die(f"jwks_source 必须是 {'/'.join(JWKS_SOURCES)}，收到: '{jwks_source}'")

    args = [
        "eiam", "CreateFederatedCredentialProvider",
        "--force", "--method", "POST",
        "--region", region,
        "--InstanceId", iid,
        "--FederatedCredentialProviderType", "oidc",
        "--FederatedCredentialProviderName", name,
        "--NetworkAccessEndpointId", nae_id,
        "--OidcProviderConfig.JwksSource", jwks_source,
        "--OidcProviderConfig.Issuer", issuer,
    ]
    if jwks_source == "static":
        if not jwks_value:
            die("静态填充(static)模式必须提供 JWKS JSON 文件路径")
        jwks = read_jwks_file(jwks_value)
        info(f"[静态填充] JWKS 已校验: {len(json.loads(jwks)['keys'])} 个公钥, {len(jwks)} 字符")
        args += ["--OidcProviderConfig.StaticJwks", jwks]
    elif jwks_source == "dynamic_from_jwks_uri":
        if not jwks_value.startswith("https://"):
            die(f"验签公钥地址解析(dynamic_from_jwks_uri)模式的 jwks_value 必须是 HTTPS URL: '{jwks_value}'")
        info(f"[验签公钥地址解析] 创建时 IDaaS 将同步试拉: {jwks_value}")
        args += ["--OidcProviderConfig.JwksUri", jwks_value]
    else:  # dynamic_from_issuer
        info(f"[Issuer地址解析] 创建时 IDaaS 将同步试拉: {issuer}/.well-known/openid-configuration → jwks_uri")
        info("若创建失败报 OBTAIN_JWKS_ERROR，说明 issuer 对 IDaaS 不可达，请降级「静态填充(static)」模式")

    for i, a in enumerate(aud_list, 1):
        args += [f"--OidcProviderConfig.Audiences.{i}", a]
    if trust_condition:
        args += ["--OidcProviderConfig.TrustCondition", trust_condition]
    args += ["--yes"]

    d = run_aliyun(args)
    print(json.dumps(d, ensure_ascii=False))
    fcp_id = d.get("FederatedCredentialProviderId", "")
    if not fcp_id:
        die(f"创建失败（名称重复？权限不足？JWKS 格式非法？动态模式 issuer/jwks_uri 不可达？）: {d}")
    print(f"FCP_ID={fcp_id}")


if __name__ == "__main__":
    main()
