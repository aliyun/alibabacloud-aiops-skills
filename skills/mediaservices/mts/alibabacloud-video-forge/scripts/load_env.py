#!/usr/bin/env python3
"""
load_env.py — 阿里云 MPS Skill 环境变量自动加载工具

功能：
  扫描以下常用文件，如果文件中包含指定的环境变量 KEY，则将该文件中的所有
  KEY=VALUE 行加载到当前进程的 os.environ 中（不覆盖已存在的值）：
    ~/.bashrc
    ~/.profile
    ~/.bash_profile
    ~/.env

  目标变量（只要文件中存在其中任意一个，该文件就会被加载）：
    ALIBABA_CLOUD_OSS_BUCKET
    ALIBABA_CLOUD_OSS_ENDPOINT
    ALIBABA_CLOUD_REGION
    ALIBABA_CLOUD_MPS_PIPELINE_ID
  
  凭证通过 alibabacloud_credentials 默认凭证链获取，请使用 'aliyun configure' 配置。

用法（在其他脚本中调用）：
    from load_env import ensure_env_loaded, get_oss_auth, infer_region_from_oss
    ensure_env_loaded()
    auth = get_oss_auth()  # 获取 OSS 认证对象
    region = infer_region_from_oss(url=url, endpoint=endpoint, bucket=bucket)  # 智能推断 region

依赖检查：
    脚本会自动检查所需依赖包是否安装，如果缺失会给出安装建议

Note:
    为遵循最小权限原则，本脚本仅扫描用户主目录下的配置文件
    不再扫描系统级配置文件（/etc/environment, /etc/profile）
"""

import os
import re
import sys

# 依赖检查
_REQUIRED_PACKAGES = {
    'oss2': 'OSS SDK',
    'alibabacloud_credentials': 'Alibaba Cloud Credentials SDK'
}

# ─── Region 智能推断 ────────────────────────────────────────────────────────

# 支持的阿里云 region 列表
_VALID_REGIONS = {
    'cn-hangzhou', 'cn-shanghai', 'cn-beijing', 'cn-shenzhen', 'cn-zhangjiakou',
    'cn-huhehaote', 'cn-wulanchabu', 'cn-chengdu', 'cn-qingdao', 'cn-hongkong',
    'cn-heyuan', 'cn-guangzhou', 'cn-fuzhou', 'cn-nanjing', 'cn-wuhan',
    'ap-southeast-1', 'ap-southeast-2', 'ap-southeast-3', 'ap-southeast-5', 'ap-southeast-6', 'ap-southeast-7',
    'ap-northeast-1', 'ap-northeast-2', 'ap-south-1',
    'us-west-1', 'us-east-1', 'eu-west-1', 'eu-central-1', 'me-east-1', 'me-central-1',
}

# 从 OSS endpoint 提取 region 的正则
_OSS_ENDPOINT_REGION_RE = re.compile(r'oss[.-]([\w-]+)(?:\.aliyuncs\.com|\.internal)')

# 从 OSS URL 提取 region 的正则（如 bucket-name.oss-cn-hangzhou.aliyuncs.com）
_OSS_URL_REGION_RE = re.compile(r'\.oss[.-]([\w-]+)\.aliyuncs\.com')


