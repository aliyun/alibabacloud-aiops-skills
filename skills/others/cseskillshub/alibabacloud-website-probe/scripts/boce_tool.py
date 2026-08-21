#!/usr/bin/env python3
"""
Boce Tool - Pure HTTP Python Implementation
Replicates https://boce.aliyun.com/detect/* (网络拨测工具)

Authentication: XSRF-TOKEN cookie + header (auto-acquired from page visit).
Supports: DNS, HTTP, PING, MTR, Traceroute detection from 200+ global probe nodes.
"""

import sys
import json
import time
import random
import string
import argparse
import os
import re
import pathlib
import secrets
from typing import Optional, Any, List, Dict
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import urllib3

# ─── Config ───────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30  # seconds per request
MAX_WORKERS = 6       # concurrent threads
POLL_INTERVAL = 3     # seconds between result polls
POLL_TIMEOUT = 120    # max seconds to wait for results
MAX_NODES_DEFAULT = 50
SKILL_VERSION = "0.1.0"
# Observability (platform rule SA-2.11): the User-Agent MUST follow the template
# AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}, where SKILL_NAME equals
# the SKILL.md frontmatter name and session-id is a 32-char lowercase hex string
# generated once per session and shared by every backend used in that session.
SKILL_NAME = "alibabacloud-website-probe"
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
_RUN_SESSION_ID = None


def get_run_session_id() -> str:
    """Return the session-id: 32-char lowercase hex, generated once per session.

    The value is cached at module level so that every backend touched during the
    same run reports the same session-id. It can be pinned externally through
    the SKILL_SESSION_ID environment variable, which is only honoured when it is
    a valid 32-char lowercase hex string; anything else is ignored so the header
    can never drift from the required format.
    """
    global _RUN_SESSION_ID
    if _RUN_SESSION_ID is None:
        external = os.environ.get("SKILL_SESSION_ID", "")
        if re.fullmatch(r"[0-9a-f]{32}", external):
            _RUN_SESSION_ID = external
        else:
            _RUN_SESSION_ID = secrets.token_hex(16)
    return _RUN_SESSION_ID


def build_user_agent() -> str:
    """Render the mandatory Agent-Skills User-Agent for this session."""
    return UA_TEMPLATE.format(skill_name=SKILL_NAME, session_id=get_run_session_id())

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_URL = "https://boce.aliyun.com"
API_ENDPOINT = "/data/api.json"
INIT_PAGE = "/detect/dns"

PRODUCT_CREATE = "metrics20180308"
PRODUCT_QUERY = "metrics20190101"

# Mobile probe (AgentGroup=2) invalid city+isp blocklist.
# Read-only reference data embedded as a module-level constant (the scripts/
# directory may only contain executable code, no data files).
# Keys use Chinese names matching boce node `CityName.zh_CN` / `IspName.zh_CN`.
MOBILE_INVALID_COMBOS = frozenset({
    ("中卫市", "移动"),
    ("乌鲁木齐市", "联通"),
    ("厦门市", "电信"),
    ("厦门市", "移动"),
    ("合肥市", "电信"),
    ("吕梁市", "联通"),
    ("嘉兴市", "电信"),
    ("天津市", "电信"),
    ("忻州市", "联通"),
    ("杭州市", "电信"),
    ("杭州市", "移动"),
    ("杭州市", "联通"),
    ("沧州市", "联通"),
    ("河源市", "电信"),
    ("泉州市", "电信"),
    ("泰州市", "电信"),
    ("深圳市", "联通"),
    ("衡水市", "联通"),
    ("襄阳", "移动"),
    ("西宁市", "移动"),
    ("贵阳市", "电信"),
    ("连云港市", "移动"),
    ("通化市", "电信"),
    ("鄂尔多斯市", "联通"),
    ("重庆市", "电信"),
    ("重庆市", "移动"),
    ("镇江市", "电信"),
})

TASK_TYPES = {
    "http": "1",
    "ping": "2",
    "dns": "5",
    "traceroute": "9",
    "mtr": "12",
}

ISP_MAP = {
    "电信": "132",
    "联通": "232",
    "移动": "5",
    "阿里巴巴": "465",
    "亚马逊": "18825",
    "谷歌": "18828",
    "微软": "18857",
    "ens": "18885",
}

AREA_MAP = {
    "华东": "HuaDong",
    "华南": "HuaNan",
    "华北": "HuaBei",
    "华中": "HuaZhong",
    "东北": "DongBei",
    "西南": "XiNan",
    "西北": "XiBei",
    "境外": "Overseas",
}

DNS_TYPES = ["A", "AAAA", "MX", "NS", "CNAME", "TXT", "ANY"]
HTTP_METHODS = ["get", "post", "head"]

# ─── Auth ─────────────────────────────────────────────────────────────────────
COOKIE_DOMAIN = "boce.aliyun.com"
CACHE_DIR = pathlib.Path.home() / ".qoderwork" / "cache"
CACHE_FILE = CACHE_DIR / "boce_session.json"
CACHE_TTL_SECONDS = 7200  # 2 hours

SESSION_HELP_MSG = """
================================================================
  无法获取 XSRF-TOKEN。

  可能原因：
  1. 网络无法访问 boce.aliyun.com (检查 VPN/DNS)
  2. 站点临时不可用

  解决方案：
  1. 确认可以在浏览器中打开 https://boce.aliyun.com/detect/dns
  2. 重新运行本脚本，或使用 --refresh 参数强制刷新
================================================================
"""


class TokenExpiredError(Exception):
    """Raised when XSRF token is expired and needs refresh."""
    pass


# ─── Cookie Cache Layer ───────────────────────────────────────────────────────

