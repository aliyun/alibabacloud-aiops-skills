# -*- coding: utf-8 -*-
"""
数据校验公共工具模块（网络层：aliyun CLI）

提供客户端构建、响应校验、状态轮询等通用函数。
所有工作流脚本共享此模块。

网络层说明：
- API 调用通过 `aliyun lhm <命令>`（aliyun-cli-lhm 插件）发出，
  协议层与原 Python SDK 的 ROA 签名等价。
- request 模型由本地轻量模块 lhm_models 提供（原 alibabacloud_lhm20250116
  SDK 已废弃、不再安装），仅用于把参数序列化成 to_map() 里的 camelCase dict。
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional, List, Tuple

import yaml

# 本地模块所在目录（与本文件同目录）；确保无论从哪个工作目录加载本模块，
# 都能 import 同目录的 lhm_models（request 模型层）与 aliyun_cli（网络层）。
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# request 模型层：本地轻量实现，替代已废弃、不再安装的 alibabacloud_lhm20250116 SDK。
import lhm_models  # noqa: E402

# 网络层模块：aliyun CLI 通道。
import aliyun_cli  # noqa: E402

from aliyun_cli import AliyunCliError  # noqa: F401,E402  供调用方异常处理复用


# ============================================================================
# 常量
# ============================================================================

EXEC_STATUS_TEXT = {
    0: 'TODO', 1: 'RUNNING', 2: 'STOPPED', 3: 'FAILED', 4: 'FINISHED',
}
CHECK_RESULT_TEXT = {
    0: 'NO_RECORD', 1: 'PASSED', 2: 'FAILED',
}
JOB_STATUS_TEXT = {
    0: 'INIT', 1: 'RUNNING', 2: 'FINISHED', 3: 'STOPPED',
    4: 'FAILED', 6: 'READY', 7: 'SKIPPED',
}
CHECK_TYPE_TEXT = {
    0: '数据量',
    1: '指标',
    2: '弱内容',
    # 3: '自定义',   # 后端未实现，调用会失败
    # 4: '全文',     # 后端未实现，调用会失败
    # 5: '空值率',   # 后端未实现，调用会失败
}


def _log(*args):
    """将进度日志输出到 stderr，避免污染 stdout 中的 JSON。"""
    print(*args, file=sys.stderr)


# ============================================================================
# 客户端
# ============================================================================

# region 逻辑名 → 阿里云 RegionId 的映射
REGION_ID_MAP = {
    'hangzhou': 'cn-hangzhou',
    'cn-hangzhou': 'cn-hangzhou',
    'hz': 'cn-hangzhou',
    'singapore': 'ap-southeast-1',
    'ap-southeast-1': 'ap-southeast-1',
    'sg': 'ap-southeast-1',
}

# region 逻辑名 / RegionId → endpoint 的映射（生产环境）
# 新加坡端点可通过环境变量 LHM_SINGAPORE_ENDPOINT 覆盖，避免端点未定时硬编码死
PROD_ENDPOINT_MAP = {
    'cn-hangzhou': 'lhm.cn-hangzhou.aliyuncs.com',
    'ap-southeast-1': os.environ.get(
        'LHM_SINGAPORE_ENDPOINT', 'lhm.ap-southeast-1.aliyuncs.com'
    ),
}

# lhm-common 统一配置文件路径
CONFIG_DIR = os.path.expanduser('~/.lhm')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'data_validation_config.yaml')


def check_env() -> Tuple[bool, Optional[str]]:
    """
    检查运行环境是否具备 API 调用条件。

    需要：aliyun CLI（含 aliyun-cli-lhm 插件）。
    凭证不在此处检查：由 aliyun CLI 通过默认凭证链自动解析
    （环境变量 / RAM Role / ~/.alibabacloud/credentials）。

    Returns:
        (ok, reason_or_none)
    """
    if aliyun_cli.find_aliyun_binary() is None:
        return False, (
            '未检测到 aliyun CLI，请先安装（要求版本 >= 3.3.8）：'
            'https://help.aliyun.com/cli/'
        )
    plugin_manifest = os.path.expanduser(
        '~/.aliyun/plugins/aliyun-cli-lhm/manifest.json'
    )
    if not os.path.isfile(plugin_manifest):
        return False, (
            'aliyun-cli-lhm 插件未安装。请运行：\n'
            '  aliyun plugin install --names lhm '
            '--source-base https://cli.aliyun-inc.com/registry_id/2/env/pre/plugins'
        )
    return True, None


# ============================================================================
# aliyun CLI 客户端（保持 SDK 形状的调用契约）
# ============================================================================

# 方法名 → 插件命令的特殊映射（默认规则：下划线直接转连字符）
_COMMAND_OVERRIDES = {
    'get_lhm_dwresource_group_status': 'get-lhm-dw-resource-group-status',
}

# 插件 flag 与 SDK request 模型字段名不一致的重命名表：
# command -> {模型序列化出的 camelCase 字段: 插件实际接受的字段}
# GetLhmDWResourceGroupStatus：SDK 模型只有 region_id（序列化为 regionId），
# 而插件命令要求 --biz-region-id，不重命名会被当未知 flag 丢弃导致参数缺失。
_FIELD_OVERRIDES = {
    'get-lhm-dw-resource-group-status': {'regionId': 'bizRegionId'},
}


class _CliResponse:
    """模拟 SDK Response：仅暴露 .body（AttrBody，snake_case 属性访问）。"""

    def __init__(self, body):
        self.body = body


class AliyunCliClient:
    """aliyun CLI 封装的 LHM 客户端。

    与 alibabacloud_lhm20250116 SDK Client 调用形状一致：
    `client.xxx_method(request)` 返回带 `.body` 的响应对象，
    body 支持 snake_case 属性访问（success / err_code / data ...），
    业务代码无需感知底层通道差异。
    """

    def __init__(
        self,
        endpoint: str,
        region_id: str,
    ):
        # Credentials are resolved through the default credential chain;
        # AK/SK are no longer passed explicitly.
        self._endpoint = endpoint
        self._region_id = region_id

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        command = _COMMAND_OVERRIDES.get(name, name.replace('_', '-'))
        field_overrides = _FIELD_OVERRIDES.get(command)

        def _call(request=None):
            payload = request
            if field_overrides and request is not None:
                # 先序列化为参数 dict，再按插件要求重命名字段
                params = aliyun_cli._request_params(request)
                payload = {
                    field_overrides.get(k, k): v for k, v in params.items()
                }
            body = aliyun_cli.invoke(
                command,
                payload,
                endpoint=self._endpoint,
                region_id=self._region_id,
            )
            return _CliResponse(body)

        return _call


# 兼容既有类型注解 / 调用方引用
LhmClient = AliyunCliClient


# credentials.json（LHM 统一配置）候选路径，与其它子技能的 credentials.py 保持一致：
# 会话配置($LHM_SESSION_FILE) > $LHM_CREDENTIALS_FILE > ./config/lhm_credentials.json
# > ~/.lhm/credentials.json
def _credentials_search_paths() -> List[str]:
    paths: List[str] = []
    session_file = os.environ.get('LHM_SESSION_FILE', '').strip()
    if session_file:
        paths.append(os.path.expanduser(session_file))
    explicit = os.environ.get('LHM_CREDENTIALS_FILE', '').strip()
    if explicit:
        paths.append(os.path.expanduser(explicit))
    paths.append(os.path.join('config', 'lhm_credentials.json'))
    paths.append(os.path.join(CONFIG_DIR, 'credentials.json'))
    return paths


def _clean_cfg_value(value) -> str:
    """规整配置值：非字符串 / 空 / 占位符(<...>) 一律视为未填写。"""
    if not isinstance(value, str):
        return ''
    value = value.strip()
    if not value or value.startswith('<'):
        return ''
    return value


def read_lhm_endpoint_region() -> Tuple[str, str]:
    """从 credentials.json 的 `lhm` 段读取固定参数 endpoint / region_id。

    同时兼容嵌套写法 {"lhm": {"endpoint":..,"region_id":..}} 与顶层扁平写法
    {"endpoint":..,"region_id":..}。按 _credentials_search_paths() 顺序取第一个
    存在且可解析的文件。返回 (endpoint, region_id)，缺失时对应项为空串。
    """
    for path in _credentials_search_paths():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        lhm = data.get('lhm')
        lhm = lhm if isinstance(lhm, dict) else {}
        endpoint = _clean_cfg_value(lhm.get('endpoint') or data.get('endpoint'))
        region_id = _clean_cfg_value(lhm.get('region_id') or data.get('region_id'))
        if endpoint or region_id:
            return endpoint, region_id
    return '', ''


def build_client(
    region: Optional[str] = None,
) -> LhmClient:
    """
    构建 LHM 客户端（底层走 aliyun CLI + aliyun-cli-lhm 插件）。

    每条 `aliyun lhm <命令>` 都会带上固定参数 --endpoint / --region，其值优先
    来源于配置文件 credentials.json 的 `lhm` 段（lhm.endpoint / lhm.region_id），
    与其它子技能（lhm-sch-ds / lhm-sch-env / lhm-sch-deploy / lhm-sch-read-exec）对齐。

    Credentials are resolved through the default credential chain
    (environment variables, RAM Role, ~/.alibabacloud/credentials).

    解析优先级：
      region_id：显式入参 region > credentials.json lhm.region_id
                 > 环境变量 REGION_ID > 默认 hangzhou
      endpoint ：credentials.json lhm.endpoint > 环境变量 LHM_ENDPOINT
                 > 由 region_id 映射(PROD_ENDPOINT_MAP)/推导

    Args:
        region: 中心节点逻辑名或 RegionId（如 'hangzhou'/'sg'/'cn-hangzhou'）。
                仅在调用方显式指定时覆盖 credentials.json 的 region_id；
                为 None 时以 credentials.json / 环境变量为准。
    """
    cfg_endpoint, cfg_region_id = read_lhm_endpoint_region()

    # region_id：显式入参优先，其次 credentials.json，再次环境变量，最后默认杭州
    region_source = (
        (region or '').strip()
        or cfg_region_id
        or os.environ.get('REGION_ID', '').strip()
        or 'hangzhou'
    )
    region_key = region_source.lower()
    region_id = REGION_ID_MAP.get(region_key)
    if region_id is None:
        # 允许直接给出合法 RegionId（如 credentials.json 里写 cn-shanghai）
        if '-' in region_source:
            region_id = region_source
        else:
            raise RuntimeError(
                f"不支持的 region: {region_source!r}。支持: "
                f"{', '.join(sorted(set(REGION_ID_MAP.values())))}"
            )

    # endpoint：credentials.json 优先，其次环境变量，最后按 region_id 映射/推导
    endpoint = (
        cfg_endpoint
        or os.environ.get('LHM_ENDPOINT', '').strip()
        or PROD_ENDPOINT_MAP.get(region_id)
        or f'lhm.{region_id}.aliyuncs.com'
    )

    return AliyunCliClient(endpoint, region_id)


# ============================================================================
# 配置文件管理 (lhm-common)
# ============================================================================

def load_config(config_path: Optional[str] = None) -> dict:
    """
    从 ~/.lhm/data_validation_config.yaml 加载配置。

    Args:
        config_path: 配置文件路径，默认使用 CONFIG_PATH

    Returns:
        配置字典。文件不存在时返回空字典。
    """
    path = config_path or CONFIG_PATH
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def save_config(cfg: dict, config_path: Optional[str] = None) -> None:
    """将配置写入 data_validation_config.yaml。"""
    path = config_path or CONFIG_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def resolve_data_source(alias: str, config_path: Optional[str] = None) -> Tuple[str, str, str]:
    """
    从 data_validation_config.yaml 中按别名解析数据源。

    Args:
        alias: 数据源别名（如 'mc_source'）
        config_path: 配置文件路径，默认 CONFIG_PATH

    Returns:
        (ds_id, ds_name, ds_type) 元组

    Raises:
        RuntimeError: 别名不存在时抛出
    """
    cfg = load_config(config_path)
    ds_list = cfg.get('data_sources', [])
    for ds in ds_list:
        if ds.get('alias') == alias:
            return (ds['ds_id'], ds['ds_name'], ds['ds_type'])
    available = [d.get('alias', '?') for d in ds_list]
    raise RuntimeError(
        f'数据源别名 {alias!r} 未在 data_validation_config.yaml 中定义。'
        f'可用别名: {", ".join(available) if available else "(无)"}。'
        f'请运行 lhm-common config add-ds 添加。'
    )


def build_client_from_config(
    config_path: Optional[str] = None,
    region: Optional[str] = None,
) -> LhmClient:
    """
    从 data_validation_config.yaml 构建客户端。

    Credentials are resolved through the default credential chain;
    AK/SK are no longer accepted as parameters.

    Args:
        config_path: 配置文件路径
        region: 覆盖 region

    Returns:
        LhmClient 实例
    """
    cfg = load_config(config_path)
    api_cfg = cfg.get('api', {})

    # 不再强制默认 'hangzhou'：留空时让 build_client 回落到 credentials.json 的
    # lhm.region_id / lhm.endpoint，保证固定参数来源与其它子技能一致。
    rgn = region or api_cfg.get('region')

    return build_client(region=rgn)


# ============================================================================
# 资源组 / 服务代理状态检查 (lhm-common)
# ============================================================================

# Agent 状态枚举：只有 Online 视为可用
AGENT_STATUS_ONLINE = 'Online'
AGENT_STATUS_VALUES = [
    'Online', 'Offline', 'Not_Started', 'Started',
    'Installing', 'Stopped', 'Install_Failed',
]

# 资源组状态枚举：只有 Normal 视为健康
RG_STATUS_HEALTHY = 'Normal'
RG_STATUS_VALUES = [
    'Normal', 'Stop', 'Creating', 'Updating', 'Starting',
    'CreateFailed', 'UpdateFailed', 'Deleted', 'Deleting',
    'DeleteFailed', 'Freezed', 'Timeout',
]


def check_resource_group_status(client: LhmClient, region_id: str) -> dict:
    """
    查询 DataWorks 资源组绑定状态。

    调用 GetLhmDWResourceGroupStatus(region_id) API。
    response.body.data 为纯字符串（资源组状态），直接比对。

    Returns:
        {
            "ok": True,
            "bound": bool,       # data 非空即已绑定
            "status": str,       # 状态字符串
            "is_healthy": bool,  # status == "Normal"
        }
    """
    try:
        req = lhm_models.GetLhmDWResourceGroupStatusRequest(region_id=region_id)
        resp = client.get_lhm_dwresource_group_status(req)
        check_resp(resp, 'GetLhmDWResourceGroupStatus')
        data = resp.body.data or ''
        return {
            'ok': True,
            'bound': bool(data),
            'status': data,
            'is_healthy': data == RG_STATUS_HEALTHY,
        }
    except Exception as e:
        return {
            'ok': False,
            'bound': False,
            'status': '',
            'is_healthy': False,
            'error': str(e),
        }


def check_agent_status(client: LhmClient, agent_type: int = 1) -> dict:
    """
    查询服务代理在线状态。

    调用 GetLhmAgentStatus(agent_type) API。
    response.body.data 为纯字符串（Agent 状态），直接比对。

    Returns:
        {
            "ok": True,
            "configured": bool,   # data 非空即已配置
            "status": str,        # 状态字符串
            "is_online": bool,    # status == "Online"
        }
    """
    try:
        req = lhm_models.GetLhmAgentStatusRequest(agent_type=agent_type)
        resp = client.get_lhm_agent_status(req)
        check_resp(resp, 'GetLhmAgentStatus')
        data = resp.body.data or ''
        return {
            'ok': True,
            'configured': bool(data),
            'status': data,
            'is_online': data == AGENT_STATUS_ONLINE,
        }
    except Exception as e:
        return {
            'ok': False,
            'configured': False,
            'status': '',
            'is_online': False,
            'error': str(e),
        }


# ============================================================================
# 响应校验
# ============================================================================

def check_resp(resp, action: str):
    """统一响应校验：success=False 时抛异常。"""
    if not resp.body.success:
        raise RuntimeError(
            f'[{action}] 失败: '
            f'errCode={resp.body.err_code}, '
            f'errMessage={resp.body.err_message}, '
            f'requestId={resp.body.request_id}'
        )


# ============================================================================
# 校验引擎（Engine）
# ============================================================================
#
# 背景：AddDataCheckTask / add-data-check-task 没有引擎参数，通过 API 创建的任务
# srcEngineId / dstEngineId 恒为空。后端此时会回落成「拿数据源自身当引擎」
# （DbModel.getEngineInfo()），MaxCompute 场景直接抛
#   [RuntimeException]No default project specified.
# 且该错误只在 job/step 的 err_message 里可见。
#
# 因此这里在「建任务之后、写表配置之前」用 UpdateDataCheckTask 补上引擎：
# 表配置行与批次都会从当时的任务记录拷贝引擎字段，晚了就补不上。

# 兜底表：这些数据源类型缺引擎会直接失败，必须严格校验（依据后端 base_ds_engine_rel）。
# 其他类型（MySQL/StarRocks 等）回落到数据源自身即可正常工作，因此不强制。
ENGINE_REQUIRED_DS_TYPES = {
    'maxcompute', 'hive', 'kudu', 'iceberg', 'emrserverlessspark',
}

_ENGINE_ID_KEYS = ('id', 'engine_id', 'ds_id', 'datasource_id', 'component_id')
_ENGINE_NAME_KEYS = (
    'name', 'engine_name', 'ds_name', 'datasource_name', 'component_name',
)
_ENGINE_TYPE_KEYS = ('engine_type', 'type', 'ds_type', 'datasource_type')


class EngineResolveError(RuntimeError):
    """校验引擎无法确定（0 个 / 多个候选）时抛出，消息里带可执行的修复指引。"""


def _as_dict(obj) -> dict:
    """把 AttrBody / dict 统一成 dict。"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, 'to_dict', None)
    if to_dict is not None:
        try:
            return to_dict()
        except Exception:
            return {}
    return {}