def infer_region_from_oss(
    url: str = None,
    endpoint: str = None,
    bucket: str = None,
    oss_object: str = None,
    fallback_region: str = None,
) -> str:
    """
    从 OSS 相关参数中智能推断 region。
    
    优先级（从高到低）：
      1. 从 OSS URL 中提取（如 https://bucket.oss-cn-hangzhou.aliyuncs.com/...）
      2. 从 OSS endpoint 中提取（如 oss-cn-hangzhou.aliyuncs.com）
      3. 从 bucket 名称中推断（如 test-video-forge-cnhangzhou）
      4. 使用 fallback_region（如果提供）
      5. 使用环境变量 ALIBABA_CLOUD_REGION
      6. 最终默认值 cn-shanghai
    
    Args:
        url: OSS URL（如 https://bucket.oss-cn-hangzhou.aliyuncs.com/object）
        endpoint: OSS endpoint（如 oss-cn-hangzhou.aliyuncs.com）
        bucket: OSS bucket 名称
        oss_object: OSS object key（通常不包含 region 信息，但为完整性保留）
        fallback_region: 回退 region（如命令行参数指定的值）
    
    Returns:
        str: 推断出的 region（如 cn-hangzhou）
    """
    # 1. 从 URL 提取
    if url:
        region = _extract_region_from_url(url)
        if region:
            return region
    
    # 2. 从 endpoint 提取
    if endpoint:
        region = _extract_region_from_endpoint(endpoint)
        if region:
            return region
    
    # 3. 从 bucket 名称推断
    if bucket:
        region = _infer_region_from_bucket_name(bucket)
        if region:
            return region
    
    # 4. 使用 fallback_region
    if fallback_region:
        return fallback_region
    
    # 5. 使用环境变量
    env_region = os.environ.get("ALIBABA_CLOUD_REGION")
    if env_region:
        return env_region
    
    # 6. 最终默认值
    return "cn-shanghai"


def _extract_region_from_url(url: str) -> str:
    """从 OSS URL 中提取 region"""
    if not url:
        return None
    
    match = _OSS_URL_REGION_RE.search(url)
    if match:
        region = match.group(1)
        if region in _VALID_REGIONS:
            return region
    return None


def _extract_region_from_endpoint(endpoint: str) -> str:
    """从 OSS endpoint 中提取 region"""
    if not endpoint:
        return None
    
    match = _OSS_ENDPOINT_REGION_RE.search(endpoint)
    if match:
        region = match.group(1)
        if region in _VALID_REGIONS:
            return region
    return None


def _infer_region_from_bucket_name(bucket: str) -> str:
    """
    从 bucket 名称推断 region。
    
    常见模式：
      - xxx-cnhangzhou -> cn-hangzhou
      - xxx-cn-hangzhou -> cn-hangzhou
      - xxx-apsoutheast1 -> ap-southeast-1
    """
    if not bucket:
        return None
    
    bucket_lower = bucket.lower()
    
    # 检查每个有效 region
    for region in _VALID_REGIONS:
        # 格式1: xxx-cn-hangzhou（带连字符）
        if f'-{region}' in bucket_lower or bucket_lower.endswith(region):
            return region
        
        # 格式2: xxx-cnhangzhou（不带连字符）
        region_compact = region.replace('-', '')
        if f'-{region_compact}' in bucket_lower or bucket_lower.endswith(region_compact):
            return region
    
    return None


def get_region_with_inference(
    explicit_region: str = None,
    url: str = None,
    endpoint: str = None,
    bucket: str = None,
    oss_object: str = None,
) -> str:
    """
    获取 region，支持智能推断。
    
    优先级：
      1. explicit_region（命令行明确指定的 --region 参数）
      2. 从 OSS URL/endpoint/bucket 推断
      3. 环境变量 ALIBABA_CLOUD_REGION
      4. 默认值 cn-shanghai
    
    这是推荐在脚本中使用的主入口函数。
    
    Args:
        explicit_region: 命令行明确指定的 region（如果未指定则为 None 或空字符串）
        url: OSS URL
        endpoint: OSS endpoint
        bucket: OSS bucket 名称
        oss_object: OSS object key
    
    Returns:
        str: 最终使用的 region
    """
    # 如果明确指定了 region，直接使用
    if explicit_region:
        return explicit_region
    
    # 使用智能推断
    return infer_region_from_oss(
        url=url,
        endpoint=endpoint,
        bucket=bucket,
        oss_object=oss_object,
    )


