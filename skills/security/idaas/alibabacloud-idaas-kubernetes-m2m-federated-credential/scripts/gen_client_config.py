#!/usr/bin/env python3
"""产出 IDaaS SDK 的 client-config.json 内容与 Java 接入代码样例（原生 K8s OIDC 场景）。

用法: gen_client_config.py <region> <endpoint> <instance_id> <client_id> <cred_name>
                           [role_arn] [out_path]
  endpoint:  实例 DefaultEndpoint（如 rz8w3xcn.aliyunidaas.com），带不带 https:// 均可
  cred_name: 应用联邦凭证名称（须与已创建的凭证完全一致）
  role_arn:  目标云角色 ARN（acs:ram::<账号ID>:role/<角色名>），仅用于代码样例占位
  out_path:  可选，client-config.json 写出路径（默认只打印不落盘）

配置依据《【PAM】原生 Kubernetes 无静态凭据获取 STS Token》步骤 7；
KUBERNETES 部署环境 Token 路径解析优先级: oidcTokenFilePath 字段 >
oidcTokenFilePathEnvVarName 环境变量 > 默认 /var/run/secrets/kubernetes.io/serviceaccount/token
（原生 K8s 默认 SA Token 路径恰为默认值，env 变量按文档保留以兼容 projected token）。
"""
import json
import sys

from common import die

PAM_SCOPE = "urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential"

JAVA_SAMPLE = """// Maven 依赖与版本以 SDK README 为准:
//   https://github.com/cloud-idaas/idaas-java-core-sdk/blob/main/README_zh.md
//   https://github.com/cloud-idaas/idaas-java-akless-alibabacloud-adapter/blob/main/README_zh.md
// Python SDK 接入见对应 README（github.com/cloud-idaas 组织下 python 仓）

public static void main(String[] args) {
    IDaaSCredentialProviderFactory.init();
    AlibabaCloudCredentialsProvider credentialsProvider =
            IDaaSPamAklessCredentialFactory.getAlibabaCloudCredentialsProvider(
                    "{role_arn}"
            );
    CredentialModel credentials = credentialsProvider.getCredentials();
    System.out.println(credentials.getAccessKeyId());
    System.out.println(credentials.getAccessKeySecret());
    System.out.println(credentials.getSecurityToken());
}"""

POD_ENV_NOTE = """# Pod 清单要点（deployment 片段）:
#   env:
#   - name: KUBERNETES_OIDC_TOKEN_FILE
#     value: /var/run/secrets/kubernetes.io/serviceaccount/token
#   配置文件挂载到 ~/.cloud_idaas/client-config.json，
#   或经 JVM -Dcloud_idaas_config_path / 环境变量 CLOUD_IDAAS_CONFIG_PATH 指定路径
#   业务 Pod 需可访问 EIAM 实例公网域名 {endpoint}"""


def main() -> None:
    if len(sys.argv) < 6:
        die("用法: gen_client_config.py <region> <endpoint> <instance_id> "
            "<client_id> <cred_name> [role_arn] [out_path]")
    region, endpoint, iid, client_id, cred_name = sys.argv[1:6]
    role_arn = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else \
        "acs:ram::<账号ID>:role/<角色名>"
    out_path = sys.argv[7] if len(sys.argv) > 7 else ""

    endpoint = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
    base = f"https://{endpoint}/api/v2/iauths_system/oauth2"
    config = {
        "idaasInstanceId": iid,
        "clientId": client_id,
        "issuer": base,
        "tokenEndpoint": f"{base}/token",
        "scope": PAM_SCOPE,
        "openApiEndpoint": f"eiam.{region}.aliyuncs.com",
        "developerApiEndpoint": f"eiam-developerapi.{region}.aliyuncs.com",
        "authnConfiguration": {
            "identityType": "CLIENT",
            "authnMethod": "OIDC",
            "applicationFederatedCredentialName": cred_name,
            "clientDeployEnvironment": "KUBERNETES",
            "oidcTokenFilePathEnvVarName": "KUBERNETES_OIDC_TOKEN_FILE",
        },
        "httpConfiguration": {"connectTimeout": 5000, "readTimeout": 10000},
    }
    text = json.dumps(config, ensure_ascii=False, indent=2)
    print("=== client-config.json ===")
    print(text)
    if out_path:
        with open(out_path, "w") as f:
            f.write(text + "\n")
        print(f"\nCONFIG_FILE={out_path}")
    print("\n=== Java 接入样例 ===")
    print(JAVA_SAMPLE.replace("{role_arn}", role_arn))
    print("\n=== 部署提示 ===")
    print(POD_ENV_NOTE.replace("{endpoint}", endpoint))


if __name__ == "__main__":
    main()
