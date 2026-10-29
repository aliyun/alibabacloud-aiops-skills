#!/usr/bin/env python3
"""解析 K8s SA Token（JWT），自动带入信任源所需参数——aud/iss 等不需要用户手填。

用法: parse_sa_token.py <token_file>
  token_file: SA JWT Token 文件（kubectl create token / Pod 内 cat 的原文）

输出末行（供 Agent 解析与自动填参）:
  ISS=<issuer>                     → 信任源 Issuer 直接带入
  AUD_PRIMARY=<主aud>              → 信任源 Audiences 推荐值（ANY-match 语义，只配一个主值即可）
  AUD_ALL=<逗号分隔全部aud>         → 备查；仅当主 aud 不稳定/多工作负载 audience 不同才考虑多配
  SUB= / NS= / SA= / EXP=          → 凭证 namespace/serviceAccount 带入 + 有效期提醒

主 aud 选择规则：优先取与 issuer 相同的值；否则取数组第一个。
校验语义（源码 jose4j setExpectedAudience）：token.aud ∩ 信任源Audiences ≠ ∅ 即通过；iss 严格相等。
"""
import sys
import time

from common import decode_jwt_payload, die


def main() -> None:
    if len(sys.argv) < 2:
        die("用法: parse_sa_token.py <token_file>")
    with open(sys.argv[1]) as f:
        tok = f.read().strip()
    pl = decode_jwt_payload(tok)
    if not pl:
        die("Token 无法解析为 JWT（应为 header.payload.signature 三段）")

    iss = pl.get("iss", "")
    aud = pl.get("aud")
    auds = aud if isinstance(aud, list) else ([aud] if aud else [])
    if not auds:
        die("Token 缺少 aud claim")
    aud_primary = iss if iss in auds else auds[0]

    k8s = pl.get("kubernetes.io") or {}
    ns = k8s.get("namespace", "")
    sa = (k8s.get("serviceaccount") or {}).get("name", "")
    exp = pl.get("exp", 0)
    exp_str = time.strftime("%F %T", time.localtime(exp)) if exp else "?"
    remain = int((exp - time.time()) // 60) if exp else -1

    print(f"iss:     {iss}")
    print(f"aud:     {auds}  → 主aud: {aud_primary}")
    print(f"sub:     {pl.get('sub', '')}")
    print(f"ns/sa:   {ns} / {sa}")
    print(f"过期时间: {exp_str}" + (f"（剩余 {remain} 分钟）" if remain >= 0 else ""))
    if 0 <= remain < 10:
        print("⚠️ Token 即将过期，建议重新签发后再做换 Token 验证", file=sys.stderr)
    if not k8s:
        print("⚠️ 无 kubernetes.io claims——structured kubernetes 凭证校验会失败，"
              "确认这是 projected/TokenRequest 签发的 SA Token", file=sys.stderr)

    print(f"ISS={iss}")
    print(f"AUD_PRIMARY={aud_primary}")
    print(f"AUD_ALL={','.join(auds)}")
    print(f"SUB={pl.get('sub', '')}")
    print(f"NS={ns}")
    print(f"SA={sa}")
    print(f"EXP={exp_str}")


if __name__ == "__main__":
    main()