def _check_dependencies():
    """检查必需的依赖包是否已安装"""
    missing_packages = []
    
    for package, description in _REQUIRED_PACKAGES.items():
        try:
            if package == 'oss2':
                import oss2
            elif package == 'alibabacloud_credentials':
                from alibabacloud_credentials.client import Client
        except ImportError:
            missing_packages.append((package, description))
    
    if missing_packages:
        print("❌ 缺少必要的依赖包:", file=sys.stderr)
        for package, description in missing_packages:
            print(f"   - {description} ({package})", file=sys.stderr)
        
        print("\n💡 安装建议:", file=sys.stderr)
        print("   pip install alibabacloud-mts20140618 alibabacloud-credentials oss2", file=sys.stderr)
        print("   # 或者如果权限不足:", file=sys.stderr)
        print("   pip install --user alibabacloud-mts20140618 alibabacloud-credentials oss2", file=sys.stderr)
        
        return False
    return True


def check_and_setup_credentials():
    """
    检查并设置凭证，支持多种来源自动检测和回退
    
    Returns:
        bool: 凭证是否可用
    
    Note:
        ⚠️ 安全规则:
        - NEVER read, echo, or print AK/SK values
        - NEVER ask user to input AK/SK directly
        - ONLY use alibabacloud_credentials for secure credential management
    """
    # 使用 alibabacloud_credentials 检查凭证（遵循默认凭证链）
    try:
        from alibabacloud_credentials.client import Client
        cred_client = Client()
        # 尝试获取凭证，如果配置正确会自动加载
        cred = cred_client.get_credential()
        if cred:
            print("✅ 使用 alibabacloud_credentials 管理的凭证")
            return True
    except Exception as e:
        pass
    
    # 凭证获取失败，给出友好提示（不打印具体值）
    print("❌ 未检测到有效的阿里云凭证", file=sys.stderr)
    print("\n💡 请使用 Aliyun CLI 配置凭证:", file=sys.stderr)
    print("     $ aliyun configure")
    print("     按提示输入 AccessKey ID、AccessKey Secret 和 Region")
    print("\n   配置完成后运行 'aliyun configure list' 验证")
    return False

# 扫描的候选文件列表（按优先级排序）
# 仅包含用户主目录下的配置文件，遵循最小权限原则
_ENV_FILES = [
    os.path.expanduser("~/.bashrc"),
    os.path.expanduser("~/.profile"),
    os.path.expanduser("~/.bash_profile"),
    os.path.expanduser("~/.env"),
]

# KEY=VALUE 行的正则（支持带引号的值）
_KV_RE = re.compile(
    r"""^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([\'"]?)(.*?)\2\s*$"""
)

# alibabacloud_credentials 是否可用
_CREDENTIALS_SDK_AVAILABLE = None


def _check_credentials_sdk():
    """检查 alibabacloud_credentials SDK 是否可用"""
    global _CREDENTIALS_SDK_AVAILABLE
    if _CREDENTIALS_SDK_AVAILABLE is None:
        try:
            from alibabacloud_credentials.client import Client
            _CREDENTIALS_SDK_AVAILABLE = True
        except ImportError:
            _CREDENTIALS_SDK_AVAILABLE = False
    return _CREDENTIALS_SDK_AVAILABLE


def get_oss_auth():
    """
    获取 OSS 认证对象，使用阿里云默认凭证链。
    
    使用 alibabacloud_credentials SDK（支持多种凭证来源：环境变量、配置文件、ECS RAM 角色等）。
    
    Returns:
        oss2.ProviderAuth: OSS 认证对象
    
    Raises:
        SystemExit: 如果无法获取有效凭证
    
    Note:
        ⚠️ 安全规则：NEVER read or expose AK/SK values directly
    """
    try:
        import oss2
    except ImportError:
        print("错误：未安装阿里云 OSS SDK。请运行：pip install oss2", file=sys.stderr)
        sys.exit(1)
    
    # 使用 alibabacloud_credentials SDK（遵循默认凭证链）
    if _check_credentials_sdk():
        try:
            from alibabacloud_credentials.client import Client as CredClient
            from oss2.credentials import CredentialsProvider, Credentials
            
            # 创建凭证客户端并验证凭证可用性
            cred_client = CredClient()
            # 尝试获取凭证（不打印具体值）
            _ = cred_client.get_credential()
            
            # 使用凭证提供器模式（不暴露 AK/SK）
            class AlibabaCloudCredentialsProvider(CredentialsProvider):
                """使用 alibabacloud_credentials 的 OSS 凭证提供器"""
                
                def __init__(self, client):
                    self._cred_client = client
                
                def get_credentials(self):
                    ak = self._cred_client.get_access_key_id()
                    sk = self._cred_client.get_access_key_secret()
                    token = self._cred_client.get_security_token()
                    return Credentials(ak, sk, token)
            
            provider = AlibabaCloudCredentialsProvider(cred_client)
            return oss2.ProviderAuth(provider)
            
        except Exception as e:
            # 凭证获取失败，打印错误信息
            print(f"错误：alibabacloud_credentials 凭证获取失败: {str(e)}", file=sys.stderr)
    
    # 凭证获取失败，打印友好提示
    _print_credentials_hint()
    sys.exit(1)


