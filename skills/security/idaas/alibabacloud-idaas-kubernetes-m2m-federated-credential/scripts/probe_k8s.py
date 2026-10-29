#!/usr/bin/env python3
"""探测本机 kubectl 与集群连通性；可达则直接采集 OIDC Discovery 与静态 JWKS。

用法: probe_k8s.py [jwks_out_path]
  jwks_out_path: JWKS 导出路径，默认 /tmp/idaas-k8s-jwks.json

输出末行（供 Agent 解析）:
  K8S_PROBE=ok|no_kubectl|unreachable|no_issuer
  可达时另有: ISSUER=<url>  JWKS_FILE=<path>  JWKS_KEYS=<n>
降级: 任一失败不阻断——Agent 应改用 gen_k8s_commands.py 让用户在控制节点执行后贴回。
"""
import json
import sys
from pathlib import Path

from common import info, try_kubectl


def main() -> None:
    jwks_out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/idaas-k8s-jwks.json"

    p = try_kubectl(["version", "--client=false", "--request-timeout=8s"], timeout=15)
    if p is None:
        info("本机未安装 kubectl")
        print("K8S_PROBE=no_kubectl")
        return
    if p == "timeout" or p.returncode != 0:
        err = "" if p == "timeout" else (p.stderr or "").strip()[:200]
        info(f"集群不可达（Agent 环境常见，正常降级）: {err or '超时'}")
        print("K8S_PROBE=unreachable")
        return

    # OIDC Discovery
    d = try_kubectl(["get", "--raw", "/.well-known/openid-configuration"], timeout=15)
    if d is None or d == "timeout" or d.returncode != 0:
        info("无法获取 OIDC Discovery（API Server 未配置 --service-account-issuer？）")
        print("K8S_PROBE=no_issuer")
        return
    try:
        disc = json.loads(d.stdout)
        issuer = disc.get("issuer", "")
    except json.JSONDecodeError:
        info(f"Discovery 输出非 JSON: {d.stdout[:200]}")
        print("K8S_PROBE=no_issuer")
        return
    if not issuer:
        info("Discovery 中无 issuer 字段")
        print("K8S_PROBE=no_issuer")
        return

    # JWKS 导出
    j = try_kubectl(["get", "--raw", "/openid/v1/jwks"], timeout=15)
    if j is None or j == "timeout" or j.returncode != 0:
        info("无法导出 JWKS（/openid/v1/jwks 不可访问）")
        print(f"ISSUER={issuer}")
        print("K8S_PROBE=no_issuer")
        return
    try:
        jwks = json.loads(j.stdout)
        n_keys = len(jwks.get("keys", []))
    except json.JSONDecodeError:
        info("JWKS 输出非 JSON")
        print("K8S_PROBE=no_issuer")
        return
    Path(jwks_out).write_text(json.dumps(jwks, ensure_ascii=False))

    info(f"✓ 集群可达 | issuer={issuer} | JWKS {n_keys} 个公钥 → {jwks_out}")
    print(f"ISSUER={issuer}")
    print(f"JWKS_FILE={jwks_out}")
    print(f"JWKS_KEYS={n_keys}")
    print("K8S_PROBE=ok")


if __name__ == "__main__":
    main()
