"""aliyun CLI 通道模块：替代 alibabacloud_lhm20250116 SDK 的网络层。

为什么存在：
- LHM 接口不再经 Python SDK 发送，而是通过 `aliyun lhm <command>`
  （aliyun-cli-lhm 插件）发出。协议层与原 SDK 的 ROA 签名等价。
- 本模块保持 SDK 形状的调用契约：
    * `invoke()` 接收 SDK request 模型（取 `to_map()` 里的 query/body 参数）
    * 返回值是属性访问对象（`body.success` / `body.err_code` / `body.data`），
      camelCase 响应自动转 snake_case，业务代码无需改动
    * 失败抛出 AliyunCliError，带 code/message/status_code/request_id，
      与 Tea SDK 异常的字段一致，现有异常处理逻辑可直接复用

运行时依赖：
- aliyun CLI 二进制（含 aliyun-cli-lhm 插件，版本需包含所需命令）
- 凭据通过子进程环境变量传入，不落命令行参数、不进 shell 历史

api-version 自适应：
- 每个命令带首选版本；若插件报
  "not available in the current API version ... Available versions ..."，
  解析提示里的版本号自动重试一次（进程内缓存结果）。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any, Dict, List, Optional

DEFAULT_API_VERSION = "2025-01-16"

# 插件提示可复用版本的原话：
# "Available versions for this command: [2022-11-15]"
_VERSION_HINT_RE = re.compile(
    r"Available versions for this command:\s*\[([^\]]+)\]"
)
_UNKNOWN_FLAG_RE = re.compile(r"unknown flag:\s*(--[a-z0-9-]+)")

# 进程内缓存：command -> 修正后的 api-version
_VERSION_OVERRIDES: Dict[str, str] = {}

# 只在旧 API 版本提供的命令：直接指定首选版本，省掉一次「版本不匹配」的失败调用
_PREFERRED_VERSIONS: Dict[str, str] = {
    "list-meta-data-component-engine": "2022-11-15",
    "get-data-check-engine-relation": "2022-11-15",
    "get-data-check-support-engine-type": "2022-11-15",
}

# 丢弃这些参数会静默改变校验语义（引擎绑定 / 阈值 / 执行参数），
# 插件不认时必须显式失败，而不是像其他参数那样剔除后重试。
_CRITICAL_FLAG_PARAMS = {
    "srcEngineId", "srcEngineName", "srcEngineType",
    "dstEngineId", "dstEngineName", "dstEngineType",
    "totalCountThreshold", "startImmediately",
    "sourceGlobalParams", "targetGlobalParams", "checkGlobalParams",
}


class AliyunCliError(Exception):
    """aliyun CLI 调用失败。字段与 Tea SDK 异常对齐，便于现有 except 复用。"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: Optional[int] = None,
        request_id: str = "",
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(message)


def find_aliyun_binary() -> Optional[str]:
    """定位 aliyun CLI 二进制；找不到返回 None。
    
    沙箱环境中 aliyun CLI 可能被封装为代理，实际调用需要使用 aliyun_real。
    优先检测 aliyun_real，如果存在则使用它；否则回退到 aliyun。
    """
    # 优先使用 aliyun_real（沙箱环境）
    real_binary = shutil.which("aliyun_real")
    if real_binary is not None:
        return real_binary
    # 回退到标准 aliyun CLI
    return shutil.which("aliyun")


