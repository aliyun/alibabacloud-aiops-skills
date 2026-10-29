#!/usr/bin/env python3
"""生成用户在 K8s 控制节点/业务 Pod 上执行的命令块（kubectl 降级贴回模式）。

用法:
  完整采集（Phase 1）:  gen_k8s_commands.py [namespace] [service_account] [pod_name]
  仅取验证 Token（Phase 3）: gen_k8s_commands.py --token-only <namespace> <service_account> [pod_name]
    --token-only 模式只输出【③ SA Token】引导，且 ns/sa 应传入第 4 轮已确定的实际值
    （命令直接可复制执行，不留占位符）

完整模式请用户贴回产物：
- 必贴：① Issuer ③ SA Token（Token 用于自动解析 aud/iss/ns/sa，信任源参数从中带入）
- 条件贴：② JWKS JSON——仅信任来源选「静态填充(static)」时需要；
  「Issuer地址解析(dynamic_from_issuer)」模式无需此步
"""
import sys

DISCOVERY_CMD = "kubectl get --raw /.well-known/openid-configuration"
JWKS_CMD = "kubectl get --raw /openid/v1/jwks > /tmp/idaas-jwks.json && cat /tmp/idaas-jwks.json"

TEST_POD_YAML = """cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: idaas-token-test
  namespace: {ns}
spec:
  containers:
  - name: shell
    image: registry.cn-hangzhou.aliyuncs.com/acs/busybox:latest
    command: ["sleep", "3600"]
  serviceAccountName: {sa}
  terminationGracePeriodSeconds: 0
EOF"""


def print_token_section(ns: str, sa: str, pod: str, known: bool) -> None:
    """输出取 SA Token 的引导；known=True 时 ns/sa 为已确定实际值（Phase 3），命令直接可执行"""
    ns_show, sa_show = ns or "default", sa or "default"
    print("【③ ServiceAccount Token】")
    print("  方式 A（推荐，无需已有 Pod）：直接为指定 ServiceAccount 签发 Token")
    print(f"    kubectl create token {sa_show} -n {ns_show} --duration=1h")
    if not known:
        print("    # 命令含义: create token <sa> -n <namespace>")
        print("    #   <sa>        = 业务 Pod 使用的 ServiceAccount 名称")
        print("    #   <namespace> = 业务 Pod 所在的命名空间")
        print("    #   两者须与后面创建联邦凭证时填的 Namespace/ServiceAccount 一致")
        print("    # 尚未规划专属 SA 时用集群默认值 default/default（如上），仅限测试；")
        print("    # 生产环境应创建独立 namespace 与 ServiceAccount")
    print("    # ⚠️ --duration=1h 勿省略也不宜更短：projected token 默认仅 1h 有效，")
    print("    #    流程交互耗时可能导致中途过期（过期后换 Token 验证会失败，需重签）")
    print("  方式 B（取业务 Pod 实际挂载的 Token，最贴近运行时真实场景）：")
    if pod:
        print(f"    kubectl exec -n {ns_show} {pod} -- "
              "cat /var/run/secrets/kubernetes.io/serviceaccount/token")
    else:
        if known:
            print(f"    kubectl get pods -n {ns_show}   # 先找到使用该 SA 的业务 Pod")
        print(f"    kubectl exec -n {ns_show if known else '<namespace>'} "
              f"{'<pod名称>'} -- "
              "cat /var/run/secrets/kubernetes.io/serviceaccount/token")
    if not pod and not known:
        print("  （集群尚无业务 Pod 时，也可先建临时测试 Pod 再用方式 B；ns/sa 须与凭证一致，"
              "下例用 default/default）：")
        for line in TEST_POD_YAML.format(ns="default", sa="default").splitlines():
            print(f"    {line}")
        print("    kubectl exec -n default idaas-token-test -- "
              "cat /var/run/secrets/kubernetes.io/serviceaccount/token")
        print("    # 用完清理: kubectl delete pod -n default idaas-token-test")


def main() -> None:
    args = sys.argv[1:]
    token_only = bool(args) and args[0] == "--token-only"
    if token_only:
        args = args[1:]
    ns = args[0] if len(args) > 0 else ""
    sa = args[1] if len(args) > 1 else ""
    pod = args[2] if len(args) > 2 else ""

    if token_only:
        if not (ns and sa):
            sys.exit("用法: gen_k8s_commands.py --token-only <namespace> <service_account> "
                     "[pod_name]（Phase 3 重新签发验证 Token，ns/sa 传联邦凭证的实际值）")
        print("进入最终验证：请重新签发一个新鲜 Token（此前的 Token 可能已在流程交互中过期），"
              "执行以下任一命令并把输出贴回：\n")
        print_token_section(ns, sa, pod, known=True)
        print("\n注意：取到后请尽快贴回，skill 会立即完成换 Token 验证。")
        return

    print("请在能访问集群 API Server 的控制节点依次执行以下命令，并把输出贴回：\n")
    print("【① OIDC Discovery】（输出是一段 JSON，整体贴回即可，skill 会自动解析出 issuer）")
    print(f"  {DISCOVERY_CMD}\n")
    print("【② JWKS 验签公钥集】（⚠️ 仅信任来源选「静态填充」时需要；"
          "选「Issuer地址解析」则跳过此步）")
    print(f"  {JWKS_CMD}\n")
    print_token_section(ns, sa, pod, known=False)
    print("\n注意：SA Token（尤其 projected token）有效期较短，取到后请尽快贴回；"
          "换 Token 验证前建议重新签发一个新鲜的（旧的可能已过期）。")


if __name__ == "__main__":
    main()
