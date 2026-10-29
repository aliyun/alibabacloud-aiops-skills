#!/usr/bin/env python3
"""探测集群 issuer 是否公网可达（供信任来源模式推荐：可达→「Issuer地址解析(dynamic_from_issuer)」可自动跟随密钥轮换）。

用法: check_issuer_public.py <issuer> [jwks_out_path]
  jwks_out_path: 可达时把抓到的 JWKS 落盘路径，默认 /tmp/idaas-k8s-jwks.json
                 （公网 issuer 场景用户无需手动导出 JWKS，此文件供 kid 陈旧比对等复用检测用）

输出末行: ISSUER_PUBLIC=yes|no ；可达时另有 DISCOVERY_JWKS_URI=<uri> JWKS_KEYS=<n> JWKS_FILE=<path>

⚠️ 本探测仅代表"当前执行环境公网可达"，≈ IDaaS 公网出口大概率也可达；
权威校验以 dynamic 模式创建时 IDaaS 的同步试拉为准（失败报 OBTAIN_JWKS_ERROR 即不可达，降级 static）。
自建集群 issuer（https://kubernetes.default.svc...）DNS 必不解析 → no，属预期。
"""
import json
import subprocess
import sys
from pathlib import Path

from common import die, info


def curl_json(url: str, timeout: int = 10):
    try:
        p = subprocess.run(["curl", "-sS", "--max-time", str(timeout), "-k", url],
                           capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return None
    if p.returncode != 0:
        info(f"curl 失败: {(p.stderr or '').strip()[:150]}")
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        info(f"响应非 JSON: {p.stdout[:150]}")
        return None


def main() -> None:
    if len(sys.argv) < 2:
        die("用法: check_issuer_public.py <issuer> [jwks_out_path]")
    issuer = sys.argv[1].rstrip("/")
    jwks_out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/idaas-k8s-jwks.json"

    disc = curl_json(f"{issuer}/.well-known/openid-configuration")
    if not disc or not disc.get("issuer"):
        print("ISSUER_PUBLIC=no")
        return

    jwks_uri = disc.get("jwks_uri", "")
    info(f"discovery 可达 | issuer={disc.get('issuer')} | jwks_uri={jwks_uri}")
    # 校验 discovery 自报 issuer 与入参一致（不一致则验签会失败，必须提醒）
    if disc.get("issuer") != issuer:
        info(f"⚠️ discovery 自报 issuer 与入参不一致！信任源必须填自报值: {disc.get('issuer')}")
        print(f"DISCOVERY_ISSUER={disc.get('issuer')}")

    # jwks_uri 合法性：host 为空即坏值（ACK 集群内 discovery 实测为 https://:6443/... 形态；
    # 注意 netloc 对 ":6443" 非空，必须用 hostname 判定）
    from urllib.parse import urlparse
    uri_ok = bool(jwks_uri) and jwks_uri.startswith("https://") and bool(urlparse(jwks_uri).hostname)
    if jwks_uri and not uri_ok:
        info(f"⚠️ jwks_uri 非法（host 为空或非 HTTPS）: '{jwks_uri}'——"
             "不可用于「验签公钥地址解析(dynamic_from_jwks_uri)」；"
             "若这是集群内 discovery 的值，请以公网 discovery（本脚本抓取源）为准")
    print(f"JWKS_URI_OK={'yes' if uri_ok else 'no'}")

    n_keys = 0
    jwks_file = ""
    if uri_ok:
        jwks = curl_json(jwks_uri)
        if jwks and isinstance(jwks.get("keys"), list) and jwks["keys"]:
            n_keys = len(jwks["keys"])
            Path(jwks_out).write_text(json.dumps(jwks, ensure_ascii=False))
            jwks_file = jwks_out
            info(f"JWKS 端点可达: {n_keys} 个公钥 → 已存 {jwks_out}（供 kid 比对/静态填充备用）")
        else:
            info("⚠️ jwks_uri 不可达或非 JWKS 格式（dynamic_from_issuer 创建会失败，"
                 "考虑 dynamic_from_jwks_uri 手动指定或 static）")
    print(f"DISCOVERY_JWKS_URI={jwks_uri}")
    print(f"JWKS_KEYS={n_keys}")
    if jwks_file:
        print(f"JWKS_FILE={jwks_file}")
    print("ISSUER_PUBLIC=yes")


if __name__ == "__main__":
    main()
