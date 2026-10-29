#!/usr/bin/env python3
"""创建应用联邦凭证（OIDC 类型，kubernetes 结构化校验模式），关联 OIDC 信任源与 M2M Client。

用法: create_k8s_credential.py <region> <instance_id> <app_id> <fcp_id>
                               <cred_name> <namespace> <service_account> [pod_name_prefix] [description]
  namespace/service_account: 业务 Pod 的命名空间与 ServiceAccount（必填，服务端编译为
    And(Equals(jwt.claims.'kubernetes.io'.namespace, "..."), Equals(jwt.claims.'kubernetes.io'.serviceaccount.name, "..."))）
  pod_name_prefix: 可选 Pod 名称前缀（追加 StartsWith 条件）

输出: 原始响应 + 末行 AFC_ID=afc_xxx

⚠️ 关键（源码 ApplicationFederatedCredentialValidator 反查）：
- kubernetes 校验模式 = VerificationMode=structured + OidcVerificationConfig.Profile=kubernetes
  （VerificationMode 无独立 kubernetes 枚举值）
- structured 模式下禁传 VerificationCondition / AttributeMappings（由服务端编译器生成）
- 嵌套参数同样需要 --force --method POST + 点分扁平参数
"""
import json
import re
import sys

from common import die, info, run_aliyun

K8S_NAME_RE = r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?"


def main() -> None:
    if len(sys.argv) < 8:
        die("用法: create_k8s_credential.py <region> <instance_id> <app_id> <fcp_id> "
            "<cred_name> <namespace> <service_account> [pod_name_prefix] [description]")
    region, iid, app_id, fcp_id, name, ns, sa = sys.argv[1:8]
    pod_prefix = sys.argv[8] if len(sys.argv) > 8 else ""
    desc = sys.argv[9] if len(sys.argv) > 9 else "由 skill idaas-kubernetes-m2m-federated-credential 创建"

    if len(name) > 64:
        die(f"凭证名称须 <=64 字符: '{name}'")
    if not re.fullmatch(K8S_NAME_RE, ns):
        die(f"非法 K8s namespace: '{ns}'")
    if not re.fullmatch(K8S_NAME_RE, sa):
        die(f"非法 K8s ServiceAccount 名称: '{sa}'")
    if ns == "default" or sa == "default":
        info("⚠️ 检测到 default namespace/ServiceAccount：仅建议测试环境使用，"
             "生产环境请为应用创建独立 namespace 与 SA")

    args = [
        "eiam", "CreateApplicationFederatedCredential",
        "--force", "--method", "POST",
        "--region", region,
        "--InstanceId", iid,
        "--ApplicationId", app_id,
        "--FederatedCredentialProviderId", fcp_id,
        "--ApplicationFederatedCredentialType", "oidc",
        "--ApplicationFederatedCredentialName", name,
        "--Description", desc,
        "--VerificationMode", "structured",
        "--OidcVerificationConfig.Profile", "kubernetes",
        "--OidcVerificationConfig.KubernetesConfig.Namespace", ns,
        "--OidcVerificationConfig.KubernetesConfig.ServiceAccountName", sa,
    ]
    if pod_prefix:
        args += ["--OidcVerificationConfig.KubernetesConfig.PodNamePrefix", pod_prefix]
    args += ["--yes"]

    d = run_aliyun(args)
    print(json.dumps(d, ensure_ascii=False))
    afc_id = d.get("ApplicationFederatedCredentialId", "")
    if not afc_id:
        die(f"创建联邦凭证失败: {d}")
    print(f"AFC_ID={afc_id}")


if __name__ == "__main__":
    main()