def _pick(d: dict, keys) -> Optional[str]:
    """按候选 key 顺序取第一个非空值（兼容 snake_case / camelCase）。"""
    for key in keys:
        val = d.get(key)
        if val not in (None, ''):
            return str(val)
    return None


def normalize_engine_item(item) -> Optional[Tuple[str, str, str]]:
    """把引擎列表的一项归一成 (engine_id, engine_name, engine_type)。"""
    d = _as_dict(item)
    engine_id = _pick(d, _ENGINE_ID_KEYS)
    if not engine_id:
        return None
    engine_name = _pick(d, _ENGINE_NAME_KEYS) or engine_id
    engine_type = _pick(d, _ENGINE_TYPE_KEYS) or ''
    if engine_type.isdigit():
        # componentType 这类数字字段不是引擎类型
        engine_type = ''
    return (engine_id, engine_name, engine_type)


def list_ds_engine_types(
    client: LhmClient,
    ds_type: str,
    check_type: Optional[int] = None,
    template_id: Optional[str] = None,
) -> List[str]:
    """
    查询模板允许的引擎类型（GetDataCheckEngineRelation，api-version 2022-11-15）。

    Returns:
        引擎类型列表；返回 [] 表示该数据源类型无需绑定引擎（或接口无数据）。
    """
    params = {'dsType': ds_type}
    if check_type is not None:
        params['checkType'] = check_type
    if template_id:
        params['templateId'] = template_id
    resp = client.get_data_check_engine_relation(params)
    check_resp(resp, 'GetDataCheckEngineRelation')
    engine_types: List[str] = []
    for row in (resp.body.data or []):
        d = _as_dict(row)
        rel_ds_type = _pick(d, ('ds_type', 'dsType')) or ''
        if rel_ds_type and rel_ds_type.lower() != str(ds_type).lower():
            continue
        for t in (d.get('engine_types') or d.get('engineTypes') or []):
            if t and t not in engine_types:
                engine_types.append(t)
    return engine_types