def _print_credentials_hint():
    """打印凭证配置提示"""
    hint = """
╔══════════════════════════════════════════════════════════════════╗
║                    阿里云凭证未配置                                ║
╚══════════════════════════════════════════════════════════════════╝

未能获取到有效的阿里云凭证。请使用以下方式配置：

【推荐】使用 aliyun CLI 配置
  aliyun configure
  # 按提示输入凭证信息

配置完成后运行 'aliyun configure list' 验证凭证状态。

密钥获取地址：https://ram.console.aliyun.com/manage/ak

⚠️  安全提示：请勿在代码中硬编码密钥，使用 aliyun configure 安全配置。
"""
    print(hint, file=sys.stderr)


def _parse_env_file(filepath: str) -> dict:
    """
    解析一个 shell 风格的环境变量文件，返回 {key: value} 字典。
    支持：
      KEY=value
      export KEY=value
      KEY="value with spaces"
      KEY='value'
      # 注释行（忽略）
    """
    result = {}
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                # 跳过注释和空行
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                m = _KV_RE.match(line)
                if m:
                    key = m.group(1)
                    value = m.group(3)
                    result[key] = value
    except (OSError, IOError):
        pass
    return result


def _file_contains_target(parsed: dict) -> bool:
    """判断解析结果中是否包含至少一个目标变量。"""
    return bool(_TARGET_VARS & set(parsed.keys()))


def load_env_files(verbose: bool = False) -> dict:
    """
    扫描所有候选文件，将包含目标变量的文件内容加载到 os.environ。
    已存在的环境变量不会被覆盖（setdefault 语义）。

    返回：本次新加载的变量字典 {key: value}
    """
    newly_loaded = {}

    for filepath in _ENV_FILES:
        if not os.path.isfile(filepath):
            if verbose:
                print(f"[load_env] 跳过（不存在）: {filepath}", file=sys.stderr)
            continue

        parsed = _parse_env_file(filepath)

        if not _file_contains_target(parsed):
            if verbose:
                print(f"[load_env] 跳过（无目标变量）: {filepath}", file=sys.stderr)
            continue

        if verbose:
            print(f"[load_env] 加载文件: {filepath}", file=sys.stderr)

        for key, value in parsed.items():
            if key not in os.environ:
                os.environ[key] = value
                newly_loaded[key] = value
                if verbose:
                    # 密钥只显示前4位
                    display = value[:4] + "****" if len(value) > 4 else "****"
                    print(f"[load_env]   设置 {key}={display}", file=sys.stderr)
            else:
                if verbose:
                    print(f"[load_env]   跳过（已存在）: {key}", file=sys.stderr)

    return newly_loaded


def check_required_vars(required: list = None) -> list:
    """
    检查必需的环境变量是否已设置。
    返回缺失的变量名列表（空列表表示全部已设置）。
    
    Note: 凭证检查应通过 alibabacloud_credentials 进行，此函数仅检查其他配置变量。
    """
    if required is None:
        required = []  # 凭证通过 alibabacloud_credentials 管理，不检查 AK/SK 环境变量
    return [k for k in required if not os.environ.get(k)]