def _snake_case(name: str) -> str:
    """camelCase -> snake_case（requestId -> request_id）。"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _kebab_case(name: str) -> str:
    """camelCase -> kebab-case（dataSourceName -> data-source-name）。"""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _normalize_bool(value: Any) -> Any:
    """部分接口把 success 返回成字符串 "true"/"false"，统一成布尔。"""
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


class AttrBody:
    """把 JSON dict 包装成 SDK body 风格的属性访问对象。

    递归转换：嵌套 dict -> AttrBody，list -> list（元素同样处理），
    键名 camelCase -> snake_case。`to_dict()` 可还原为原始结构。
    """

    def __init__(self, mapping: Dict[str, Any]):
        self._fields: Dict[str, Any] = {}
        for key, value in mapping.items():
            self._fields[_snake_case(key)] = _convert(value)
        # 归一化布尔字符串（含 success / errCode 等标量）
        for key, value in list(self._fields.items()):
            if not isinstance(value, (AttrBody, list)):
                self._fields[key] = _normalize_bool(value)

    def __getattr__(self, item: str) -> Any:
        fields = self.__dict__.get("_fields")
        if fields is not None and item in fields:
            return fields[item]
        return None  # SDK 模型对缺省字段返回 None，保持同行为
    
    def __iter__(self):
        # 兼容把 body/data 当容器遍历的写法（如 for item in body.data）
        return iter(self.__dict__.get("_fields") or {})
    
    def __len__(self) -> int:
        return len(self.__dict__.get("_fields") or {})
    
    def __bool__(self) -> bool:
        # 空对象视为真（与 SDK 模型对象一致，避免 `if body.data:` 误判）
        return True

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in self._fields.items():
            if isinstance(value, AttrBody):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if isinstance(item, AttrBody) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


def _convert(value: Any) -> Any:
    if isinstance(value, dict):
        return AttrBody(value)
    if isinstance(value, list):
        return [_convert(item) for item in value]
    return value


def _request_params(request: Any) -> Dict[str, Any]:
    """从 SDK request 模型提取参数（camelCase dict）。

    ROA 请求参数在 to_map() 的 'query' 或 'body' 里；两者都有时合并
    （body 优先，实际接口不会同时使用两处）。普通 dict 直接透传。
    """
    if request is None:
        return {}
    if isinstance(request, dict):
        return dict(request)
    to_map = getattr(request, "to_map", None)
    if to_map is None:
        raise AliyunCliError(
            "CLI_BAD_REQUEST",
            f"request 对象不支持 to_map(): {type(request).__name__}",
        )
    mapped = to_map() or {}
    if "body" in mapped or "query" in mapped:
        # 标准 Tea 结构：{'headers':..,'query':{..},'body':{..}}
        params: Dict[str, Any] = {}
        params.update(mapped.get("query") or {})
        params.update(mapped.get("body") or {})
    else:
        # 本仓库 inner SDK 的 to_map() 直接返回平铺参数 dict
        params = {k: v for k, v in mapped.items() if k != "headers"}
    return {key: value for key, value in params.items() if value is not None}


def _flag_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_env() -> Dict[str, str]:
    """Build subprocess environment inheriting the current credential chain.

    Credentials are resolved through the default credential chain
    (environment variables, RAM Role, ~/.alibabacloud/credentials).
    This function no longer injects AK/SK explicitly.
    """
    return os.environ.copy()


_FALLBACK_SESSION_ID = ""


def _build_user_agent() -> str:
    """Observability UA：AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{version}。

    session-id 优先取环境变量 LHM_SESSION_ID（dispatcher 会话开始时生成一次，
    全会话复用）；未设置时每进程兜底生成一次并缓存，保证 UA 始终存在且
    同进程内多次调用一致。
    """
    global _FALLBACK_SESSION_ID
    session_id = os.environ.get("LHM_SESSION_ID", "").strip()
    if not session_id:
        if not _FALLBACK_SESSION_ID:
            _FALLBACK_SESSION_ID = uuid.uuid4().hex
        session_id = _FALLBACK_SESSION_ID
    version = os.environ.get("LHM_SKILL_VERSION", "").strip() or "1.0.0"
    return f"AlibabaCloud-Agent-Skills/lhm-data-validation-skill/{session_id} skill-version/{version}"


def invoke(
    command: str,
    request: Any = None,
    *,
    endpoint: str,
    region_id: str,
    api_version: str = DEFAULT_API_VERSION,
    timeout: int = 120,
) -> AttrBody:
    """调用 `aliyun lhm <command>`，返回属性访问的响应体。

    Credentials are resolved through the default credential chain
    (environment variables, RAM Role, ~/.alibabacloud/credentials).

    Args:
        command: 插件命令名（kebab-case），如 list-meta-data-component-page。
        request: SDK request 模型或 camelCase dict；None 表示无参调用。
        endpoint / region_id: 连接参数。
        api_version: 首选 API 版本；版本不匹配时按插件提示自动重试。
        timeout: 子进程超时（秒）。

    Returns:
        AttrBody（可用 body.success / body.err_code / body.data 访问）。

    Raises:
        AliyunCliError: CLI 缺失、执行失败、输出无法解析等。
    """
    binary = find_aliyun_binary()
    if binary is None:
        raise AliyunCliError(
            "CLI_NOT_FOUND",
            "未找到 aliyun CLI 二进制，请先安装：https://help.aliyun.com/cli/",
        )

    params = _request_params(request)
    version = _VERSION_OVERRIDES.get(command) or _PREFERRED_VERSIONS.get(
        command, api_version
    )

    # 自适应重试：version 修正 与 unknown flag 剔除，最多各一次
    for attempt in range(3):
        argv: List[str] = [
            binary, "lhm", command,
            "--api-version", version,
            "--region", region_id,
            "--user-agent", _build_user_agent(),
        ]
        if endpoint:
            argv += ["--endpoint", endpoint]
        for key in sorted(params):
            argv += [f"--{_kebab_case(key)}", _flag_value(params[key])]

        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_build_env(),
            )
        except FileNotFoundError:
            raise AliyunCliError("CLI_NOT_FOUND", "aliyun CLI 二进制不可执行")
        except subprocess.TimeoutExpired:
            raise AliyunCliError(
                "CLI_TIMEOUT", f"aliyun CLI 调用超时（{timeout}s）：{command}"
            )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode == 0 and stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError as parse_error:
                raise AliyunCliError(
                    "CLI_BAD_OUTPUT",
                    f"aliyun CLI 输出不是合法 JSON：{stdout[:500]}",
                ) from parse_error
            if not isinstance(payload, dict):
                payload = {"data": payload}
            return AttrBody(payload)

        if attempt < 2:
            hint = _VERSION_HINT_RE.search(stderr)
            if hint and command not in _VERSION_OVERRIDES:
                fixed = hint.group(1).split(",")[0].strip()
                if fixed and fixed != version:
                    _VERSION_OVERRIDES[command] = fixed
                    version = fixed
                    continue
            flag_match = _UNKNOWN_FLAG_RE.search(stderr)
            if flag_match:
                bad_flag = flag_match.group(1)
                camel = "".join(
                    part.capitalize() for part in bad_flag.lstrip("-").split("-")
                )
                camel = camel[:1].lower() + camel[1:]
                if camel in params:
                    if camel in _CRITICAL_FLAG_PARAMS:
                        raise AliyunCliError(
                            "CLI_PARAM_UNSUPPORTED",
                            f"aliyun-cli-lhm 插件不支持参数 {bad_flag}（{camel}）。"
                            f"该参数会影响校验语义，已中止以避免静默丢参。"
                            f"请升级插件后重试：bash scripts/install_lhm_plugin.sh",
                        )
                    print(
                        f"[aliyun-cli] 警告: 插件不支持参数 {bad_flag}，已忽略后重试",
                        file=sys.stderr,
                    )
                    params.pop(camel)
                    continue

        # 从错误输出里尽量提取服务端信息
        code = "CLI_ERROR"
        message = stderr or stdout or f"aliyun CLI 退出码 {proc.returncode}"
        request_id = ""
        if stdout:
            try:
                payload = json.loads(stdout)
                if isinstance(payload, dict):
                    code = str(payload.get("errCode") or payload.get("Code") or code)
                    message = str(
                        payload.get("errMessage")
                        or payload.get("Message")
                        or message
                    )
                    request_id = str(payload.get("requestId") or "")
                    return AttrBody(payload)  # HTTP 200 的业务失败，交回业务层判断
            except json.JSONDecodeError:
                pass
        raise AliyunCliError(code, message, request_id=request_id)

    raise AliyunCliError("CLI_ERROR", "aliyun CLI 调用重试次数耗尽")
