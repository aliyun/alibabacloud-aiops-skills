import hashlib
import json
import os
from typing import List, Dict, Any, Union

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient


def mask_sensitive_DFS(notebook: Union[Dict[str, Any], List[Any]]) -> None:
    # 对 Data 中已知敏感字段进行脱敏处理
    _SENSITIVE_DATA_KEYS = {"Password", "password", "AccessKey", "SecretKey", "ConnectionString", "connectionString"}
    if isinstance(notebook, dict):
        for key in notebook:
            if key in _SENSITIVE_DATA_KEYS and isinstance(notebook[key], str):
                notebook[key] = "******"
            else:
                mask_sensitive_DFS(notebook[key])
        return
    if isinstance(notebook, list):
        for item in notebook:
            mask_sensitive_DFS(item)


class callAliyunOpenAPI:
    def __init__(self):
        pass

    _SKILL_NAME = "alibabacloud-dms-data-agent-platform-setup"
    _UA_TEMPLATE = f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{{session_id}}"

    @staticmethod
    def create_client() -> OpenApiClient:
        """
        使用凭据初始化账号Client，凭据通过默认凭据链自动获取。
        凭据链配置方式请参见：https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials#3ca299f04bw3c
        @return: Client
        @throws Exception
        """
        session_id = os.environ.get("SKILL_SESSION_ID")
        if not session_id:
            raise EnvironmentError(
                "SKILL_SESSION_ID environment variable is not set. "
                "Generate a 32-char hex string once per session and export it."
            )

        # 使用默认凭据链，无需手动传入 AK/SK
        credentialsClient = CredentialClient()

        config = open_api_models.Config(credential=credentialsClient)
        config.user_agent = callAliyunOpenAPI._UA_TEMPLATE.format(session_id=session_id)
        # Endpoint 请参考 https://api.aliyun.com/product/dms-enterprise
        config.endpoint = "dms-enterprise.aliyuncs.com"
        return OpenApiClient(config)

    @staticmethod
    def create_API_info(API_name: str, method_type: str) -> open_api_models.Params:
        """
        API 相关
        @param path: string Path parameters
        @return: OpenApi.Params
        """
        params = open_api_models.Params(
            # 接口名称,
            action=API_name,
            # 接口版本,
            version="2018-11-01",
            # 接口协议,
            protocol="HTTPS",
            # 接口 HTTP 方法,
            method=method_type,
            auth_type="AK",
            style="RPC",
            # 接口 PATH,
            pathname="/",
            # 接口请求体内容格式,
            req_body_type="json",
            # 接口响应体内容格式,
            body_type="json",
        )
        return params

    @staticmethod
    def launch(
        input_dict: Dict[str, Any],
        API_name: str,
        method_type: str='POST'
    ) -> Dict[str, Any]:
        json_body: Dict[str, Any] = input_dict

        # 基于请求参数生成幂等 ClientToken，确保相同参数的重试不会创建重复实例
        client_token = hashlib.sha256(
            json.dumps(json_body, sort_keys=True).encode()
        ).hexdigest()
        json_body["ClientToken"] = client_token

        client = callAliyunOpenAPI.create_client()
        params = callAliyunOpenAPI.create_API_info(API_name, method_type)

        # runtime options
        runtime = util_models.RuntimeOptions(
            connect_timeout=10000,  # 连接超时 10 秒（单位：毫秒）
            read_timeout=30000,  # 读取超时 30 秒（单位：毫秒）
        )
        request = open_api_models.OpenApiRequest(
            query=OpenApiUtilClient.query(json_body)
        )
        # 返回值实际为 Map 类型，可从 Map 中获得三类数据：响应体 body、响应头 headers、HTTP 返回的状态码 statusCode。
        resp: Dict[str, Any] = client.call_api(params, request, runtime)

        return resp

if __name__ == "__main__":
    test_input = {
        "password": "value1",
        "key2": "value2",
        "key3": {
            "password": "value4",
            "key5": "value5"
        }
    }
    mask_sensitive_DFS(test_input)
    print(test_input)