def list_engine_datasources(
    client: LhmClient,
    ds_type: str,
    engine_types: Optional[List[str]] = None,
    ds_id: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """
    查询可用的校验引擎数据源（ListMetaDataComponentEngine），即控制台「校验引擎」下拉框。

    注意：不传 engineTypeList —— 它是 CLI 的 list 类型 flag（要求空格分隔多值），
    JSON 序列化后插件无法解析，因此改为拉回结果后在本地按 engine_types 过滤。
    """
    params = {'dsType': ds_type}
    if ds_id:
        params['id'] = ds_id
    resp = client.list_meta_data_component_engine(params)
    check_resp(resp, 'ListMetaDataComponentEngine')
    allowed = {str(t).lower() for t in (engine_types or [])}
    result: List[Tuple[str, str, str]] = []
    for item in (resp.body.data or []):
        engine = normalize_engine_item(item)
        if engine is None:
            continue
        # 引擎类型未知时不过滤，避免因字段名差异误杀候选
        if allowed and engine[2] and engine[2].lower() not in allowed:
            continue
        if engine not in result:
            result.append(engine)
    return result


def resolve_engine_alias(
    alias: str, config_path: Optional[str] = None
) -> Optional[Tuple[str, str, str]]:
    """从 data_sources 别名条目里读取引擎三要素（engine_id / engine_name / engine_type）。"""
    cfg = load_config(config_path)
    for ds in cfg.get('data_sources', []):
        if ds.get('alias') != alias:
            continue
        engine_id = ds.get('engine_id')
        if not engine_id:
            return None
        return (
            str(engine_id),
            str(ds.get('engine_name') or engine_id),
            str(ds.get('engine_type') or ds.get('ds_type') or ''),
        )
    return None


def build_engine_arg(
    engine_alias: Optional[str] = None,
    engine_id: Optional[str] = None,
    engine_name: Optional[str] = None,
    engine_type: Optional[str] = None,
    config_path: Optional[str] = None,
) -> Optional[Tuple[str, str, str]]:
    """把命令行传入的引擎参数（别名 或 id/name/type）归一成三元组。"""
    if engine_alias:
        engine = resolve_engine_alias(engine_alias, config_path)
        if engine is None:
            raise RuntimeError(
                f'数据源别名 {engine_alias!r} 未配置引擎信息。请补充：\n'
                f'  lhm-common config add-ds --alias {engine_alias} ... '
                f'--engine-id <id> --engine-name <name> --engine-type <type>'
            )
        return engine
    if engine_id:
        return (str(engine_id), str(engine_name or engine_id), str(engine_type or ''))
    return None


def recall_engine_choice(
    ds_id: str, check_type: Optional[int] = None, config_path: Optional[str] = None
) -> Optional[Tuple[str, str, str]]:
    """回忆上次为该数据源成功用过的引擎（写在配置的 engine_choices 段）。"""
    cfg = load_config(config_path)
    for item in cfg.get('engine_choices', []):
        if str(item.get('ds_id')) != str(ds_id):
            continue
        if item.get('check_type') not in (None, check_type):
            continue
        engine_id = item.get('engine_id')
        if engine_id:
            return (
                str(engine_id),
                str(item.get('engine_name') or engine_id),
                str(item.get('engine_type') or ''),
            )
    return None


def remember_engine_choice(
    ds_id: str,
    engine: Optional[Tuple[str, str, str]],
    check_type: Optional[int] = None,
    config_path: Optional[str] = None,
) -> None:
    """记住引擎选择，下次同一数据源直接复用，无需再查/再问。"""
    if not engine:
        return
    try:
        cfg = load_config(config_path)
        choices = cfg.setdefault('engine_choices', [])
        entry = {
            'ds_id': str(ds_id),
            'check_type': check_type,
            'engine_id': engine[0],
            'engine_name': engine[1],
            'engine_type': engine[2],
        }
        for i, item in enumerate(choices):
            if (str(item.get('ds_id')) == str(ds_id)
                    and item.get('check_type') == check_type):
                choices[i] = entry
                break
        else:
            choices.append(entry)
        save_config(cfg, config_path)
    except Exception as e:
        # 记忆失败不影响主流程
        _log(f'  [engine] 记录引擎选择失败（忽略）: {e}')


def resolve_engine(
    client: LhmClient,
    ds: Tuple[str, str, str],
    check_type: Optional[int] = None,
    template_id: Optional[str] = None,
    prefer: Optional[Tuple[str, str, str]] = None,
    side: str = 'src',
    config_path: Optional[str] = None,
) -> dict:
    """
    解析某一端应绑定的校验引擎。

    消歧顺序：显式指定 > 记忆里的选择 > 唯一候选；仍不唯一时：
    - 强类型（MaxCompute/Hive 等，缺引擎必失败）抛 EngineResolveError，列出候选；
    - 其他类型保持老行为（引擎留空、回落数据源自身），只打警告。

    Returns:
        {'required': bool, 'strict': bool, 'engine': (id,name,type)|None,
         'source': str|None, 'engine_types': [...], 'candidates': [...],
         'warning': str|None}
    """
    ds_id, _ds_name, ds_type = ds
    strict = str(ds_type).lower() in ENGINE_REQUIRED_DS_TYPES
    info = {
        'required': False, 'strict': strict, 'engine': None, 'source': None,
        'engine_types': [], 'candidates': [], 'warning': None,
    }

    if prefer:
        info.update(required=True, engine=tuple(prefer), source='explicit')
        return info

    # 1) 该数据源类型是否需要引擎
    try:
        engine_types = list_ds_engine_types(client, ds_type, check_type, template_id)
    except Exception as e:
        engine_types = []
        _log(f'  [engine] {side} 查询引擎类型失败，改用内置判断: {e}')
    info['engine_types'] = engine_types
    info['required'] = bool(engine_types) or strict
    if not info['required']:
        return info

    # 2) 记忆里的选择
    remembered = recall_engine_choice(ds_id, check_type, config_path)
    if remembered:
        info.update(engine=remembered, source='remembered')
        return info

    # 3) 查候选并按数量决策
    try:
        candidates = list_engine_datasources(client, ds_type, engine_types)
    except Exception as e:
        if strict:
            raise
        info['warning'] = f'{side} 端查询可用引擎失败，引擎留空（沿用旧行为）: {e}'
        _log(f'  [engine] {info["warning"]}')
        return info
    info['candidates'] = candidates

    if len(candidates) == 1:
        info.update(engine=candidates[0], source='unique')
    elif not candidates:
        msg = (
            f'{side} 端数据源类型 {ds_type} 需要绑定校验引擎'
            f'（允许类型: {", ".join(engine_types) or "未知"}），但账号下查不到可用引擎。\n'
            f'请先在 LHM 控制台注册对应计算引擎，或显式指定：\n'
            f'  --{side}-engine-id <id> --{side}-engine-name <name> '
            f'--{side}-engine-type <type>'
        )
        if strict:
            raise EngineResolveError(msg)
        info['warning'] = msg
        _log(f'  [engine] {msg}')
    else:
        listed = '\n'.join(
            f'  - id={c[0]}  name={c[1]}  type={c[2] or "?"}' for c in candidates
        )
        msg = (
            f'{side} 端有 {len(candidates)} 个可用校验引擎，不做猜测，请指定其中一个：\n'
            f'{listed}\n'
            f'指定方式: --{side}-engine-id <id> --{side}-engine-name <name> '
            f'--{side}-engine-type <type>\n'
            f'（指定一次后会记录到 {CONFIG_PATH} 的 engine_choices，后续自动复用）'
        )
        if strict:
            raise EngineResolveError(msg)
        info['warning'] = msg
        _log(f'  [engine] {msg}')

    if info['engine'] and str(info['engine'][0]) == str(ds_id):
        info['warning'] = (
            f'{side} 端解析到的引擎与数据源是同一条记录（id={ds_id}），'
            f'绑定它不会改变后端执行行为。若仍报 "No default project specified"，'
            f'说明该数据源本身缺少默认 project，需要在 LHM 控制台补齐。'
        )
    return info


def bind_task_engine(
    client: LhmClient,
    task_id: int,
    src_engine: Optional[Tuple[str, str, str]] = None,
    dst_engine: Optional[Tuple[str, str, str]] = None,
) -> None:
    """
    给任务绑定校验引擎（UpdateDataCheckTask）。

    只传 id + 引擎字段即可：后端 updateById 走 MyBatis-Plus NOT_NULL 策略，
    未传字段不会被清空（与模板 update 会清空 metricRules 的坑不同）。
    """
    params = {'id': task_id}
    if src_engine:
        params['srcEngineId'] = src_engine[0]
        params['srcEngineName'] = src_engine[1]
        if src_engine[2]:
            params['srcEngineType'] = src_engine[2]
    if dst_engine:
        params['dstEngineId'] = dst_engine[0]
        params['dstEngineName'] = dst_engine[1]
        if dst_engine[2]:
            params['dstEngineType'] = dst_engine[2]
    if len(params) == 1:
        return
    resp = client.update_data_check_task(params)
    check_resp(resp, 'UpdateDataCheckTask')


def get_task_engine(client: LhmClient, task_id: int) -> dict:
    """回读任务当前绑定的引擎（GetDataCheckTaskConfig）。"""
    resp = client.get_data_check_task_config({'taskId': task_id})
    check_resp(resp, 'GetDataCheckTaskConfig')
    d = _as_dict(resp.body.data)
    return {
        'src_engine_id': _pick(d, ('src_engine_id', 'srcEngineId')),
        'src_engine_name': _pick(d, ('src_engine_name', 'srcEngineName')),
        'src_engine_type': _pick(d, ('src_engine_type', 'srcEngineType')),
        'dst_engine_id': _pick(d, ('dst_engine_id', 'dstEngineId')),
        'dst_engine_name': _pick(d, ('dst_engine_name', 'dstEngineName')),
        'dst_engine_type': _pick(d, ('dst_engine_type', 'dstEngineType')),
    }


def ensure_task_engine(
    client: LhmClient,
    task_id: int,
    src_ds: Tuple[str, str, str],
    dst_ds: Tuple[str, str, str],
    check_type: Optional[int] = None,
    template_id: Optional[str] = None,
    src_engine: Optional[Tuple[str, str, str]] = None,
    dst_engine: Optional[Tuple[str, str, str]] = None,
    auto: bool = True,
    config_path: Optional[str] = None,
) -> dict:
    """
    建任务之后立刻完成：解析引擎 → 绑定 → 回读断言。

    必须在 add_data_check_config / exec_data_check_save_task **之前**调用。

    Returns:
        引擎信息 dict（含 bound 回读结果与 warnings），供调用方输出到 JSON。
    """
    result = {'auto': auto, 'src': None, 'dst': None, 'bound': {}, 'warnings': []}
    if not auto and not src_engine and not dst_engine:
        _log('  [engine] 跳过引擎绑定（auto=False 且未显式指定）')
        result['skipped'] = True
        return result

    src_info = resolve_engine(
        client, src_ds, check_type, template_id,
        prefer=src_engine, side='src', config_path=config_path,
    )
    dst_info = resolve_engine(
        client, dst_ds, check_type, template_id,
        prefer=dst_engine, side='dst', config_path=config_path,
    )
    result['src'] = src_info
    result['dst'] = dst_info
    for info in (src_info, dst_info):
        if info.get('warning'):
            result['warnings'].append(info['warning'])

    bind_task_engine(client, task_id, src_info['engine'], dst_info['engine'])
    for side, info in (('src', src_info), ('dst', dst_info)):
        if info['engine']:
            _log(
                f'  [engine] {side} -> id={info["engine"][0]} '
                f'name={info["engine"][1]} type={info["engine"][2] or "?"}'
                f'（来源: {info["source"]}）'
            )

    # 回读断言：需要引擎却没绑上就当场失败，不让它跑到 worker 阶段才炸
    bound = get_task_engine(client, task_id)
    result['bound'] = bound
    for side, info in (('src', src_info), ('dst', dst_info)):
        if info['strict'] and not bound.get(f'{side}_engine_id'):
            raise EngineResolveError(
                f'{side} 端需要校验引擎，但任务 {task_id} 回读后引擎仍为空，已中止。\n'
                f'请确认 aliyun-cli-lhm 插件支持 update-data-check-task 的引擎参数，'
                f'或手动执行：\n'
                f'  aliyun lhm update-data-check-task --api-version 2025-01-16 '
                f'--id {task_id} --{side}-engine-id <id> '
                f'--{side}-engine-name <name> --{side}-engine-type <type>'
            )

    for ds, info in ((src_ds, src_info), (dst_ds, dst_info)):
        if info['engine'] and info['source'] in ('explicit', 'unique'):
            remember_engine_choice(ds[0], info['engine'], check_type, config_path)
    return result


# ============================================================================
# 轮询
# ============================================================================

def poll_exec_status(
    client: LhmClient,
    task_id: int,
    batch_id: int,
    timeout_sec: int = 1800,
    interval_sec: int = 5,
    max_retries: int = 3,
) -> int:
    """
    轮询执行状态直到终态（2/3/4），返回最终 exec_status。

    自适应间隔策略：前 60s 使用 interval_sec，之后每轮递增 2s，上限 30s。
    批量任务通常耗时较长，自适应策略可减少不必要的 API 调用。
    连接异常时自动重试（指数退避），最多 max_retries 次。
    """
    deadline = time.time() + timeout_sec
    current_interval = interval_sec
    elapsed = 0
    consecutive_errors = 0
    while True:
        request = lhm_models.ListDataCheckTaskHistoryRequest(
            task_id=task_id,
            batch_id=batch_id,
            page_index=1,
            page_size=10,
        )
        try:
            resp = client.list_data_check_task_history(request)
            check_resp(resp, 'ListDataCheckTaskHistory')
            consecutive_errors = 0  # 成功后重置错误计数
            rows = resp.body.data or []
            if rows:
                row = rows[0]
                status = row.exec_status
                print(
                    f'  [轮询] batchId={row.batch_id} '
                    f'execStatus={status}({EXEC_STATUS_TEXT.get(status, "?")}) '
                    f'checkResult={row.check_result}({CHECK_RESULT_TEXT.get(row.check_result, "?")}) '
                    f'progress={row.progress}',
                    file=sys.stderr,
                )
                if status in (2, 3, 4):
                    return status
        except Exception as e:
            consecutive_errors += 1
            if consecutive_errors > max_retries:
                _log(f'  [轮询] 连续 {consecutive_errors} 次连接异常，放弃: {e}')
                raise
            retry_wait = min(current_interval * (2 ** consecutive_errors), 60)
            print(
                f'  [轮询] 连接异常 ({consecutive_errors}/{max_retries}), '
                f'{retry_wait}s 后重试: {e}',
                file=sys.stderr,
            )
            time.sleep(retry_wait)
            continue
        if time.time() > deadline:
            _log(f'  [轮询] 超时 ({timeout_sec}s)')
            return -1
        time.sleep(current_interval)
        elapsed += current_interval
        if elapsed > 60:
            current_interval = min(current_interval + 2, 30)


# ============================================================================
# 场景 1：一键执行校验
# ============================================================================

def run_count_check(
    client: LhmClient,
    task_name: str,
    src_ds: Tuple[str, str, str],
    dst_ds: Tuple[str, str, str],
    tables: List[Tuple[str, str, str, str]],
    threshold: Optional[float] = None,
    source_global_params: Optional[str] = None,
    target_global_params: Optional[str] = None,
    src_engine: Optional[Tuple[str, str, str]] = None,
    dst_engine: Optional[Tuple[str, str, str]] = None,
    auto_bind_engine: bool = True,
    engines_out: Optional[dict] = None,
) -> Tuple[int, int]:
    """
    一键执行逐表数据量校验。

    自动串联：创建任务 → 逐表配置 → 保存批次 → 立即执行

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        task_name: 任务名称（仅允许英文字母、中文汉字、数字）
        src_ds: (src_ds_id, src_ds_name, src_ds_type) 元组
        dst_ds: (dst_ds_id, dst_ds_name, dst_ds_type) 元组
        tables: [(source_table, target_table, source_partition, target_partition), ...]
                分区可为空字符串表示整表校验
        threshold: 数据量阈值。切勿传 0.0（表示一致率 >= 0% 即通过，全部误判 PASSED）；
                   None = 不传，使用系统默认精确匹配；或传 100
        source_global_params: 源端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）
        target_global_params: 目标端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）

    Returns:
        (task_id, batch_id)
    """
    # Step 1: 创建任务
    resp = client.add_data_check_task(lhm_models.AddDataCheckTaskRequest(
        task_name=task_name,
        check_type=0,
        task_mode=0,
        src_ds_id=src_ds[0], src_ds_name=src_ds[1], src_ds_type=src_ds[2],
        dst_ds_id=dst_ds[0], dst_ds_name=dst_ds[1], dst_ds_type=dst_ds[2],
    ))
    check_resp(resp, 'AddDataCheckTask')
    task_id = resp.body.data
    _log(f'[一键执行] taskId={task_id}')

    # Step 1.05: 绑定校验引擎（必须在写表配置之前，配置行会拷贝任务上的引擎字段）
    engine_info = ensure_task_engine(
        client, task_id, src_ds, dst_ds,
        check_type=0,
        src_engine=src_engine, dst_engine=dst_engine,
        auto=auto_bind_engine,
    )
    if engines_out is not None:
        engines_out.update(engine_info)

    # Step 1.1: 逐表配置
    for i, (src_table, dst_table, src_part, dst_part) in enumerate(tables, 1):
        config_req = lhm_models.AddDataCheckConfigRequest(
            task_id=task_id,
            source_table=src_table,
            target_table=dst_table,
            source_partition=src_part,
            target_partition=dst_part,
            total_count_threshold=threshold,
            is_full_table_count=0 if src_part else 1,
        )
        resp = client.add_data_check_config(config_req)
        check_resp(resp, f'AddDataCheckConfig[{i}]')
        _log(f'  [{i}/{len(tables)}] {src_table} → configId={resp.body.data}')

    # Step 2: 保存并立即执行
    save_req = lhm_models.ExecDataCheckSaveTaskRequest(
        task_id=task_id,
        total_count_threshold=threshold,
        start_immediately=1,
    )
    if source_global_params:
        save_req.source_global_params = source_global_params
    if target_global_params:
        save_req.target_global_params = target_global_params
    resp = client.exec_data_check_save_task(save_req)
    check_resp(resp, 'ExecDataCheckSaveTask')
    batch_id = resp.body.data
    _log(f'[一键执行] batchId={batch_id}，已自动触发执行')

    return task_id, batch_id


def run_metric_check(
    client: LhmClient,
    task_name: str,
    src_ds: Tuple[str, str, str],
    dst_ds: Tuple[str, str, str],
    tables: List[dict],
    check_template_id: str = '1001',
    threshold: Optional[float] = None,
    source_global_params: Optional[str] = None,
    target_global_params: Optional[str] = None,
    src_engine: Optional[Tuple[str, str, str]] = None,
    dst_engine: Optional[Tuple[str, str, str]] = None,
    auto_bind_engine: bool = True,
    engines_out: Optional[dict] = None,
) -> Tuple[int, int]:
    """
    一键执行逐表指标校验。

    自动串联：创建任务（指定模板） → 逐表配置指标字段 → 保存批次 → 立即执行

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        task_name: 任务名称（仅允许英文字母、中文汉字、数字）
        src_ds: (src_ds_id, src_ds_name, src_ds_type) 元组
        dst_ds: (dst_ds_id, dst_ds_name, dst_ds_type) 元组
        tables: [{'source_table': str, 'target_table': str,
                  'source_partition': str, 'target_partition': str,
                  'source_columns': str, 'target_columns': str}, ...]
                partition 和 columns 可为空字符串
        check_template_id: 校验模板（推荐 1001=MIX）
        threshold: 阈值（**默认 None = 不传，由系统使用默认值**；
                   切勿传 0.0，否则所有数值指标会误判为 PASSED）
        source_global_params: 源端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）
        target_global_params: 目标端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）

    Returns:
        (task_id, batch_id)
    """
    # Step 1: 创建任务
    resp = client.add_data_check_task(lhm_models.AddDataCheckTaskRequest(
        task_name=task_name,
        check_type=1,
        task_mode=0,
        check_template_id=check_template_id,
        src_ds_id=src_ds[0], src_ds_name=src_ds[1], src_ds_type=src_ds[2],
        dst_ds_id=dst_ds[0], dst_ds_name=dst_ds[1], dst_ds_type=dst_ds[2],
    ))
    check_resp(resp, 'AddDataCheckTask')
    task_id = resp.body.data
    _log(f'[一键执行] taskId={task_id}（模板: {check_template_id}）')

    # Step 1.05: 绑定校验引擎（必须在写表配置之前，配置行会拷贝任务上的引擎字段）
    engine_info = ensure_task_engine(
        client, task_id, src_ds, dst_ds,
        check_type=1, template_id=check_template_id,
        src_engine=src_engine, dst_engine=dst_engine,
        auto=auto_bind_engine,
    )
    if engines_out is not None:
        engines_out.update(engine_info)

    # Step 1.1: 逐表配置
    for i, table in enumerate(tables, 1):
        config_req = lhm_models.AddDataCheckConfigRequest(
            task_id=task_id,
            source_table=table['source_table'],
            target_table=table['target_table'],
            source_partition=table.get('source_partition', ''),
            target_partition=table.get('target_partition', ''),
            is_full_table_count=0 if table.get('source_partition') else 1,
        )
        # 指标校验：threshold 为 None 时不传，避免 0.0 导致全部误判 PASSED
        if threshold is not None:
            config_req.total_count_threshold = threshold
        if table.get('source_columns'):
            config_req.source_columns = table['source_columns']
        if table.get('target_columns'):
            config_req.target_columns = table['target_columns']

        resp = client.add_data_check_config(config_req)
        check_resp(resp, f'AddDataCheckConfig[{i}]')
        cols = table.get('source_columns', '') or '模板默认'
        _log(f'  [{i}/{len(tables)}] {table["source_table"]} → configId={resp.body.data}（{cols}）')

    # Step 2: 保存并立即执行
    save_req = lhm_models.ExecDataCheckSaveTaskRequest(
        task_id=task_id,
        start_immediately=1,
    )
    # 指标校验：threshold 为 None 时不传，避免 0.0 导致全部误判 PASSED
    if threshold is not None:
        save_req.total_count_threshold = threshold
    if source_global_params:
        save_req.source_global_params = source_global_params
    if target_global_params:
        save_req.target_global_params = target_global_params
    resp = client.exec_data_check_save_task(save_req)
    check_resp(resp, 'ExecDataCheckSaveTask')
    batch_id = resp.body.data
    _log(f'[一键执行] batchId={batch_id}，已自动触发执行')

    return task_id, batch_id


def run_batch_check(
    client: LhmClient,
    task_name: str,
    src_ds: Tuple[str, str, str],
    dst_ds: Tuple[str, str, str],
    check_type: int,
    match_rule: str,
    threshold: Optional[float] = None,
    check_template_id: Optional[str] = None,
    source_global_params: Optional[str] = None,
    target_global_params: Optional[str] = None,
    src_engine: Optional[Tuple[str, str, str]] = None,
    dst_engine: Optional[Tuple[str, str, str]] = None,
    auto_bind_engine: bool = True,
    engines_out: Optional[dict] = None,
) -> Tuple[int, int]:
    """
    一键执行批量模式校验。

    自动串联：创建任务（批量模式） → 配置匹配规则 → 保存批次 → 立即执行

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        task_name: 任务名称（仅允许英文字母、中文汉字、数字）
        src_ds: (src_ds_id, src_ds_name, src_ds_type) 元组
        dst_ds: (dst_ds_id, dst_ds_name, dst_ds_type) 元组
        check_type: 校验类型（0=数据量 1=指标）
        match_rule: 批量匹配规则（详见 batch_match_rules.md）
        threshold: 阈值（**默认 None = 不传，由系统使用默认值**；
                   指标校验切勿传 0.0，否则所有数值指标会误判为 PASSED）
        check_template_id: 校验模板（仅指标校验时需要）
        source_global_params: 源端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）
        target_global_params: 目标端全局参数（MaxCompute 分区表须设 'odps.sql.allow.fullscan=true'）

    Returns:
        (task_id, batch_id)
    """
    # Step 1: 创建任务
    task_req = lhm_models.AddDataCheckTaskRequest(
        task_name=task_name,
        check_type=check_type,
        task_mode=1,
        src_ds_id=src_ds[0], src_ds_name=src_ds[1], src_ds_type=src_ds[2],
        dst_ds_id=dst_ds[0], dst_ds_name=dst_ds[1], dst_ds_type=dst_ds[2],
    )
    if check_template_id:
        task_req.check_template_id = check_template_id

    resp = client.add_data_check_task(task_req)
    check_resp(resp, 'AddDataCheckTask')
    task_id = resp.body.data
    _log(f'[一键执行] taskId={task_id}（批量模式）')

    # Step 1.05: 绑定校验引擎（必须在写配置之前，批量模式 save 时也会重写该字段）
    engine_info = ensure_task_engine(
        client, task_id, src_ds, dst_ds,
        check_type=check_type, template_id=check_template_id,
        src_engine=src_engine, dst_engine=dst_engine,
        auto=auto_bind_engine,
    )
    if engines_out is not None:
        engines_out.update(engine_info)

    # Step 1.1: 配置批量匹配规则
    config_req = lhm_models.AddDataCheckConfigRequest(
        task_id=task_id,
        task_config_info=match_rule,
    )
    resp = client.add_data_check_config(config_req)
    check_resp(resp, 'AddDataCheckConfig')
    _log(f'[一键执行] 匹配规则已配置: {match_rule}')

    # Step 2: 保存并立即执行
    save_req = lhm_models.ExecDataCheckSaveTaskRequest(
        task_id=task_id,
        start_immediately=1,
    )
    # threshold 为 None 时不传，避免指标校验传 0.0 导致全部误判 PASSED
    if threshold is not None:
        save_req.total_count_threshold = threshold
    if source_global_params:
        save_req.source_global_params = source_global_params
    if target_global_params:
        save_req.target_global_params = target_global_params
    try:
        resp = client.exec_data_check_save_task(save_req)
        check_resp(resp, 'ExecDataCheckSaveTask')
    except RuntimeError as e:
        err_msg = str(e)
        if '校验规划结果为空' in err_msg or 'planner result is empty' in err_msg.lower():
            raise RuntimeError(
                f'校验规划结果为空，请检查批量匹配规则是否匹配到表。\n'
                f'当前规则: {match_rule}\n'
                f'常见原因:\n'
                f'  1. 通配符误用：批量规则字段为“正则表达式”，'
                f'     匹配所有 lhm_ 开头的表应写 lhm_.*，而不是 lhm_*；'
                f'     匹配所有表应写 *\n'
                f'  2. 库名/表名拼写错误，或目标端不存在同名表\n'
                f'  3. MaxCompute 分区表未在规则中指定双边分区条件\n'
                f'  4. 数据源类型与规则不匹配\n'
                f'原始错误: {err_msg}'
            ) from e
        raise
    batch_id = resp.body.data
    _log(f'[一键执行] batchId={batch_id}（规则: {match_rule}），已自动触发执行')

    return task_id, batch_id


# ============================================================================
# 场景 6：查询不通过任务
# ============================================================================

def list_failed_tasks(
    client: LhmClient,
    include_stopped: bool = True,
) -> list:
    """
    查询所有存在问题的任务（不通过 / 执行失败 / 被终止）。

    直接使用 get_data_check_task_list 返回的状态字段，无需额外调 history API。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        include_stopped: 是否包含被终止（exec_status=2）的任务

    Returns:
        [{'id': int, 'batch_id': int, 'task_name': str, 'check_type': str,
          'exec_status': str, 'check_result': str}, ...]
    """
    page = 1
    all_tasks = []
    while True:
        resp = client.get_data_check_task_list(lhm_models.GetDataCheckTaskListRequest(
            page_index=page, page_size=100
        ))
        check_resp(resp, 'GetDataCheckTaskList')
        rows = resp.body.data or []
        all_tasks.extend(rows)
        if len(rows) < 100:
            break
        page += 1

    problem_tasks = []
    for task in all_tasks:
        exec_status = task.exec_status
        check_result = task.check_result
        if exec_status is None:
            continue

        # FINISHED(4)+FAIL(2) / FAILED(3) / STOPPED(2)
        is_problem = (exec_status == 4 and check_result == 2) or exec_status == 3
        if include_stopped and exec_status == 2:
            is_problem = True

        if is_problem:
            problem_tasks.append({
                'id': task.id,
                'batch_id': task.last_batch_id,
                'task_name': task.task_name,
                'check_type': CHECK_TYPE_TEXT.get(task.check_type, str(task.check_type)),
                'exec_status': EXEC_STATUS_TEXT.get(exec_status, str(exec_status)),
                'check_result': CHECK_RESULT_TEXT.get(check_result, str(check_result)) if check_result is not None else '-',
            })

    return problem_tasks


# ============================================================================
# 场景 2~5：报告下载、诊断、重跑、全流程
# ============================================================================

def download_report(
    client: LhmClient,
    batch_id: int,
    timeout_sec: int = 300,
    interval_sec: int = 3,
) -> str:
    """
    一键下载报告。

    自动串联：确认批次完成 → 触发报告生成 → 轮询报告状态 → 下载

    Returns:
        OSS 下载链接
    """
    # 1. 确认批次已执行完成
    history_req = lhm_models.ListDataCheckTaskHistoryRequest(batch_id=batch_id, page_index=1, page_size=1)
    resp = client.list_data_check_task_history(history_req)
    check_resp(resp, 'ListDataCheckTaskHistory')
    if resp.body.data[0].exec_status != 4:
        raise RuntimeError(f'批次未完成: exec_status={resp.body.data[0].exec_status}')

    # 2. 触发报告生成
    resp = client.exec_data_check_generate_report(lhm_models.ExecDataCheckGenerateReportRequest(batch_id=batch_id))
    check_resp(resp, 'ExecDataCheckGenerateReport')

    # 3. 轮询报告生成状态
    deadline = time.time() + timeout_sec
    while True:
        resp = client.get_data_check_report_status(lhm_models.GetDataCheckReportStatusRequest(batch_id=batch_id))
        check_resp(resp, 'GetDataCheckReportStatus')
        status = resp.body.data
        if status == 2:
            break
        elif status == 3:
            raise RuntimeError('报告生成失败')
        if time.time() > deadline:
            raise RuntimeError(f'报告生成超时 ({timeout_sec}s)')
        time.sleep(interval_sec)

    # 4. 下载
    resp = client.exec_data_check_download_report(lhm_models.ExecDataCheckDownloadReportRequest(batch_id=batch_id))
    check_resp(resp, 'ExecDataCheckDownloadReport')
    return resp.body.data


def diagnose_failed(
    client: LhmClient,
    batch_id: int,
    group_by_field: bool = False,
) -> list:
    """
    一键诊断不通过原因。

    自动串联：报告列表 → 筛选不通过的表 → 查 Step 明细 → 查字段明细 → 输出诊断结果

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        batch_id: 批次 ID
        group_by_field: True 时返回按字段分组的结构化字典，False 时返回扁平列表

    Returns:
        group_by_field=False 时：
            诊断列表 [{'table': str, 'type': str, 'detail': dict}, ...]
        group_by_field=True 时：
            {
                'table_name': {
                    'summary': {'total': int, 'pass': int, 'fail': int},
                    'steps': [...],
                    'columns': {
                        'field_name': {'pass': int, 'fail': int, 'metrics': [...]},
                    }
                }
            }
    """
    # 1. 获取报告列表，筛选不通过的表
    resp = client.list_data_check_report(lhm_models.ListDataCheckReportRequest(
        batch_id=batch_id, check_result=2, page_index=1, page_size=200,
    ))
    check_resp(resp, 'ListDataCheckReport')

    diagnosis = []
    for row in resp.body.data:
        job_id = row.job_id  # str 字符串哈希
        table = row.source_table
        # 报告级别的 count 数据（Step API 对数据量校验可能不返回 src_count/dst_count）
        report_src_count = row.source_count
        report_dst_count = row.target_count

        # 2. 查 Step 明细（使用 list_data_check_report_step_by_job_id，接受字符串 job_id）
        step_resp = client.list_data_check_report_step_by_job_id(
            lhm_models.ListDataCheckReportStepByJobIdRequest(
                job_id=job_id, page_index=1, page_size=200,
            )
        )
        check_resp(step_resp, 'ListDataCheckReportStepByJobId')

        for step in step_resp.body.data:
            diagnosis.append({
                'table': table,
                'type': 'STEP',
                'detail': {
                    'result_id': step.result_id,
                    'src_count': step.src_count if step.src_count is not None else report_src_count,
                    'dst_count': step.dst_count if step.dst_count is not None else report_dst_count,
                    'source_pt_name': step.source_pt_name,
                    'target_pt_name': step.target_pt_name,
                    'src_sql': step.src_sql,
                    'dst_sql': step.dst_sql,
                    'is_consistent': step.is_consistent,  # 0=不一致 1=一致
                    'err_message': step.err_message,
                }
            })

            # 3. 查字段明细（指标校验时，按 result_id 查询）
            # 返回全部字段（包括通过的），差异分析时需要正反两面数据
            if step.result_id:
                col_resp = client.list_data_check_column_results(
                    lhm_models.ListDataCheckColumnResultsRequest(
                        result_id=step.result_id, page_index=1, page_size=200,
                    )
                )
                if col_resp.body.success and col_resp.body.data:
                    for col in col_resp.body.data:
                        diagnosis.append({
                            'table': table,
                            'type': 'COLUMN',
                            'detail': {
                                'column': col.src_column_name,
                                'metric': col.src_alias or col.src_metric_column,
                                'src_result': col.src_result,
                                'dst_result': col.dst_result,
                                'actual_threshold': col.actual_threshold,
                                'is_consistent': col.is_consistent,
                            }
                        })

    if not group_by_field:
        return diagnosis

    # 结构化输出：按表 → 字段分组
    grouped = {}
    for item in diagnosis:
        table = item['table']
        if table not in grouped:
            grouped[table] = {
                'summary': {'total': 0, 'pass': 0, 'fail': 0},
                'steps': [],
                'columns': {},
            }
        if item['type'] == 'STEP':
            grouped[table]['steps'].append(item['detail'])
        elif item['type'] == 'COLUMN':
            field = item['detail']['column']
            if field not in grouped[table]['columns']:
                grouped[table]['columns'][field] = {'pass': 0, 'fail': 0, 'metrics': []}
            entry = grouped[table]['columns'][field]
            entry['metrics'].append(item['detail'])
            if item['detail'].get('is_consistent', 0) == 1:
                entry['pass'] += 1
                grouped[table]['summary']['pass'] += 1
            else:
                entry['fail'] += 1
                grouped[table]['summary']['fail'] += 1
            grouped[table]['summary']['total'] += 1

    return grouped


def summarize_batch(
    client: LhmClient,
    batch_id: int,
) -> dict:
    """
    快速查看一个批次的校验概况。

    一次调用返回：任务名、模板、表级统计、字段级统计、差异率。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        batch_id: 批次 ID

    Returns:
        {
            'task_name': str,
            'template': str,
            'total_tables': int,
            'pass_tables': int,
            'fail_tables': int,
            'pass_rate': str,       # 如 '88.46%'
            'column_pass_rate': float,
            'diff_rate': str,       # 如 '54.10%'
            'exec_status': int,
            'check_result': int,
        }
    """
    # 1. 报告概览
    resp = client.get_data_check_report_overview(
        lhm_models.GetDataCheckReportOverviewRequest(batch_id=batch_id)
    )
    check_resp(resp, 'GetDataCheckReportOverview')
    d = resp.body.data

    result = {
        'task_name': d.task_name,
        'template': d.check_template_name,
        'total_tables': d.check_table_num,
        'pass_tables': d.pass_table_num,
        'fail_tables': d.error_table_num,
        'pass_rate': d.pass_process_export,
        'column_pass_rate': d.pass_column_rate,
        'exec_status': 4,  # overview 隐含已完成
        'check_result': d.check_result,
    }

    # 2. 取第一张表拿 diff_rate
    list_resp = client.list_data_check_report(
        lhm_models.ListDataCheckReportRequest(batch_id=batch_id, page_index=1, page_size=1)
    )
    if list_resp.body.success and list_resp.body.data:
        result['diff_rate'] = list_resp.body.data[0].diff_rate
    else:
        result['diff_rate'] = '-'

    return result


def rerun_failed(
    client: LhmClient,
    batch_id: int,
    fail_type: int = 0,
) -> int:
    """
    一键重跑失败任务。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        batch_id: 原批次 ID
        fail_type: 0=仅失败 1=失败+不通过 2=失败+被终止

    Returns:
        新 batch_id
    """
    resp = client.exec_data_check_run_failed(lhm_models.ExecDataCheckRunFailedRequest(
        batch_id=batch_id,
        type=fail_type,
    ))
    check_resp(resp, 'ExecDataCheckRunFailed')
    new_batch_id = resp.body.data
    _log(f'[一键重跑] 新 batchId={new_batch_id}')
    return new_batch_id


def full_check_pipeline(
    client: LhmClient,
    task_name: str,
    src_ds: Tuple[str, str, str],
    dst_ds: Tuple[str, str, str],
    tables: List[Tuple[str, str, str, str]],
    threshold: float = 0.0,
) -> dict:
    """
    端到端全流程：执行校验 → 等待完成 → 下载报告 → 诊断不通过。

    Returns:
        {task_id, batch_id, pass_rate, oss_url, diagnosis}
    """
    # 场景 1: 执行
    task_id, batch_id = run_count_check(
        client, task_name, src_ds, dst_ds, tables, threshold,
    )

    # 轮询
    final = poll_exec_status(client, task_id, batch_id)
    if final == 3:
        raise RuntimeError('校验执行失败')

    # 场景 2: 下载
    oss_url = download_report(client, batch_id)

    # 报告概览
    resp = client.get_data_check_report_overview(
        lhm_models.GetDataCheckReportOverviewRequest(batch_id=batch_id))
    check_resp(resp, 'GetDataCheckReportOverview')
    pass_rate = resp.body.data.pass_process_export

    # 场景 3: 诊断
    diagnosis = diagnose_failed(client, batch_id)

    return {
        'task_id': task_id,
        'batch_id': batch_id,
        'pass_rate': pass_rate,
        'oss_url': oss_url,
        'diagnosis': diagnosis,
    }


# ============================================================================
# 模板管理 (Template CRUD)
# ============================================================================

def list_templates(
    client,
    check_type: Optional[int] = None,
    name: Optional[str] = None,
    is_builtin: Optional[int] = None,
) -> List[dict]:
    """
    列出可用校验模板。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        check_type: 校验类型筛选 (0=数据量/1=指标/2=弱内容)
        name: 名称模糊匹配
        is_builtin: 0=自定义, 1=内置

    Returns:
        模板列表，每项含 templateId/templateName/checkType/isBuiltin 等
    """
    req = lhm_models.GetDataCheckTemplateListRequest(
        check_type=check_type,
        template_name=name,
        is_builtin=is_builtin,
    )
    resp = client.get_data_check_template_list(req)
    check_resp(resp, 'GetDataCheckTemplateList')
    items = resp.body.data or []
    return [
        {
            'templateId': t.template_id,
            'templateName': t.template_name,
            'checkType': t.check_type,
            'checkTypeExport': t.check_type_export,
            'dsTypes': t.ds_types,
            'engineTypes': t.engine_types,
            'isBuiltin': t.is_builtin,
            'templateDesc': t.template_desc,
            'isUsedByTask': t.is_used_by_task,
            'gmtModified': t.gmt_modified,
        }
        for t in items
    ]


def get_template_detail(client, template_id: str) -> dict:
    """
    查看模板完整配置。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        template_id: 模板 ID（内置: 1001/1002/1003, 自定义: UUID）

    Returns:
        模板详情字典，含 metricRules / weakContentRule / dsEngineRels 等
    """
    req = lhm_models.GetDataCheckTemplateRequest(template_id=template_id)
    resp = client.get_data_check_template(req)
    check_resp(resp, 'GetDataCheckTemplate')
    d = resp.body.data
    if not d:
        raise RuntimeError(f'模板 {template_id} 不存在或已被删除')

    result = {
        'templateId': d.template_id,
        'templateName': d.template_name,
        'checkType': d.check_type,
        'templateDesc': d.template_desc,
        'dsEngineRels': [
            {'dsType': r.ds_type, 'engineTypes': r.engine_types}
            for r in (d.ds_engine_rels or [])
        ],
    }

    # metric rules
    if d.metric_rules:
        result['metricRules'] = [
            {
                'ruleId': r.rule_id,
                'dataTypeClassify': r.data_type_classify,
                'dataTypeGroup': r.data_type_group,
                'dataTypeList': r.data_type_list,
                'checkMethods': r.check_methods,
                'diffTolerateType': r.diff_tolerate_type,
                'diffTolerateValues': r.diff_tolerate_values,
                'isCountCheck': r.is_count_check,
                'filterColumnName': r.filter_column_name,
            }
            for r in d.metric_rules
        ]

    # weak content rule
    if d.weak_content_rule:
        wcr = d.weak_content_rule
        result['weakContentRule'] = {
            'ruleId': wcr.rule_id,
            'weakContentAlgorithm': wcr.weak_content_algorithm,
            'filterColumnTypes': wcr.filter_column_types,
            'filterColumnExpression': wcr.filter_column_expression,
        }

    return result


def create_template(
    client,
    name: str,
    check_type: int,
    ds_engine_rels: List[dict],
    metric_rules: Optional[List[dict]] = None,
    weak_content_rule: Optional[dict] = None,
    desc: Optional[str] = None,
) -> str:
    """
    创建自定义校验模板。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        name: 模板名称
        check_type: 1=指标, 2=弱内容
        ds_engine_rels: [{"dsType": "MaxCompute", "engineTypes": ["MaxCompute"]}]
        metric_rules: checkType=1 时的规则列表
        weak_content_rule: checkType=2 时的弱内容规则
        desc: 模板描述

    Returns:
        新建的模板 ID (UUID)
    """
    ds_rels = [
        lhm_models.AddDataCheckTemplateRequestDsEngineRels(
            ds_type=r['dsType'], engine_types=r['engineTypes'],
        )
        for r in ds_engine_rels
    ]

    mr_list = None
    if metric_rules:
        mr_list = [
            lhm_models.AddDataCheckTemplateRequestMetricRules(
                data_type_classify=r.get('dataTypeClassify', 0),
                data_type_group=r['dataTypeGroup'],
                data_type_list=r['dataTypeList'],
                check_methods=r['checkMethods'],
                diff_tolerate_type=r.get('diffTolerateType', 0),
                diff_tolerate_values=r.get('diffTolerateValues', {"SAME": 0}),
                is_count_check=r.get('isCountCheck', 1),
                filter_column_name=r.get('filterColumnName'),
                ignore_numeric_zero=r.get('ignoreNumericZero'),
                ignore_string_empty=r.get('ignoreStringEmpty'),
                enable_decimal_scale=r.get('enableDecimalScale'),
                set_decimal_scale=r.get('setDecimalScale'),
            )
            for r in metric_rules
        ]

    wc_rule = None
    if weak_content_rule:
        wc_rule = lhm_models.AddDataCheckTemplateRequestWeakContentRule(
            filter_column_types=weak_content_rule.get('filterColumnTypes'),
            filter_column_expression=weak_content_rule.get('filterColumnExpression'),
        )

    req = lhm_models.AddDataCheckTemplateRequest(
        template_name=name,
        check_type=check_type,
        ds_engine_rels=ds_rels,
        metric_rules=mr_list,
        weak_content_rule=wc_rule,
        template_desc=desc,
    )
    resp = client.add_data_check_template(req)
    check_resp(resp, 'AddDataCheckTemplate')
    return resp.body.data


def update_template(
    client,
    template_id: str,
    name: Optional[str] = None,
    check_type: Optional[int] = None,
    ds_engine_rels: Optional[List[dict]] = None,
    metric_rules: Optional[List[dict]] = None,
    weak_content_rule: Optional[dict] = None,
    desc: Optional[str] = None,
) -> None:
    """
    更新模板（upsert 语义）。

    注意：后端 UpdateCmd.getMetricRules() 会清空 metricRules 字段，
    必须按 dataTypeClassify 拆分到 basicMetricRules / complexMetricRules。
    此函数内部自动完成拆分，调用方无需关心。

    后端要求 checkType 和 dsEngineRels 必传（即使只更新名称）。
    未提供时自动从现有模板回填。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        template_id: 模板 ID
        name: 新名称（可选）
        check_type: 校验类型（可选，不传则从现有模板回填）
        ds_engine_rels: 数据源-引擎映射（可选，不传则从现有模板回填）
        metric_rules: 规则列表，按 dataTypeClassify 自动拆分
        weak_content_rule: 弱内容规则（可选）
        desc: 描述（可选）
    """
    # 回填必填字段：checkType / dsEngineRels / 规则（未传时保留现有值）
    _need_backfill = (check_type is None or ds_engine_rels is None
                      or (metric_rules is None and weak_content_rule is None))
    if _need_backfill:
        existing = get_template_detail(client, template_id)
        if check_type is None:
            check_type = existing.get('checkType')
        if ds_engine_rels is None:
            ds_engine_rels = existing.get('dsEngineRels', [])
        # 规则回填：未传则保留现有，传空列表则视为清空
        if metric_rules is None and existing.get('metricRules'):
            metric_rules = existing['metricRules']
        if weak_content_rule is None and existing.get('weakContentRule'):
            weak_content_rule = existing['weakContentRule']

    ds_rels = None
    if ds_engine_rels:
        ds_rels = [
            lhm_models.UpdateDataCheckTemplateRequestDsEngineRels(
                ds_type=r['dsType'], engine_types=r['engineTypes'],
            )
            for r in ds_engine_rels
        ]

    # 按 dataTypeClassify 拆分到 basic / complex
    basic_rules = None
    complex_rules = None
    if metric_rules:
        basic_list = []
        complex_list = []
        for r in metric_rules:
            classify = r.get('dataTypeClassify', 0)
            rule_kwargs = dict(
                rule_id=r.get('ruleId'),
                data_type_classify=classify,
                data_type_group=r['dataTypeGroup'],
                data_type_list=r['dataTypeList'],
                check_methods=r['checkMethods'],
                diff_tolerate_type=r.get('diffTolerateType', 0),
                diff_tolerate_values=r.get('diffTolerateValues', {"SAME": 0}),
                is_count_check=r.get('isCountCheck', 1),
                filter_column_name=r.get('filterColumnName'),
                ignore_numeric_zero=r.get('ignoreNumericZero'),
                ignore_string_empty=r.get('ignoreStringEmpty'),
                enable_decimal_scale=r.get('enableDecimalScale'),
                set_decimal_scale=r.get('setDecimalScale'),
            )
            if classify == 0:
                basic_list.append(lhm_models.UpdateDataCheckTemplateRequestBasicMetricRules(**rule_kwargs))
            else:
                complex_list.append(lhm_models.UpdateDataCheckTemplateRequestComplexMetricRules(**rule_kwargs))
        basic_rules = basic_list or None
        complex_rules = complex_list or None

    wc_rule = None
    if weak_content_rule:
        wc_rule = lhm_models.UpdateDataCheckTemplateRequestWeakContentRule(
            rule_id=weak_content_rule.get('ruleId'),
            filter_column_types=weak_content_rule.get('filterColumnTypes'),
            filter_column_expression=weak_content_rule.get('filterColumnExpression'),
        )

    req = lhm_models.UpdateDataCheckTemplateRequest(
        template_id=template_id,
        template_name=name,
        check_type=check_type,
        ds_engine_rels=ds_rels,
        basic_metric_rules=basic_rules,
        complex_metric_rules=complex_rules,
        weak_content_rule=wc_rule,
        template_desc=desc,
    )
    resp = client.update_data_check_template(req)
    check_resp(resp, 'UpdateDataCheckTemplate')


def delete_templates(client, template_ids: List[str]) -> None:
    """
    批量删除模板。

    Args:
        client: LHM 客户端（网络层走 aliyun CLI）
        template_ids: 模板 ID 列表
    """
    req = lhm_models.DeleteDataCheckTemplateRequest(template_ids=template_ids)
    resp = client.delete_data_check_template(req)
    check_resp(resp, 'DeleteDataCheckTemplate')