def _print_setup_hint(missing_vars: list) -> None:
    """当环境变量加载失败时，向用户打印详细的配置引导提示。"""
    # 过滤掉 AK/SK 相关的变量，只显示其他配置变量
    config_vars = [v for v in missing_vars if 'ACCESS_KEY' not in v]
    
    hint = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    阿里云MPS环境变量未配置                          ║
╚══════════════════════════════════════════════════════════════════╝

【凭证配置】请使用 Aliyun CLI 配置凭证：
  aliyun configure
  # 按提示输入凭证信息，配置完成后运行 'aliyun configure list' 验证

"""
    if config_vars:
        config_str = "\n".join(f"    export {k}=<your_value>" for k in config_vars)
        hint += f"""【其他配置】以下环境变量需要设置：
{config_str}

  OSS 信息可以在阿里云控制台 https://oss.console.aliyun.com/ 获取
"""
    
    hint += """
开通 MPS 服务可以在阿里云控制台 https://mts.console.aliyun.com/ 开通
密钥可以在阿里云控制台 https://ram.console.aliyun.com/manage/ak 获取

⚠️  安全提示：请勿在代码中硬编码密钥，使用 aliyun configure 安全配置。
"""
    print(hint, file=sys.stderr)


def ensure_env_loaded(
    required: list = None,
    verbose: bool = False,
) -> bool:
    """
    确保必需的环境变量已加载。

    执行流程：
      1. 检查必需变量是否已在 os.environ 中
      2. 如果有缺失，扫描候选文件并加载
      3. 再次检查，返回是否全部就绪

    参数：
      required  — 必须存在的变量列表（凭证通过 alibabacloud_credentials 管理）
      verbose   — 是否打印加载日志到 stderr

    返回：True 表示所有必需变量均已就绪，False 表示仍有缺失
    """
    if required is None:
        required = []  # 凭证通过 alibabacloud_credentials 管理，不检查 AK/SK 环境变量

    missing_before = check_required_vars(required)
    if not missing_before:
        # 全部已就绪，无需加载
        return True

    if verbose:
        print(
            f"[load_env] 检测到缺失变量: {missing_before}，开始扫描环境变量文件...",
            file=sys.stderr,
        )

    load_env_files(verbose=verbose)

    missing_after = check_required_vars(required)
    if missing_after:
        return False

    if verbose:
        print("[load_env] 所有必需变量已加载完成。", file=sys.stderr)
    return True


# ─── 独立运行时：诊断模式 ───────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="扫描系统环境变量文件并加载阿里云 MPS 所需变量（诊断模式）"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="显示详细加载日志"
    )
    parser.add_argument(
        "--check-only", action="store_true", help="仅检查当前环境变量状态，不加载"
    )
    args = parser.parse_args()

    if args.check_only:
        print("=== 当前环境变量状态 ===")
        for var in sorted(_TARGET_VARS):
            val = os.environ.get(var, "")
            if val:
                display = val[:4] + "****" if len(val) > 4 else "****"
                status = f"✅ 已设置 ({display})"
            else:
                status = "❌ 未设置"
            print(f"  {var}: {status}")
        sys.exit(0)

    print("=== 扫描环境变量文件 ===", flush=True)
    newly = load_env_files(verbose=True)
    sys.stderr.flush()

    print("\n=== 加载结果 ===")
    for var in sorted(_TARGET_VARS):
        val = os.environ.get(var, "")
        if val:
            display = val[:4] + "****" if len(val) > 4 else "****"
            status = f"✅ 已设置 ({display})"
        else:
            status = "❌ 未设置"
        print(f"  {var}: {status}")

    if newly:
        print(f"\n本次新加载了 {len(newly)} 个变量: {list(newly.keys())}")
    else:
        print("\n未加载任何新变量（已全部设置或文件中无目标变量）")

    # 检查凭证是否可用（通过 alibabacloud_credentials）
    if not check_credentials():
        _print_setup_hint([])
        sys.exit(1)