def _load_cache() -> Optional[Dict[str, str]]:
    """Load session data from local cache. Returns dict with 'xsrf_token' and 'cookies'."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        if time.time() > cache.get("expires_at", 0):
            return None
        if not cache.get("xsrf_token"):
            return None
        return cache
    except (json.JSONDecodeError, IOError, KeyError):
        return None


def _save_cache(xsrf_token: str, cookies: dict, ttl: int = CACHE_TTL_SECONDS):
    """Save session data to local cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache = {
            "xsrf_token": xsrf_token,
            "cookies": cookies,
            "cached_at": int(time.time()),
            "expires_at": int(time.time()) + ttl,
            "domain": COOKIE_DOMAIN,
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
        os.chmod(CACHE_FILE, 0o600)
    except Exception:
        pass


def _invalidate_cache():
    """Remove the local session cache file."""
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
    except Exception:
        pass


def _acquire_token_from_page(session: requests.Session) -> Optional[str]:
    """Visit the detection page to acquire XSRF-TOKEN cookie."""
    try:
        resp = session.get(
            f"{BASE_URL}{INIT_PAGE}",
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        resp.raise_for_status()
        xsrf = session.cookies.get("XSRF-TOKEN")
        if xsrf:
            # Save all cookies to cache
            cookies = {c.name: c.value for c in session.cookies}
            _save_cache(xsrf, cookies)
            return xsrf
        return None
    except Exception:
        return None


def build_session(refresh: bool = False) -> requests.Session:
    """
    Build a requests.Session with XSRF-TOKEN.
    
    Layered strategy:
    1. Local cache (fastest)
    2. Direct page visit (fallback)
    
    TLS verification is always enforced for the boce platform session; the
    User-Agent follows the mandatory template
    AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id} so every request issued
    during this session is traceable on the platform side.
    """
    session = requests.Session()
    session.verify = True
    
    # Connection pooling
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=urllib3.Retry(total=2, backoff_factor=0.3,
                                  status_forcelist=[502, 503, 504])
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Observability: mandatory UA template + session-id generated once per session
    session.headers.update({
        "User-Agent": build_user_agent(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/detect/dns",
        "bx-v": "2.5.36",
    })

    xsrf_token = None

    if not refresh:
        # Layer 1: Try local cache
        cached = _load_cache()
        if cached:
            xsrf_token = cached["xsrf_token"]
            for name, value in cached.get("cookies", {}).items():
                session.cookies.set(name, value, domain=COOKIE_DOMAIN)
    
    if not xsrf_token:
        # Layer 2: Direct page visit
        xsrf_token = _acquire_token_from_page(session)
    
    if not xsrf_token:
        print(SESSION_HELP_MSG, file=sys.stderr)
        sys.exit(1)
    
    # Set the XSRF header
    session.headers["X-Xsrf-Token"] = xsrf_token
    session.cookies.set("XSRF-TOKEN", xsrf_token, domain=COOKIE_DOMAIN)
    
    # Store token on session for refresh logic
    session._boce_xsrf_token = xsrf_token
    return session


def refresh_session(session: requests.Session) -> bool:
    """Refresh the XSRF token by re-visiting the page."""
    _invalidate_cache()
    # Clear existing cookies
    session.cookies.clear()
    xsrf_token = _acquire_token_from_page(session)
    if xsrf_token:
        session.headers["X-Xsrf-Token"] = xsrf_token
        session._boce_xsrf_token = xsrf_token
        return True
    return False


# ─── API Layer ────────────────────────────────────────────────────────────────

def _generate_task_name() -> str:
    """Generate unique task name: <hex8>_<timestamp>"""
    hex_part = ''.join(random.choices(string.hexdigits[:16], k=8))
    return f"{hex_part}_{int(time.time() * 1000)}"


def _call_api(session: requests.Session, action: str, params: dict,
              product: str = PRODUCT_QUERY, include_umid: bool = False,
              _retry: bool = True) -> dict:
    """
    Call boce API with auto-retry on token expiry.
    
    Args:
        session: requests.Session with XSRF token
        action: API action name
        params: params dict (will be JSON-encoded and URL-encoded)
        product: product version string
        include_umid: whether to include umid/collina params
        _retry: internal flag for retry logic
    
    Returns:
        Parsed JSON response dict
    
    Raises:
        TokenExpiredError: when token is expired and refresh failed
    """
    url = f"{BASE_URL}{API_ENDPOINT}?action={action}"
    
    form_data = {
        "csrf_token": "mock-sec-token",
        "_csrf": "mock-sec-token",
        "sec_token": "mock-sec-token",
        "product": product,
        "action": action,
        "region": "cn-hangzhou",
        "params": json.dumps(params, ensure_ascii=False),
    }
    
    if include_umid:
        form_data["umid"] = "mock-umid"
        form_data["collina"] = "mock-collina-ua"
    
    try:
        resp = session.post(url, data=form_data, timeout=REQUEST_TIMEOUT)
        
        # Check for token expiry
        if resp.status_code == 403 or resp.status_code == 302:
            if _retry and refresh_session(session):
                return _call_api(session, action, params, product, include_umid, _retry=False)
            raise TokenExpiredError("XSRF token expired and refresh failed")
        
        resp.raise_for_status()
        result = resp.json()
        
        # Check for API-level errors
        if result.get("code") != "200":
            error_msg = result.get("msg", result.get("message", "Unknown error"))
            # Handle rate limiting with backoff retry
            if "flow control" in str(error_msg).lower() or "限流" in str(error_msg):
                if _retry:
                    time.sleep(3)  # Wait 3 seconds before retry
                    return _call_api(session, action, params, product, include_umid, _retry=False)
            if "token" in str(error_msg).lower() or "csrf" in str(error_msg).lower():
                if _retry and refresh_session(session):
                    return _call_api(session, action, params, product, include_umid, _retry=False)
                raise TokenExpiredError(f"Token error: {error_msg}")
            raise RuntimeError(f"API error [{action}]: {error_msg}")
        
        return result
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise RuntimeError(f"Network error [{action}]: {e}")


# ─── Probe Nodes ──────────────────────────────────────────────────────────────

def get_probe_nodes(session: requests.Session, task_type: str = "5",
                    ipv6: bool = False) -> List[Dict]:
    """
    Get available probe nodes for a given task type.
    
    Args:
        session: authenticated session
        task_type: "1"(HTTP), "2"(PING), "5"(DNS), "9"(Traceroute), "12"(MTR)
        ipv6: whether to get IPv6 nodes
    
    Returns:
        List of node dicts with isp/city/area info
    """
    params = {
        "City": "",
        "TaskType": task_type,
    }
    if ipv6:
        params["IPV6"] = True
    else:
        params["IPV4"] = True
    
    result = _call_api(session, "DescribeSiteMonitorISPCityList", params)
    nodes = result.get("data", {}).get("IspCityList", {}).get("IspCity", [])
    return nodes


def filter_nodes(nodes: List[Dict], regions: Optional[List[str]] = None,
                 isps: Optional[List[str]] = None,
                 max_nodes: int = MAX_NODES_DEFAULT) -> List[Dict]:
    """
    Filter probe nodes by region and ISP.
    
    Args:
        nodes: list of node dicts from get_probe_nodes
        regions: list of region names in Chinese (华东,华南,etc.)
        isps: list of ISP names in Chinese (电信,联通,移动,etc.)
        max_nodes: maximum number of nodes to return
    
    Returns:
        Filtered and limited list of nodes
    """
    filtered = nodes
    
    if regions:
        area_set = set(regions)
        # "境外" special semantics: match any node whose Area is NOT one of the
        # seven mainland regions (covers boce nodes tagged 境外 or any other
        # non-mainland value). Can be combined with mainland region names.
        if "境外" in area_set:
            mainland_areas = {"华东", "华南", "华北", "华中", "东北", "西南", "西北"}
            area_set.discard("境外")
            if area_set:
                filtered = [n for n in filtered
                            if n.get("Area.zh_CN") in area_set
                            or n.get("Area.zh_CN") not in mainland_areas]
            else:
                filtered = [n for n in filtered
                            if n.get("Area.zh_CN") not in mainland_areas]
        else:
            filtered = [n for n in filtered if n.get("Area.zh_CN") in area_set]
    
    if isps:
        isp_name_set = set(isps)
        filtered = [n for n in filtered if n.get("IspName.zh_CN") in isp_name_set]
    
    # Deterministic stratified sampling by Area/ISP when limiting:
    # round-robin over (Area, ISP) groups guarantees at least one node per
    # group (as long as max_nodes allows), and the selection is fully
    # reproducible across runs for the same node list.
    if len(filtered) > max_nodes:
        groups: Dict[tuple, List[Dict]] = {}
        for n in filtered:
            key = (n.get("Area.zh_CN", ""), n.get("IspName.zh_CN", ""))
            groups.setdefault(key, []).append(n)
        # Stable intra-group ordering keeps the sampling deterministic
        for g in groups.values():
            g.sort(key=lambda n: (n.get("CityName.zh_CN", ""), str(n.get("City", ""))))
        selected: List[Dict] = []
        keys = sorted(groups.keys())
        while len(selected) < max_nodes:
            progressed = False
            for key in keys:
                if len(selected) >= max_nodes:
                    break
                if groups[key]:
                    selected.append(groups[key].pop(0))
                    progressed = True
            if not progressed:
                break
        filtered = selected
    
    return filtered


# ─── Detection Functions ──────────────────────────────────────────────────────

def _load_mobile_invalid_combos() -> frozenset:
    """
    Return the blocklist of (city_name, isp_name) tuples known unsupported by
    mobile probes (AgentGroup=2). Embedded as a module-level constant
    (MOBILE_INVALID_COMBOS); no external data file is read.
    """
    return MOBILE_INVALID_COMBOS


def _filter_mobile_unsupported(nodes: List[Dict]) -> (List[Dict], List[tuple]):
    """
    Pre-filter nodes against the mobile-incompatible blocklist.
    Returns (kept_nodes, dropped_tuples_for_logging).
    """
    blocklist = _load_mobile_invalid_combos()
    if not blocklist:
        return nodes, []
    kept, dropped = [], []
    for n in nodes:
        city = n.get("CityName.zh_CN")
        isp = n.get("IspName.zh_CN")
        if (city, isp) in blocklist:
            dropped.append((city, isp))
        else:
            kept.append(n)
    return kept, dropped


def _parse_invalid_combos_from_error(result: dict) -> List[Dict]:
    """
    Extract invalid_isp_city_name list from a boce error response.
    The Message field is a JSON string like:
        {"invalid_isp_city_name":[{"city":"天津市","isp":"电信"}], ...}
    """
    try:
        data = result.get("data", {}) if isinstance(result, dict) else {}
        msg = data.get("Message")
        if not msg:
            return []
        msg_data = json.loads(msg) if isinstance(msg, str) else msg
        items = msg_data.get("invalid_isp_city_name", [])
        return [c for c in items if isinstance(c, dict) and c.get("city") and c.get("isp")]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def _create_task(session: requests.Session, task_type: str, address: str,
                 nodes: List[Dict], options: dict,
                 agent_group: str = "1") -> str:
    """
    Create a one-time detection task and return task ID.
    
    Args:
        session: authenticated session
        task_type: TaskType string (1/2/5/9/12)
        address: target address
        nodes: list of probe nodes to use
        options: detection options dict
        agent_group: "1" for PC, "2" for Mobile
    
    Returns:
        taskId string
    
    Mobile-probe handling (agent_group="2"):
        1. Pre-filters nodes against the built-in MOBILE_INVALID_COMBOS
           blocklist (city+isp combos known unsupported by mobile probes).
        2. If boce backend still returns Code=655 invalid_isp_city, parses the
           offending combos from the error and retries ONCE with the remaining
           nodes. The blocklist is read-only reference data; nothing is
           written back.
    """
    is_mobile = (agent_group == "2")
    
    # Pre-filter mobile-incompatible city+isp combos
    if is_mobile:
        nodes, dropped = _filter_mobile_unsupported(nodes)
        if dropped:
            print(f"[INFO] mobile 探针预过滤丢弃 {len(dropped)} 个不支持组合: {dropped}",
                  file=sys.stderr)
        if not nodes:
            raise RuntimeError(
                "Mobile probe: all nodes were filtered out by the "
                "mobile_invalid_combos blocklist; no probes left to dispatch."
            )
    
    task_name = _generate_task_name()
    
    def _do_submit(node_list: List[Dict]) -> dict:
        isp_city = [{"isp": n["Isp"], "city": n["City"]} for n in node_list]
        params = {
            "TaskList.1.TaskType": task_type,
            "TaskList.1.TaskName": task_name,
            "TaskList.1.Address": address,
            "TaskList.1.Interval": 0,
            "TaskList.1.IspCity": isp_city,
            "TaskList.1.AgentGroup": agent_group,
            "TaskList.1.Options": options,
        }
        return _call_api(
            session, "BatchCreateOnceSiteMonitor", params,
            product=PRODUCT_CREATE, include_umid=True
        )
    
    result = _do_submit(nodes)
    data = result.get("data", {}).get("Data", [])
    
    # Retry once on mobile invalid_isp_city (no write-back to blocklist)
    if not data and is_mobile:
        invalid = _parse_invalid_combos_from_error(result)
        if invalid:
            invalid_set = {(c["city"], c["isp"]) for c in invalid}
            remaining = [
                n for n in nodes
                if (n.get("CityName.zh_CN"), n.get("IspName.zh_CN")) not in invalid_set
            ]
            if remaining:
                print(f"[INFO] mobile 探针: 自动重试，剩余 {len(remaining)} 节点",
                      file=sys.stderr)
                result = _do_submit(remaining)
                data = result.get("data", {}).get("Data", [])
    
    if not data:
        raise RuntimeError(f"Task creation failed: {result}")
    
    return data[0]["taskId"]


def _poll_results(session: requests.Session, task_id: str,
                  expected_count: int = 0,
                  timeout: int = POLL_TIMEOUT) -> List[Dict]:
    """
    Poll for detection results until ready or timeout.
    
    Uses a two-phase approach:
    - Phase 1: Wait until first results appear
    - Phase 2: Keep polling until no new results arrive for 2 consecutive polls
               or expected_count is reached or timeout
    
    Args:
        session: authenticated session
        task_id: task ID from create
        expected_count: expected number of results (0 = unknown)
        timeout: max wait time in seconds
    
    Returns:
        List of result dicts
    """
    deadline = time.time() + timeout
    last_count = 0
    stable_polls = 0  # consecutive polls with same count
    best_results = []
    
    while time.time() < deadline:
        end_time = int(time.time() * 1000)
        start_time = end_time - 7200000  # 2 hours window
        
        params = {
            "TaskIds": task_id,
            "UseFormatter": True,
            "EndTime": end_time,
            "StartTime": start_time,
        }
        
        result = _call_api(
            session, "DescribeSiteMonitorLog", params,
            product=PRODUCT_QUERY, include_umid=True
        )
        
        data_str = result.get("data", {}).get("Data", "[]")
        
        # Data is a JSON string
        if isinstance(data_str, str):
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = []
        else:
            data = data_str if isinstance(data_str, list) else []
        
        if data:
            best_results = data
            current_count = len(data)
            
            # Check if we have all expected results
            if expected_count > 0 and current_count >= expected_count:
                return best_results
            
            # Check if results are stable (no new results for 2 polls)
            if current_count == last_count:
                stable_polls += 1
                if stable_polls >= 2:
                    return best_results
            else:
                stable_polls = 0
            
            last_count = current_count
        
        time.sleep(POLL_INTERVAL)
    
    # Return whatever we have, even if incomplete
    if best_results:
        return best_results
    
    raise TimeoutError(f"Detection timed out after {timeout}s (taskId={task_id})")


def detect_dns(session: requests.Session, target: str,
               dns_type: str = "A", dns_server: str = "",
               nodes: Optional[List[Dict]] = None,
               agent_group: str = "1",
               timeout: int = 30000, poll_timeout: int = POLL_TIMEOUT) -> List[Dict]:
    """
    Perform DNS detection.
    
    Args:
        session: authenticated session
        target: domain to resolve
        dns_type: A/AAAA/MX/NS/CNAME/TXT/ANY
        dns_server: custom DNS server (empty for operator default)
        nodes: probe nodes (if None, uses default selection)
        timeout: detection timeout in ms
        poll_timeout: max wait for results in seconds
    
    Returns:
        List of per-node result dicts
    """
    if nodes is None:
        all_nodes = get_probe_nodes(session, task_type="5")
        nodes = filter_nodes(all_nodes, max_nodes=MAX_NODES_DEFAULT)
    
    options = {
        "time_out": timeout,
        "enable_operator_dns": not bool(dns_server),
        "count": 5,
        "dns_type": dns_type.upper(),
    }
    if dns_server:
        options["dns_server"] = dns_server
    
    task_id = _create_task(session, "5", target, nodes, options, agent_group=agent_group)
    return _poll_results(session, task_id, expected_count=len(nodes), timeout=poll_timeout)


def detect_http(session: requests.Session, target: str,
                method: str = "get", dns_server: str = "",
                verify_cert: bool = False, no_redirect: bool = False,
                headers: str = "", cookie: str = "",
                proxy_protocol: bool = False,
                agent_group: str = "1",
                nodes: Optional[List[Dict]] = None,
                timeout: int = 30000, poll_timeout: int = POLL_TIMEOUT) -> List[Dict]:
    """
    Perform HTTP(S) detection.
    
    Args:
        session: authenticated session
        target: full URL (must include https:// or http://)
        method: get/post/head
        dns_server: custom DNS server
        verify_cert: whether to verify SSL cert
        no_redirect: don't follow redirects
        headers: custom HTTP headers (format: "key1:value1\nkey2:value2")
        cookie: custom cookies (format: "key1=value1;key2=value2")
        proxy_protocol: enable ProxyProtocol
        agent_group: "1" for PC, "2" for Mobile
        nodes: probe nodes
        timeout: detection timeout in ms
        poll_timeout: max wait for results in seconds
    
    Returns:
        List of per-node result dicts
    """
    if not target.startswith(("http://", "https://")):
        target = f"https://{target}"
    
    if nodes is None:
        all_nodes = get_probe_nodes(session, task_type="1")
        nodes = filter_nodes(all_nodes, max_nodes=MAX_NODES_DEFAULT)
    
    options = {
        "time_out": timeout,
        "enable_operator_dns": not bool(dns_server),
        "count": 5,
        "http_method": method.lower(),
        "dns_server": dns_server if dns_server else "",
        "cert_verify": verify_cert,
        "unfollow_redirect": no_redirect,
    }
    
    if headers:
        options["header"] = headers
    if cookie:
        options["cookie"] = cookie
    if proxy_protocol:
        options["proxy_protocol"] = True
    
    task_id = _create_task(session, "1", target, nodes, options, agent_group=agent_group)
    return _poll_results(session, task_id, expected_count=len(nodes), timeout=poll_timeout)


def detect_ping(session: requests.Session, target: str,
                dns_server: str = "",
                nodes: Optional[List[Dict]] = None,
                agent_group: str = "1",
                timeout: int = 30000, poll_timeout: int = POLL_TIMEOUT) -> List[Dict]:
    """
    Perform PING detection.
    
    Args:
        session: authenticated session
        target: domain or IP
        dns_server: custom DNS server
        nodes: probe nodes
        timeout: detection timeout in ms
        poll_timeout: max wait for results in seconds
    
    Returns:
        List of per-node result dicts
    """
    if nodes is None:
        all_nodes = get_probe_nodes(session, task_type="2")
        nodes = filter_nodes(all_nodes, max_nodes=MAX_NODES_DEFAULT)
    
    options = {
        "time_out": timeout,
        "enable_operator_dns": not bool(dns_server),
        "count": 5,
    }
    if dns_server:
        options["dns_server"] = dns_server
    
    task_id = _create_task(session, "2", target, nodes, options, agent_group=agent_group)
    return _poll_results(session, task_id, expected_count=len(nodes), timeout=poll_timeout)


def detect_mtr(session: requests.Session, target: str,
               nodes: Optional[List[Dict]] = None,
               agent_group: str = "1",
               timeout: int = 30000, poll_timeout: int = 90) -> List[Dict]:
    """
    Perform MTR detection (longer timeout due to route tracing).
    
    Args:
        session: authenticated session
        target: domain or IP
        nodes: probe nodes
        timeout: detection timeout in ms
        poll_timeout: max wait for results in seconds (default 90s for MTR)
    
    Returns:
        List of per-node result dicts
    """
    if nodes is None:
        all_nodes = get_probe_nodes(session, task_type="12")
        nodes = filter_nodes(all_nodes, max_nodes=MAX_NODES_DEFAULT)
    
    options = {
        "time_out": timeout,
        "enable_operator_dns": True,
        "count": 5,
    }
    
    task_id = _create_task(session, "12", target, nodes, options, agent_group=agent_group)
    return _poll_results(session, task_id, expected_count=len(nodes), timeout=poll_timeout)


def detect_traceroute(session: requests.Session, target: str,
                      nodes: Optional[List[Dict]] = None,
                      agent_group: str = "1",
                      timeout: int = 30000, poll_timeout: int = 90) -> List[Dict]:
    """
    Perform Traceroute detection (longer timeout due to route tracing).
    
    Args:
        session: authenticated session
        target: domain or IP
        nodes: probe nodes
        timeout: detection timeout in ms
        poll_timeout: max wait for results in seconds (default 90s)
    
    Returns:
        List of per-node result dicts
    """
    if nodes is None:
        all_nodes = get_probe_nodes(session, task_type="9")
        nodes = filter_nodes(all_nodes, max_nodes=MAX_NODES_DEFAULT)
    
    options = {
        "time_out": timeout,
        "enable_operator_dns": True,
        "count": 5,
    }
    
    task_id = _create_task(session, "9", target, nodes, options, agent_group=agent_group)
    return _poll_results(session, task_id, expected_count=len(nodes), timeout=poll_timeout)


# ─── Output Formatting ────────────────────────────────────────────────────────

def format_dns_results(results: List[Dict]) -> str:
    """Format DNS detection results as a readable table."""
    lines = []
    lines.append(f"{'地区':<6} {'城市':<8} {'运营商':<6} {'DNS服务器':<16} {'解析耗时(ms)':<12} {'解析结果'}")
    lines.append("-" * 100)
    
    # Sort by area then city
    results.sort(key=lambda x: (x.get("areaCN", ""), x.get("cityCN", "")))
    
    success_count = 0
    fail_count = 0
    total_time = 0
    
    for r in results:
        area = r.get("areaCN", "-")
        city = r.get("cityCN", "-")
        isp = r.get("ispCN", "-")
        dns_server = r.get("dnsServer", r.get("targetIp", "-"))
        total_t = r.get("TotalTime", 0)
        error_code = r.get("errorCode", 0)
        
        if error_code == 0:
            ips = r.get("ips", "").strip(",")
            cnames = r.get("cnames", "").strip(",")
            result_str = ips if ips else cnames if cnames else "OK"
            success_count += 1
            total_time += total_t
        else:
            result_str = f"ERROR: {r.get('message', 'Unknown')}"
            fail_count += 1
        
        lines.append(f"{area:<6} {city:<8} {isp:<6} {dns_server:<16} {total_t:<12.2f} {result_str}")
    
    # Summary
    lines.append("-" * 100)
    avg_time = total_time / success_count if success_count > 0 else 0
    lines.append(f"总计: {len(results)} 个节点 | 成功: {success_count} | 失败: {fail_count} | 平均耗时: {avg_time:.2f}ms")
    
    return "\n".join(lines)


def format_http_results(results: List[Dict]) -> str:
    """Format HTTP detection results as a readable table."""
    lines = []
    lines.append(f"{'地区':<6} {'城市':<8} {'运营商':<6} {'状态码':<6} {'总耗时(ms)':<10} {'DNS(ms)':<8} {'TCP(ms)':<8} {'SSL(ms)':<8} {'目标IP'}")
    lines.append("-" * 110)
    
    results.sort(key=lambda x: (x.get("areaCN", ""), x.get("cityCN", "")))
    
    success_count = 0
    fail_count = 0
    total_time = 0
    
    for r in results:
        area = r.get("areaCN", "-")
        city = r.get("cityCN", "-")
        isp = r.get("ispCN", "-")
        status = int(r.get("HTTPResponseCode", 0))
        total_t = r.get("TotalTime", 0)
        dns_t = r.get("HTTPDNSTime", 0)
        tcp_t = r.get("tcpConnectTime", 0)
        ssl_t = r.get("SSLConnectTime", 0)
        target_ip = r.get("targetIp", "-")
        
        if status > 0:
            success_count += 1
            total_time += total_t
        else:
            fail_count += 1
        
        lines.append(f"{area:<6} {city:<8} {isp:<6} {status:<6} {total_t:<10.2f} {dns_t:<8.1f} {tcp_t:<8.1f} {ssl_t:<8.1f} {target_ip}")
    
    lines.append("-" * 110)
    avg_time = total_time / success_count if success_count > 0 else 0
    lines.append(f"总计: {len(results)} 个节点 | 成功: {success_count} | 失败: {fail_count} | 平均耗时: {avg_time:.2f}ms")
    
    return "\n".join(lines)


def format_ping_results(results: List[Dict]) -> str:
    """Format PING detection results as a readable table."""
    lines = []
    lines.append(f"{'地区':<6} {'城市':<8} {'运营商':<6} {'平均RTT(ms)':<12} {'最小(ms)':<10} {'最大(ms)':<10} {'丢包率(%)':<10} {'目标IP'}")
    lines.append("-" * 100)
    
    results.sort(key=lambda x: (x.get("areaCN", ""), x.get("cityCN", "")))
    
    success_count = 0
    fail_count = 0
    total_rtt = 0
    
    for r in results:
        area = r.get("areaCN", "-")
        city = r.get("cityCN", "-")
        isp = r.get("ispCN", "-")
        avg_rtt = r.get("TotalTime", 0)
        min_rtt = r.get("pingMinTime", 0)
        max_rtt = r.get("pingMaxTime", 0)
        loss = r.get("failureRate", 0)
        target_ip = r.get("targetIp", "-")
        
        if avg_rtt > 0 or r.get("pingReceivedNum", 0) > 0:
            success_count += 1
            total_rtt += avg_rtt
        else:
            fail_count += 1
        
        lines.append(f"{area:<6} {city:<8} {isp:<6} {avg_rtt:<12.2f} {min_rtt:<10.2f} {max_rtt:<10.2f} {loss:<10.1f} {target_ip}")
    
    lines.append("-" * 100)
    avg = total_rtt / success_count if success_count > 0 else 0
    lines.append(f"总计: {len(results)} 个节点 | 成功: {success_count} | 失败: {fail_count} | 平均RTT: {avg:.2f}ms")
    
    return "\n".join(lines)


def format_mtr_results(results: List[Dict]) -> str:
    """Format MTR detection results."""
    lines = []
    
    results.sort(key=lambda x: (x.get("areaCN", ""), x.get("cityCN", "")))
    
    for r in results:
        area = r.get("areaCN", "-")
        city = r.get("cityCN", "-")
        isp = r.get("ispCN", "-")
        source_ip = r.get("sourceIp", "-")
        target_ip = r.get("targetIp", "-")
        
        lines.append(f"\n{'='*80}")
        lines.append(f"[{area} {city} {isp}] {source_ip} → {target_ip}")
        lines.append(f"{'='*80}")
        
        route_json = r.get("routeJson", [])
        if isinstance(route_json, str):
            try:
                route_json = json.loads(route_json)
            except (json.JSONDecodeError, TypeError):
                route_json = []
        if route_json and isinstance(route_json, list) and isinstance(route_json[0], dict):
            lines.append(f"  {'TTL':<4} {'IP':<20} {'Loss%':<7} {'Snt':<5} {'Last(ms)':<10} {'Avg(ms)':<10} {'Best(ms)':<10} {'Worst(ms)':<10}")
            lines.append(f"  {'-'*76}")
            for hop in route_json:
                ttl = hop.get("ttl", 0)
                addr = hop.get("address_to", "*")
                loss = hop.get("loss", 0)
                snt = hop.get("snt", 0)
                last = hop.get("last", 0)
                avg = hop.get("avg", 0)
                best = hop.get("best", 0)
                worst = hop.get("worst", 0)
                lines.append(f"  {ttl:<4} {addr:<20} {loss:<7.1f} {snt:<5} {last:<10.2f} {avg:<10.2f} {best:<10.2f} {worst:<10.2f}")
        else:
            route_text = r.get("route", "No route data")
            lines.append(route_text)
    
    return "\n".join(lines)


def format_traceroute_results(results: List[Dict]) -> str:
    """Format Traceroute detection results."""
    lines = []
    
    results.sort(key=lambda x: (x.get("areaCN", ""), x.get("cityCN", "")))
    
    for r in results:
        area = r.get("areaCN", "-")
        city = r.get("cityCN", "-")
        isp = r.get("ispCN", "-")
        source_ip = r.get("sourceIp", "-")
        target_ip = r.get("targetIp", "-")
        error_code = r.get("errorCode", 0)
        message = r.get("message", "")
        
        lines.append(f"\n{'='*60}")
        lines.append(f"[{area} {city} {isp}] {source_ip} -> {target_ip}")
        lines.append(f"{'='*60}")
        
        if error_code != 0:
            lines.append(f"  ERROR: {message} (code={error_code})")
            continue
        
        route = r.get("route", "")
        if isinstance(route, list) and route:
            for i, hop in enumerate(route, 1):
                if isinstance(hop, dict):
                    ip = hop.get("ip", "*")
                    rtt = hop.get("rtt", 0)
                    if ip == "-" or ip == "*":
                        lines.append(f"  {i:>2}  *  (timeout)")
                    else:
                        lines.append(f"  {i:>2}  {ip:<20} {rtt}ms")
                else:
                    lines.append(f"  {i:>2}  {hop}")
        elif isinstance(route, str) and route.strip():
            lines.append(route)
        else:
            lines.append("  (no route data - target may be unreachable from this node)")
    
    lines.append(f"\n{'='*60}")
    lines.append(f"总计: {len(results)} 个节点")
    
    return "\n".join(lines)


def format_nodes(nodes: List[Dict]) -> str:
    """Format probe nodes list."""
    lines = []
    lines.append(f"{'区域':<6} {'省份':<8} {'城市':<10} {'运营商':<8} {'IPv4探针':<8} {'IPv6探针'}")
    lines.append("-" * 70)
    
    nodes.sort(key=lambda x: (x.get("Area.zh_CN", ""), x.get("Region.zh_CN", ""), x.get("CityName.zh_CN", "")))
    
    for n in nodes:
        area = n.get("Area.zh_CN", "-")
        region = n.get("Region.zh_CN", "-")
        city = n.get("CityName.zh_CN", "-")
        isp = n.get("IspName.zh_CN", "-")
        ipv4 = n.get("IPV4ProbeCount", 0)
        ipv6 = n.get("IPV6ProbeCount", 0)
        lines.append(f"{area:<6} {region:<8} {city:<10} {isp:<8} {ipv4:<8} {ipv6}")
    
    lines.append("-" * 70)
    lines.append(f"总计: {len(nodes)} 个节点")
    
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="网络拨测工具 - Pure HTTP replication of boce.aliyun.com",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dns --target www.example.com
  %(prog)s dns --target www.example.com --dns-server 8.8.8.8 --dns-type AAAA
  %(prog)s http --target https://www.example.com --method get
  %(prog)s ping --target 8.8.8.8 --regions 华东,华南
  %(prog)s mtr --target 8.8.8.8 --isp 电信 --max-nodes 5
  %(prog)s traceroute --target 8.8.8.8
  %(prog)s nodes --task-type dns
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Detection type")
    
    # Common arguments for all detection commands
    def add_common_args(p):
        p.add_argument("--target", "-t", required=True, help="Target domain or IP")
        p.add_argument("--regions", "-r", help="Region filter (comma-sep: 华东,华南,华北,华中,东北,西南,西北,境外)")
        p.add_argument("--isp", "-i", help="ISP filter (comma-sep: 电信,联通,移动,阿里巴巴)")
        p.add_argument("--max-nodes", "-n", type=int, default=MAX_NODES_DEFAULT, help=f"Max probe nodes (default: {MAX_NODES_DEFAULT})")
        p.add_argument("--timeout", type=int, default=30000, help="Detection timeout in ms (default: 30000)")
        p.add_argument("--json", action="store_true", help="Output raw JSON")
        p.add_argument("--refresh", action="store_true", help="Force refresh session token")
        p.add_argument("--ipv6", action="store_true", help="Use IPv6 probe nodes")
        p.add_argument("--mobile", action="store_true", help="Use mobile probe nodes instead of PC")
    
    # DNS command
    dns_parser = subparsers.add_parser("dns", help="DNS resolution detection")
    add_common_args(dns_parser)
    dns_parser.add_argument("--dns-server", "-s", default="", help="Custom DNS server (empty=operator default)")
    dns_parser.add_argument("--dns-type", "-d", default="A", choices=DNS_TYPES, help="DNS record type (default: A)")
    
    # HTTP command
    http_parser = subparsers.add_parser("http", help="HTTP(S) connectivity detection")
    add_common_args(http_parser)
    http_parser.add_argument("--method", "-m", default="get", choices=HTTP_METHODS, help="HTTP method (default: get)")
    http_parser.add_argument("--dns-server", "-s", default="", help="Custom DNS server")
    http_parser.add_argument("--verify-cert", action="store_true", help="Verify SSL certificate")
    http_parser.add_argument("--no-redirect", action="store_true", help="Don't follow redirects")
    http_parser.add_argument("--headers", default="", help="Custom HTTP headers (format: 'key1:value1\\nkey2:value2')")
    http_parser.add_argument("--cookie", default="", help="Custom cookies (format: 'key1=value1;key2=value2')")
    http_parser.add_argument("--proxy-protocol", action="store_true", help="Enable ProxyProtocol")
    
    # PING command
    ping_parser = subparsers.add_parser("ping", help="ICMP Ping latency detection")
    add_common_args(ping_parser)
    ping_parser.add_argument("--dns-server", "-s", default="", help="Custom DNS server")
    
    # MTR command
    mtr_parser = subparsers.add_parser("mtr", help="MTR route tracing")
    add_common_args(mtr_parser)
    
    # Traceroute command
    tr_parser = subparsers.add_parser("traceroute", help="Traceroute path detection")
    add_common_args(tr_parser)
    
    # Nodes command
    nodes_parser = subparsers.add_parser("nodes", help="List available probe nodes")
    nodes_parser.add_argument("--task-type", default="dns",
                             choices=list(TASK_TYPES.keys()),
                             help="Task type for node listing (default: dns)")
    nodes_parser.add_argument("--regions", "-r", help="Region filter (comma-sep)")
    nodes_parser.add_argument("--isp", "-i", help="ISP filter (comma-sep)")
    nodes_parser.add_argument("--ipv6", action="store_true", help="List IPv6 nodes")
    nodes_parser.add_argument("--json", action="store_true", help="Output raw JSON")
    nodes_parser.add_argument("--refresh", action="store_true", help="Force refresh session")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Build session
    refresh = getattr(args, "refresh", False)
    session = build_session(refresh=refresh)
    
    try:
        if args.command == "nodes":
            task_type = TASK_TYPES[args.task_type]
            nodes = get_probe_nodes(session, task_type=task_type, ipv6=getattr(args, "ipv6", False))
            
            regions = [r.strip() for r in args.regions.split(",")] if args.regions else None
            isps = [i.strip() for i in args.isp.split(",")] if args.isp else None
            
            if regions or isps:
                nodes = filter_nodes(nodes, regions=regions, isps=isps, max_nodes=99999)
            
            if args.json:
                print(json.dumps(nodes, ensure_ascii=False, indent=2))
            else:
                print(format_nodes(nodes))
            return
        
        # Detection commands
        regions = [r.strip() for r in args.regions.split(",")] if args.regions else None
        isps = [i.strip() for i in args.isp.split(",")] if args.isp else None
        
        # Get and filter nodes
        task_type = TASK_TYPES[args.command]
        all_nodes = get_probe_nodes(session, task_type=task_type, ipv6=getattr(args, "ipv6", False))
        nodes = filter_nodes(all_nodes, regions=regions, isps=isps, max_nodes=args.max_nodes)
        
        if not nodes:
            print("ERROR: 没有匹配的探测节点。请检查 --regions / --isp 参数。", file=sys.stderr)
            sys.exit(1)
        
        print(f"正在使用 {len(nodes)} 个探测节点检测 {args.target} ...", file=sys.stderr)
        
        # Determine poll timeout based on detection type
        poll_timeout = 90 if args.command in ("mtr", "traceroute") else POLL_TIMEOUT
        
        if args.command == "dns":
            agent_group = "2" if getattr(args, "mobile", False) else "1"
            results = detect_dns(
                session, args.target,
                dns_type=args.dns_type,
                dns_server=args.dns_server,
                nodes=nodes,
                agent_group=agent_group,
                timeout=args.timeout,
                poll_timeout=poll_timeout
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(format_dns_results(results))
        
        elif args.command == "http":
            agent_group = "2" if getattr(args, "mobile", False) else "1"
            results = detect_http(
                session, args.target,
                method=args.method,
                dns_server=args.dns_server,
                verify_cert=args.verify_cert,
                no_redirect=args.no_redirect,
                headers=args.headers,
                cookie=args.cookie,
                proxy_protocol=args.proxy_protocol,
                agent_group=agent_group,
                nodes=nodes,
                timeout=args.timeout,
                poll_timeout=poll_timeout
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(format_http_results(results))
        
        elif args.command == "ping":
            agent_group = "2" if getattr(args, "mobile", False) else "1"
            results = detect_ping(
                session, args.target,
                dns_server=args.dns_server,
                nodes=nodes,
                agent_group=agent_group,
                timeout=args.timeout,
                poll_timeout=poll_timeout
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(format_ping_results(results))
        
        elif args.command == "mtr":
            agent_group = "2" if getattr(args, "mobile", False) else "1"
            results = detect_mtr(
                session, args.target,
                nodes=nodes,
                agent_group=agent_group,
                timeout=args.timeout,
                poll_timeout=poll_timeout
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(format_mtr_results(results))
        
        elif args.command == "traceroute":
            agent_group = "2" if getattr(args, "mobile", False) else "1"
            results = detect_traceroute(
                session, args.target,
                nodes=nodes,
                agent_group=agent_group,
                timeout=args.timeout,
                poll_timeout=poll_timeout
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print(format_traceroute_results(results))
    
    except TokenExpiredError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print("请尝试: --refresh 参数强制刷新，或在浏览器中重新访问 boce.aliyun.com", file=sys.stderr)
        sys.exit(1)
    except TimeoutError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
