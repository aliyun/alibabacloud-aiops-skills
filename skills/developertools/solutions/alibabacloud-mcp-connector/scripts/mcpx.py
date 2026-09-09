#!/usr/bin/env python3
"""阿里云 OpenAPI 的本地命令入口。

把 alibabacloud.mcp-proxy 的 15 个工具以本地命令暴露：执行 aliyun CLI 命令、
检索 API 与官方文档、跑 Python 批量脚本、跑 Terraform 编排。
无需任何 MCP 配置。仅使用 Python 标准库，支持 macOS / Linux / Windows。
"""

import json
import os
import queue
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

IS_WINDOWS = os.name == "nt"

# POSIX 上 subprocess 没有这个常量, 用 getattr 取出以便分支逻辑可跨平台测试。
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

TOOL_PREFIX = "AlibabaCloud___"

# 钉住包版本而不用 @latest。两个原因:
#   1. @latest 会让 uv 每次重新解析 53 个包的依赖树并查询包索引, 实测每次调用
#      多花约 6 秒 (1.1s -> 7s+); 钉版本直接命中已缓存的工具环境。
#   2. @latest 使每次调用都依赖包索引可达。客户环境里包索引不通但阿里云网关
#      通是常见情况, 那会变成一个与业务无关的失败点。
# 注意: 这是 pypi 包版本, 与 serverInfo.version (远端 MCP 服务版本) 无关。
# 15 个工具由远端服务提供, 钉住本地包不会冻结工具集。
# 升级: `uvx --from pip pip index versions alibabacloud.mcp-proxy` 查新版本后改这里。
MCP_PROXY_VERSION = "0.2.17"
DEFAULT_SERVER_CMD = ["uvx", "alibabacloud.mcp-proxy@" + MCP_PROXY_VERSION]
DEFAULT_TIMEOUT = 180.0
PROTOCOL_VERSION = "2024-11-05"

EXIT_OK = 0
EXIT_TOOL_ERROR = 1
EXIT_USAGE = 2
EXIT_TRANSPORT = 3

UV_INSTALL_HINT_POSIX = "curl -LsSf https://astral.sh/uv/install.sh | sh"
UV_INSTALL_HINT_WINDOWS = (
    'powershell -ExecutionPolicy ByPass -c '
    '"irm https://astral.sh/uv/install.ps1 | iex"'
)
ALIYUN_INSTALL_HINT_POSIX = (
    '/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 '
    'https://aliyuncli.alicdn.com/setup.sh)"'
)
ALIYUN_INSTALL_HINT_WINDOWS = (
    'Invoke-WebRequest -Uri '
    '"https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" '
    '-OutFile "aliyun-cli.zip"; '
    'Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\\aliyun-cli'
)


def uv_install_hint():
    return UV_INSTALL_HINT_WINDOWS if IS_WINDOWS else UV_INSTALL_HINT_POSIX


def aliyun_install_hint():
    return ALIYUN_INSTALL_HINT_WINDOWS if IS_WINDOWS else ALIYUN_INSTALL_HINT_POSIX


USAGE = """用法: mcpx.py <子命令> [参数]

子命令:
  doctor                        前置自检: 依赖 / 凭证 / 连通性 / 身份
  login [--profile P] [--region R] [--site S]
                                自动应答 aliyun OAuth 登录的终端提示
                                不带 --profile 时覆盖当前活跃 profile
  list                          列出全部工具
  schema <TOOL>                 打印某工具的入参 schema
  call <TOOL> [JSON|-]          调用工具; '-' 表示从 stdin 读 JSON; 省略等价于 {}

通用参数:
  --timeout SECONDS             默认 180

退出码: 0 成功 / 1 工具返回 isError / 2 用法错误 / 3 传输层或前置条件失败
"""


class McpxError(Exception):
    def __init__(self, message, exit_code=EXIT_TRANSPORT):
        super().__init__(message)
        self.exit_code = exit_code


def server_command():
    """启动 MCP server 的命令。MCPX_SERVER_CMD 仅供测试注入。"""
    override = os.environ.get("MCPX_SERVER_CMD")
    if override:
        return shlex.split(override, posix=not IS_WINDOWS)
    return list(DEFAULT_SERVER_CMD)


def is_test_injection():
    return bool(os.environ.get("MCPX_SERVER_CMD"))


# proxy 0.2.17 默认用 streamable 传输连上游 .../mcp, 而上游对该端点的 GET 流
# 返回 405, 打包的 mcp SDK 会陷入无限重连, 导致 tools/list、tools/call 永不
# 返回(Windows 必现, macOS 偶尔侥幸送达)。不改 proxy 包的唯一出路: 用 proxy
# 自带的 --server-url 指到同一 COREID 的 .../sse 端点(实测两平台都正常)。
# 发现 URL 也只用 proxy 自带的 --debug --log-file, 从日志里读它自己发现的地址。
SSE_URL_MARKER = "Discovered MCP server URL:"
SERVER_URL_CACHE = os.path.join(
    os.path.expanduser("~"), ".mcpx", "server-url.json")
DISCOVERY_TIMEOUT_CAP = 90.0


def mcp_url_to_sse(url):
    """把发现到的上游 URL 结尾 /mcp 改写成 /sse；两者共享同一 /id/<COREID>/ 基座。

    容忍 query string：先分离 `?` 之后部分，只改写路径结尾，再拼回，避免
    `.../mcp?x=y` 被漏判成「非预期形态」而静默回退到坏的 streamable。
    """
    u = (url or "").strip()
    if not u:
        return None
    path_part, sep, query = u.partition("?")
    path_part = path_part.rstrip("/")
    tail = sep + query if sep else ""
    if path_part.endswith("/sse"):
        return path_part + tail
    if path_part.endswith("/mcp"):
        return path_part[:-len("/mcp")] + "/sse" + tail
    return None  # 非预期形态，不猜


def parse_discovered_url(log_text):
    """从 proxy 的 debug 日志里取最后一条 `Discovered MCP server URL: <url>`。"""
    found = None
    for line in (log_text or "").splitlines():
        idx = line.find(SSE_URL_MARKER)
        if idx < 0:
            continue
        rest = line[idx + len(SSE_URL_MARKER):].strip().split()
        if rest and rest[0].startswith("http"):
            found = rest[0]
    return found


def read_cached_server_url():
    try:
        with open(SERVER_URL_CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    url = data.get("sse_url") if isinstance(data, dict) else None
    if not (isinstance(url, str) and url.startswith("http")):
        return None
    # 身份变了(切 profile/账号)则缓存作废: 旧 COREID 配新账号 token 会被上游拒,
    # 反而产生误导性的权限报错。下次调用重新发现即可。
    if data.get("profile") != current_profile_name():
        return None
    return url


def write_cached_server_url(url):
    """缓存端点 URL(含账号级 COREID)与当时的 profile, 不是凭证; 0600 落盘, 原子替换。"""
    d = os.path.dirname(SERVER_URL_CACHE)
    tmp = None
    try:
        os.makedirs(d, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".server-url-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"sse_url": url, "profile": current_profile_name()}, fh)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, SERVER_URL_CACHE)  # 原子替换, 避免并发写半截
        tmp = None
    except OSError:
        pass  # 缓存写不进不影响主流程，下次重新发现即可
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except OSError:
                pass


def invalidate_cached_server_url():
    try:
        os.remove(SERVER_URL_CACHE)
    except OSError:
        pass


def discover_server_url(timeout):
    """拉起 proxy 的发现流程, 从 debug 日志读出上游 URL 并改写成 /sse。

    只读到 URL 就立刻回收该发现进程, 不等它连接上游(连接阶段正是要绕开的
    405 死循环)。读不到(无凭证/无权限/超时)返回 None, 由调用方回退默认命令,
    从而保留 _startup_failure 既有的凭证/权限报错。
    """
    fd, logpath = tempfile.mkstemp(prefix="mcpx-discover-", suffix=".log")
    os.close(fd)
    proc = None
    try:
        cmd = list(DEFAULT_SERVER_CMD) + ["proxy", "--debug", "--log-file", logpath]
        try:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                text=False, **spawn_kwargs())
        except OSError:
            return None
        # 喂一个 initialize 促使它走完启动发现(代理启动即发现, 喂一下更稳妥)。
        try:
            payload = (json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                           "clientInfo": {"name": "mcpx-discover", "version": "1.0"}},
            }) + "\n").encode("utf-8")
            proc.stdin.write(payload)
            proc.stdin.flush()
        except (OSError, ValueError):
            pass

        deadline = time.time() + timeout
        url = None
        while True:
            try:
                with open(logpath, encoding="utf-8", errors="replace") as fh:
                    url = parse_discovered_url(fh.read())
            except OSError:
                url = None
            if url:
                break
            if proc.poll() is not None or time.time() >= deadline:
                break
            time.sleep(0.3)
        return mcp_url_to_sse(url) if url else None
    finally:
        if proc is not None:
            kill_tree(proc, force=True)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        try:
            os.remove(logpath)
        except OSError:
            pass


def resolve_server_url(timeout):
    """返回 (sse_url 或 None, 是否来自缓存)。拿不到则上层回退默认 streamable 命令。"""
    cached = read_cached_server_url()
    if cached:
        return cached, True
    url = discover_server_url(min(timeout, DISCOVERY_TIMEOUT_CAP))
    if url:
        write_cached_server_url(url)
        return url, False
    return None, False


def spawn_kwargs():
    """让子进程自成一组, 便于整组回收。POSIX 与 Windows 机制不同。"""
    if IS_WINDOWS:
        return {"creationflags": CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def kill_tree(proc, force):
    """回收子进程及其后代。

    POSIX: 子进程自成进程组, 整组发信号。
    Windows: 没有进程组信号语义, 用 taskkill /T 递归杀树。
    """
    if proc is None or proc.poll() is not None:
        return
    if IS_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True, timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            try:
                proc.kill()
            except OSError:
                pass
        return
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill() if force else proc.terminate()
        except OSError:
            pass


_EOF = object()


class ChunkReader:
    """后台线程把子进程输出读成分块放入队列。

    不用 select: Windows 上 select 只支持 socket, 不支持管道。
    分块而非按行读: 交互提示 (如 'Default Region Id []: ') 结尾没有换行,
    按行读会一直阻塞。
    """

    def __init__(self, fileno):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, args=(fileno,), daemon=True)
        self._thread.start()

    def _run(self, fileno):
        try:
            while True:
                chunk = os.read(fileno, 65536)
                if not chunk:
                    break
                self._queue.put(chunk)
        except (OSError, ValueError):
            pass
        finally:
            self._queue.put(_EOF)

    def read(self, timeout):
        """返回 bytes / _EOF / None(超时)。"""
        try:
            return self._queue.get(timeout=max(timeout, 0.0))
        except queue.Empty:
            return None


RAM_PERMISSION = "AliyunOpenAPIMCPServerStaticCredentialAccess"

RAM_PERMISSION_HINT = (
    "常见原因: 该账号缺少 `%s` RAM 权限。\n"
    "MCP 服务需要这个权限点才能为调用方签发凭证 —— **`aliyun` CLI 登录成功不代表\n"
    "拥有这个权限**, 两者是分开的。这也是「已登录却连不上」最典型的成因。\n"
    "处置: 为当前登录账号申请或添加该 RAM 权限点, 然后重跑 `doctor`。\n"
    "确认当前是哪个身份: aliyun sts get-caller-identity" % RAM_PERMISSION
)

OAUTH_APP = "official-cli"
OAUTH_APP_ID = "4038181954557748008"
# 安装入口: 主账号/RAM 管理员从这里安装「官方 CLI」三方应用
OAUTH_APP_INSTALL_URL = "https://ram.console.aliyun.com/applications?activeTab=ThirdParty"
# 安装时要选中的官方 CLI 应用身份
OAUTH_APP_IDENTITY = "alibabacloud-cli@app.1263926834388048.onaliyun.com"
# 分配入口: 把已安装的应用授权给当前子账号/角色 (即加入访问者列表)
OAUTH_APP_ASSIGN_URL = (
    "https://ram.console.aliyun.com/applications/%s"
    "?appType=ThirdPartyApp&activeTab=Assignments" % OAUTH_APP_ID
)

# 子账号未被分配该应用时, 报错只出现在**授权页面**上, 终端不会收到任何错误
# —— 用户根本点不到「授权」, 回调永远不来, 所以 mcpx 这边的表现就是等到超时。
# 页面原文:
#   账号未允许当前身份访问该应用。
#   将以下信息发送给 RAM 访问控制管理员, 请管理员将当前访问身份添加至
#   应用的访问者列表中。
#   访问身份 <子账号>@<主账号UID>.onaliyun.com
#   应用管理地址 https://ram.console.aliyun.com/applications/<appId>?appType=ThirdPartyApp
# 页面给的 appId 与授权链接里的 client_id 是同一个, 即 OAUTH_APP_ID。
# 下面 A/B 两种情况的控制台路径用于让用户失败时不迷茫: A 安装应用, B 分配给子账号。
OAUTH_APP_HINT = (
    "若授权页面显示「账号未允许当前身份访问该应用」, 那不是网络慢, 是 `%s` 这个\n"
    "OAuth 三方应用没就位 —— 点不到授权按钮, 回调不会来, 这边只能等到超时。\n"
    "先问清是下面哪种情况; 两步都得主账号/RAM 管理员做, 子账号自己做不了:\n"
    "\n"
    "A. 主账号从没装过该应用 -> 管理员先安装:\n"
    "   1) 打开 %s\n"
    "   2) 点「安装官方应用」->「官方 CLI」\n"
    "   3) 选 %s\n"
    "B. 已装但当前子账号不在访问者列表里 -> 管理员分配:\n"
    "   1) 打开 %s\n"
    "   2) 点「添加用户或角色」\n"
    "   3) 选当前这个子账号用户\n"
    "管理员做完后刷新授权页或重跑 login。\n"
    "这与 MCP 的 RAM 权限是两道独立门槛: 这一道决定能不能登录, `%s`\n"
    "决定登录后能不能连上 MCP。"
    % (OAUTH_APP, OAUTH_APP_INSTALL_URL, OAUTH_APP_IDENTITY,
       OAUTH_APP_ASSIGN_URL, RAM_PERMISSION)
)

# 缺 RAM 权限的子账号会收到的服务端报错:
#   Error: Failed to discover MCP server URL: code: 403,
#   You are not authorized to perform this action. request id: ...
PERMISSION_DENIED_PHRASE = "You are not authorized to perform this action"

# 其余权限类特征词, 用于覆盖措辞变化。命中任一即判为权限被拒;
# 全部落空时「未知失败」兜底分支也会附上同一条提示。
_PERMISSION_MARKERS = (
    PERMISSION_DENIED_PHRASE,
    "Forbidden", "NoPermission", "AccessDenied", "not authorized",
    "Unauthorized", "InvalidAccessKeyId.Inactive", "403",
)


_NOISE_PREFIXES = (
    "Installed ",
    "Downloading ",
    "Downloaded ",
    "Resolved ",
    "Building ",
    "Built ",
    "Uninstalled ",
)


def _is_noise(line):
    stripped = line.strip()
    if not stripped:
        return True
    return stripped.startswith(_NOISE_PREFIXES)


class McpSession:
    """一次调用一个进程的 MCP stdio 会话。

    stdin 必须是 PIPE —— 这是本进程被强杀 (POSIX SIGKILL / Windows 强制终止)
    时唯一的孤儿进程保护: 本进程一死, 管道写端关闭, 子进程读到 EOF 自行退出。
    改成继承或 DEVNULL 会让该保护失效。
    """

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = float(timeout)
        self.proc = None
        self._next_id = 0
        self._stderr_chunks = []
        self._stderr_thread = None
        self._reader = None
        self._buffer = ""
        self._logpath = None
        self._used_cached_url = False
        self.server_url = None
        self._got_response = False
        self._skipped_lines = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def start(self):
        base = server_command()
        if shutil.which(base[0]) is None:
            raise McpxError(
                "找不到可执行文件 %r。\n"
                "本 SKILL 需要 uv/uvx。安装方式:\n  %s" % (base[0], uv_install_hint())
            )
        cmd = self._build_server_command(base)
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                **spawn_kwargs()
            )
        except OSError as exc:
            self._remove_log()  # _build_server_command 可能已建临时日志, 异常路径也要清
            raise McpxError("启动 MCP server 失败: %s" % exc)

        self._reader = ChunkReader(self.proc.stdout.fileno())

        def drain(stream, sink):
            try:
                for chunk in iter(stream.readline, b""):
                    sink.append(chunk.decode("utf-8", "replace"))
            except (ValueError, OSError):
                pass

        self._stderr_thread = threading.Thread(
            target=drain, args=(self.proc.stderr, self._stderr_chunks), daemon=True
        )
        self._stderr_thread.start()

    def _build_server_command(self, base):
        """真实路径强制 SSE 传输；测试注入(MCPX_SERVER_CMD)原样不动。

        只用 proxy 自带的 --server-url / --debug / --log-file 参数, 不改 proxy 代码。
        发现不到 SSE URL(如无凭证)时回退默认命令, 让 _startup_failure 报凭证/权限。
        """
        if is_test_injection():
            return base
        sse_url, from_cache = resolve_server_url(self.timeout)
        self._used_cached_url = from_cache
        if not sse_url:
            return base
        self.server_url = sse_url
        fd, self._logpath = tempfile.mkstemp(prefix="mcpx-proxy-", suffix=".log")
        os.close(fd)
        return base + ["proxy", "--server-url", sse_url,
                       "--debug", "--log-file", self._logpath]

    def child_stderr(self, include_noise=False):
        lines = "".join(self._stderr_chunks).splitlines()
        if not include_noise:
            lines = [ln for ln in lines if not _is_noise(ln)]
        return "\n".join(lines).strip()

    def _send(self, obj):
        payload = (json.dumps(obj) + "\n").encode("utf-8")
        try:
            self.proc.stdin.write(payload)
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            raise self._startup_failure()

    def _startup_failure(self):
        if self._used_cached_url:
            invalidate_cached_server_url()  # 缓存的 URL 可能已失效，下次重新发现
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=2)
        detail = self.child_stderr()
        blob = self.child_stderr(include_noise=True)
        # 真实路径用 --log-file 拉起代理, 其日志(含致命错误)写进文件而非 stderr
        # (实测 stderr 此时为空)。凭证/权限标记可能在任一处, 两处都扫; 展示给
        # 用户的 detail 在 stderr 为空时回退到日志尾部。测试注入路径无 _logpath,
        # _log_full 返回空, 行为与原先逐字一致。
        logtext = self._log_full()
        if logtext:
            # 只并入末尾若干行: 致命错误总在日志尾部, 而 _PERMISSION_MARKERS 含裸
            # "403", 并入整份冗长 debug 日志会放大无关 403 的误判面。
            bounded = "\n".join(logtext.splitlines()[-120:])
            blob = blob + "\n" + bounded
            if not detail:
                detail = self._log_tail()
        if "Specified access key is not found" in blob:
            raise_msg = (
                "阿里云凭证无效, MCP 服务在握手前已退出。\n"
                "服务端原始信息:\n%s\n\n"
                "请重新登录: mcpx.py login --region cn-hangzhou" % detail
            )
            return McpxError(raise_msg)
        if "100.100.100.200" in blob:
            return McpxError(
                "未检测到可用的阿里云凭证 (已回退到 ECS 元数据服务并超时, "
                "说明当前不在 ECS 上)。\n"
                "请先登录: mcpx.py login --region cn-hangzhou"
            )
        if any(marker in blob for marker in _PERMISSION_MARKERS):
            return McpxError(
                "凭证可用但被拒绝, MCP 服务在握手前已退出。\n"
                "服务端原始信息:\n%s\n\n%s" % (detail, RAM_PERMISSION_HINT)
            )
        return McpxError(
            "MCP 服务未响应即退出。服务端原始信息:\n%s\n\n%s"
            % (detail or "(无 stderr 输出)", RAM_PERMISSION_HINT)
        )

    def _read_message(self, deadline):
        while True:
            if "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                if line.strip():
                    try:
                        msg = json.loads(line)
                    except ValueError:
                        # 非 JSON 行(代理偶发把杂讯写到 stdout): 跳过并记录, 不崩会话
                        if len(self._skipped_lines) < 20:
                            self._skipped_lines.append(line.strip()[:200])
                        continue
                    self._got_response = True
                    return msg
                continue
            remaining = deadline - time.time()
            if remaining <= 0:
                raise self._timeout_error()
            chunk = self._reader.read(min(remaining, 0.5))
            if chunk is None:
                if self.proc.poll() is not None and not self._buffer:
                    raise self._startup_failure()
                continue
            if chunk is _EOF:
                raise self._startup_failure()
            self._buffer += chunk.decode("utf-8", "replace")

    def _timeout_error(self):
        if self._used_cached_url:
            invalidate_cached_server_url()  # 缓存 URL 可能失效，下次重新发现
        parts = ["等待 MCP 服务响应超时 (%.0fs)。" % self.timeout]
        if not self._got_response:
            parts.append(
                "尚未读到任何响应：代理可能仍在解析依赖或发现上游 URL。"
                "首次运行可加大超时, 例如 mcpx --timeout 600 <子命令>。")
        elif self.server_url:
            parts.append(
                "已连上游但后续响应未回。本次已强制走 SSE 端点\n  %s\n"
                "以规避 streamable 的 GET 405 重连死循环; 若仍卡住, 见下方诊断。"
                % self.server_url)
        elif is_test_injection():
            parts.append("已连服务但后续响应未回。")
        else:
            parts.append(
                "已连上游但后续响应未回, 且本次**未能发现/强制 SSE 端点** —— 可能仍在走\n"
                "默认 streamable 传输(上游对 GET /mcp 返回 405, SDK 无限重连, 工具调用永不返回)。\n"
                "手动指定 SSE 端点可绕过(把 <COREID> 换成你的发现值):\n"
                "  export ALIBABACLOUD_MCP_SERVER_URL="
                "\"https://openapi-mcp.<region>.aliyuncs.com/id/<COREID>/sse\"")
        detail = self.child_stderr()
        if detail:
            parts.append("子进程 stderr:\n" + detail)
        if self._skipped_lines:
            parts.append("stdout 上跳过的非 JSON 行:\n" + "\n".join(self._skipped_lines))
        tail = self._log_tail()
        if tail:
            parts.append("代理日志尾部 (--log-file):\n" + tail)
        return McpxError("\n".join(parts))

    def _log_full(self):
        if not self._logpath:
            return ""
        try:
            with open(self._logpath, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def _log_tail(self, n=40):
        lines = self._log_full().splitlines()
        keep = [ln for ln in lines[-n:] if not _is_noise(ln)]
        return "\n".join(keep).strip()

    def request(self, method, params=None):
        self._next_id += 1
        mid = self._next_id
        self._send({"jsonrpc": "2.0", "id": mid, "method": method,
                    "params": params or {}})
        deadline = time.time() + self.timeout
        while True:
            msg = self._read_message(deadline)
            if msg.get("id") != mid:
                continue
            if "error" in msg:
                err = msg["error"]
                raise McpxError("MCP 服务返回错误 %s: %s"
                                % (err.get("code"), err.get("message")))
            return msg.get("result", {})

    def initialize(self):
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcpx", "version": "1.0"},
        })
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def list_tools(self):
        return self.request("tools/list").get("tools", [])

    def call_tool(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        if self.proc is not None:
            try:
                if self.proc.stdin and not self.proc.stdin.closed:
                    self.proc.stdin.close()
            except OSError:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                kill_tree(self.proc, force=False)
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    kill_tree(self.proc, force=True)
                    try:
                        self.proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
            for stream in (self.proc.stdout, self.proc.stderr):
                try:
                    if stream:
                        stream.close()
                except OSError:
                    pass
        self._remove_log()

    def _remove_log(self):
        if self._logpath:
            try:
                os.remove(self._logpath)
            except OSError:
                pass
            self._logpath = None


def normalize_tool_name(raw):
    if raw.startswith(TOOL_PREFIX):
        return raw
    return TOOL_PREFIX + raw


def short_name(full):
    if full.startswith(TOOL_PREFIX):
        return full[len(TOOL_PREFIX):]
    return full


def first_sentence(text):
    line = (text or "").strip().split("\n", 1)[0].strip()
    if "." in line:
        return line[: line.index(".") + 1]
    return line


def parse_common(args):
    """抽出 --timeout, 返回 (timeout, 剩余位置参数)。"""
    timeout = DEFAULT_TIMEOUT
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--timeout":
            if i + 1 >= len(args):
                raise McpxError("--timeout 缺少值", EXIT_USAGE)
            try:
                timeout = float(args[i + 1])
            except ValueError:
                raise McpxError("--timeout 的值不是数字: %s" % args[i + 1],
                                EXIT_USAGE)
            i += 2
            continue
        rest.append(args[i])
        i += 1
    return timeout, rest


def find_tool(tools, wanted_full):
    for tool in tools:
        if tool["name"] == wanted_full:
            return tool
    names = ", ".join(sorted(short_name(t["name"]) for t in tools))
    raise McpxError(
        "未知工具: %s\n服务端当前提供的工具: %s" % (short_name(wanted_full), names),
        EXIT_USAGE,
    )


def cmd_list(args):
    timeout, rest = parse_common(args)
    if rest:
        raise McpxError("list 不接受位置参数: %s" % " ".join(rest), EXIT_USAGE)
    with McpSession(timeout=timeout) as session:
        session.initialize()
        tools = session.list_tools()
    for tool in tools:
        sys.stdout.write("%s\t%s\n"
                         % (short_name(tool["name"]),
                            first_sentence(tool.get("description"))))
    return EXIT_OK


def cmd_schema(args):
    timeout, rest = parse_common(args)
    if len(rest) != 1:
        raise McpxError("用法: schema <TOOL>", EXIT_USAGE)
    wanted = normalize_tool_name(rest[0])
    with McpSession(timeout=timeout) as session:
        session.initialize()
        tools = session.list_tools()
    tool = find_tool(tools, wanted)
    sys.stdout.write(json.dumps(tool.get("inputSchema", {}),
                                indent=2, ensure_ascii=False) + "\n")
    return EXIT_OK


def split_content(result):
    """返回 (拼接后的 text, 非 text 块列表)。"""
    texts = []
    others = []
    for block in result.get("content", []) or []:
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
        else:
            others.append(block)
    return "\n".join(texts), others


def load_arguments(raw):
    if raw is None:
        return {}
    if raw == "-":
        raw = sys.stdin.read()
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise McpxError(
            "入参 JSON 解析失败: %s\n"
            "提示: 参数里含双引号时, 改用 '-' 从 stdin 传入可免转义, 例如\n"
            "  echo '{\"command\":\"...\"}' | mcpx.py call CallCLI -" % exc,
            EXIT_USAGE,
        )
    if not isinstance(parsed, dict):
        raise McpxError("入参必须是 JSON 对象, 实际是 %s"
                        % type(parsed).__name__, EXIT_USAGE)
    return parsed


EMPTY_FILTER_RESULTS = ("null", "[]", "{}", '""')


def warn_if_filter_yielded_nothing(tool_short_name, arguments, text):
    """jmespath 路径写错时返回 null 且不报错, 与「真的没数据」无法区分。

    这是静默的数据正确性陷阱: 曾有人据此误判某产品无地域数据, 转而借用另一个
    产品的地域列表, 导致 7 个地域从未被扫描却对外宣称覆盖完整。
    因此只要用了 filter 且结果为空, 就必须提醒复核。
    """
    if not arguments.get("x_output_jmespath_filter"):
        return
    if text.strip() not in EMPTY_FILTER_RESULTS:
        return
    bare = {k: v for k, v in arguments.items()
            if k != "x_output_jmespath_filter"}
    sys.stderr.write(
        "警告: 带 x_output_jmespath_filter 的调用返回了 %s。\n"
        "jmespath 路径写错会静默返回 null, 与「真的没有数据」无法区分。\n"
        "下结论前先去掉 filter 裸调一次, 确认响应的真实结构:\n"
        "  mcpx call %s '%s'\n"
        % (text.strip(), tool_short_name,
           json.dumps(bare, ensure_ascii=False))
    )


def cmd_call(args):
    timeout, rest = parse_common(args)
    if not rest or len(rest) > 2:
        raise McpxError("用法: call <TOOL> [JSON|-]", EXIT_USAGE)
    wanted = normalize_tool_name(rest[0])
    arguments = load_arguments(rest[1] if len(rest) == 2 else None)

    with McpSession(timeout=timeout) as session:
        session.initialize()
        result = session.call_tool(wanted, arguments)

    text, others = split_content(result)
    for block in others:
        sys.stderr.write("非 text 类型 content 块: %s\n"
                         % json.dumps(block, ensure_ascii=False))
    if result.get("isError"):
        sys.stderr.write(text + "\n" if text else "工具返回 isError 但无正文\n")
        return EXIT_TOOL_ERROR
    warn_if_filter_yielded_nothing(short_name(wanted), arguments, text)
    if text:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return EXIT_OK


SKILL_NAME = "alibabacloud-mcp-connector"


def identity_command():
    session_id = os.environ["SKILL_SESSION_ID"]
    skill_version = os.environ["SKILL_VERSION"]
    user_agent = (
        "AlibabaCloud-Agent-Skills/%s/%s skill-version/%s"
        % (SKILL_NAME, session_id, skill_version)
    )
    return 'aliyun sts get-caller-identity --user-agent "%s"' % user_agent


def aliyun_version():
    """返回 (路径, 版本字符串) 或 (None, None)。"""
    path = shutil.which("aliyun")
    if path is None:
        return None, None
    try:
        proc = subprocess.run([path, "version"], capture_output=True,
                              text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return path, None
    return path, (proc.stdout or proc.stderr).strip().split("\n")[0].strip()


def credential_config_path():
    return os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")


# 凭证链优先级是 env > config.json > ECS 元数据: env 里只要有 ALIBABA_CLOUD_*
# 就会遮蔽配置文件里的凭证。若 env 中的那套并不完整(典型: 声明了 STS 身份却没有
# token), proxy 仍会拿它签名, 网关拒签 —— 而配置文件里那套有效凭证根本没被用到。
# 症状: 网关回显的 CanonicalRequest 里没有 x-acs-security-token 头。
# 这里只报「是否为空」, 绝不打印凭证值。


def env_credential_warning():
    """env 凭证不完整时返回告警文本; 无异常返回 None。"""
    ak = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    sk = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    if not (ak and sk):
        return None
    token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
    # STS 凭证缺 token 必然验签失败, 与具体环境无关。
    if token is None or token.strip():
        return None
    lines = ["    !! 环境变量凭证不完整: ALIBABA_CLOUD_SECURITY_TOKEN 已设置但为空"]
    lines.append("       (STS 凭证缺 token 必然验签失败)")
    lines.append("       环境变量优先级高于 %s, 会把它盖掉。"
                 % credential_config_path())
    if os.path.exists(credential_config_path()):
        lines.append("       该文件存在: 其中可能有一套有效凭证正被这些 env 变量遮蔽。")
    lines.append("       处置: unset ALIBABA_CLOUD_ACCESS_KEY_ID "
                 "ALIBABA_CLOUD_ACCESS_KEY_SECRET ALIBABA_CLOUD_SECURITY_TOKEN")
    lines.append("       (让凭证链回落到配置文件), 或改为有效值; 然后重跑 doctor。")
    return "\n".join(lines) + "\n"


def current_profile_name():
    """读 aliyun 的当前活跃 profile 名, 读不到返回 None。

    `aliyun configure` 不带 --profile 时配置的是**当前活跃 profile**, 不是
    'default' —— 实测依据: 一次不带 --profile 的 OAuth 登录改写了 current
    所指的 profile, 而 'default' 的 token/ak/sts 全部未变。
    login 据此在执行前声明将覆盖哪个 profile。
    """
    path = credential_config_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    name = data.get("current")
    return name or None


def cmd_doctor(args):
    timeout, rest = parse_common(args)
    if rest:
        raise McpxError("doctor 不接受位置参数: %s" % " ".join(rest), EXIT_USAGE)

    out = sys.stdout
    cmd = server_command()
    out.write("[0] 平台: %s\n" % ("Windows" if IS_WINDOWS else sys.platform))
    out.write("[1] MCP server 命令: %s\n" % " ".join(cmd))
    resolved = shutil.which(cmd[0])
    if resolved is None:
        raise McpxError("找不到 %r。安装 uv:\n  %s" % (cmd[0], uv_install_hint()))
    out.write("    可执行文件: %s\n" % resolved)

    out.write("[2] Python 运行时: %s\n" % sys.version.split()[0])

    out.write("[3] 凭证来源:\n")
    has_ak = bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"))
    has_sk = bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET"))
    out.write("    环境变量 AK/SK: %s\n"
              % ("已设置" if (has_ak and has_sk) else "未设置"))
    warning = env_credential_warning()
    if warning:
        out.write(warning)
    out.write("    注意: 这里检测的是本进程继承自 agent 的环境, "
              "不是你终端里的环境 —— 在别的终端 export 过, 本进程读不到。\n"
              "          凭证链优先级: 环境变量 > %s > ECS 元数据服务;\n"
              "          环境变量一旦存在就会盖过配置文件。\n"
              % credential_config_path())
    config = credential_config_path()
    has_config = os.path.exists(config)
    out.write("    %s: %s\n" % (config, "存在" if has_config else "不存在"))
    apath, aver = aliyun_version()
    if apath is None:
        out.write("    aliyun CLI: 未安装\n"
                  "      工具调用本身不需要它 (调用在远端执行), 但 `login` 硬依赖它。\n"
                  "      当前没有可用凭证, 因此顺序是: 先装 CLI -> 再 login -> 再 doctor。\n"
                  "      安装: %s\n" % aliyun_install_hint())
    else:
        out.write("    aliyun CLI: %s (%s), 需 >= 3.3.3\n"
                  % (apath, aver or "版本未知"))
    if not (has_ak and has_sk) and not has_config:
        out.write("    未发现显式凭证, 将回退到 ECS 元数据服务 (仅在 ECS 上可用)。\n")
    else:
        out.write("    注意: 有凭证 != 有权限。MCP 服务还要求账号具备 `%s`\n"
                  "          RAM 权限点, 否则下一步握手会被拒。\n" % RAM_PERMISSION)
    out.flush()

    command = identity_command()
    with McpSession(timeout=timeout) as session:
        info = session.initialize()
        out.write("[4] 握手: 成功, serverInfo=%s\n"
                  % json.dumps(info.get("serverInfo", {}), ensure_ascii=False))
        out.flush()
        result = session.call_tool(
            normalize_tool_name("CallCLI"), {"command": command}
        )

    text, _ = split_content(result)
    if result.get("isError"):
        raise McpxError("身份确认失败 (%s):\n%s" % (command, text))
    out.write("[5] 身份 (%s):\n%s\n" % (command, text))
    out.write("\n全部检查通过, 可以开始调用工具。\n")
    return EXIT_OK


AUTH_URL_MARKERS = (
    "https://signin.aliyun.com/oauth2/",
    "https://signin.alibabacloud.com/oauth2/",
)

# 提示标记 -> 应答键。顺序即实测的真实提示顺序。
LOGIN_PROMPTS = (
    ("OAuth Site Type", "site"),
    ("Default Region Id", "region"),
    ("Default Output Format", "output"),
    ("Default Language", "language"),
)


def _extract_auth_url(buffer):
    for marker in AUTH_URL_MARKERS:
        index = buffer.find(marker)
        if index < 0:
            continue
        tail = buffer[index:]
        for stop in ("\r", "\n", " "):
            cut = tail.find(stop)
            if cut >= 0:
                tail = tail[:cut]
        if tail:
            return tail
    return None


def _reap(proc):
    kill_tree(proc, force=False)
    try:
        proc.wait(timeout=3)
        return
    except subprocess.TimeoutExpired:
        pass
    kill_tree(proc, force=True)
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass


def parse_login_args(args):
    timeout = DEFAULT_TIMEOUT
    region = "cn-hangzhou"
    site = "cn"
    profile = None
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--timeout":
            if i + 1 >= len(args):
                raise McpxError("--timeout 缺少值", EXIT_USAGE)
            try:
                timeout = float(args[i + 1])
            except ValueError:
                raise McpxError("--timeout 的值不是数字: %s" % args[i + 1],
                                EXIT_USAGE)
            i += 2
        elif token == "--region":
            if i + 1 >= len(args):
                raise McpxError("--region 缺少值", EXIT_USAGE)
            region = args[i + 1]
            i += 2
        elif token == "--profile":
            if i + 1 >= len(args):
                raise McpxError("--profile 缺少值", EXIT_USAGE)
            profile = args[i + 1]
            i += 2
        elif token == "--site":
            if i + 1 >= len(args):
                raise McpxError("--site 缺少值", EXIT_USAGE)
            site = args[i + 1].lower()
            if site not in ("cn", "intl"):
                raise McpxError("--site 只能是 cn 或 intl", EXIT_USAGE)
            i += 2
        elif token == "--mode":
            raise McpxError(
                "login 只支持 OAuth 模式, 不接受 --mode。\n"
                "AK 模式要求在终端输入长期密钥, 不应让密钥经过本脚本。\n"
                "需要 AK 模式请自行在终端执行:\n"
                "  aliyun configure --mode AK",
                EXIT_USAGE,
            )
        else:
            raise McpxError("login 不认识的参数: %s" % token, EXIT_USAGE)
    return timeout, region, site, profile


def cmd_login(args):
    timeout, region, site, profile = parse_login_args(args)

    aliyun_exe = shutil.which("aliyun")
    if aliyun_exe is None:
        raise McpxError(
            "找不到 aliyun CLI, 无法配置凭证。安装命令:\n  %s\n"
            "安装后用 `aliyun version` 确认 >= 3.3.3。" % aliyun_install_hint()
        )

    # 执行前声明目标 profile。不带 --profile 时 aliyun 配置的是当前活跃
    # profile, 会覆盖其现有凭证 —— 这一点必须让用户先知道。
    target = profile or current_profile_name()
    if target:
        sys.stdout.write(
            "即将配置 aliyun profile: %s\n"
            "该 profile 的现有凭证将被覆盖。要写入其他 profile 请用 "
            "--profile NAME。\n" % target
        )
    else:
        sys.stdout.write(
            "未检测到已有 aliyun 配置, 将新建 profile。\n"
        )
    sys.stdout.flush()

    answers = {
        "site": "1\n" if site == "intl" else "\n",
        "region": region + "\n",
        "output": "\n",
        "language": "\n",
    }

    cmd = [aliyun_exe, "configure", "--mode", "OAuth"]
    if profile:
        cmd += ["--profile", profile]

    # 用管道而非 pty: OAuth 模式的提示全是普通读取, 实测管道输入生效
    # (喂 0 得到 signin.aliyun.com, 喂 1 得到 signin.alibabacloud.com)。
    # 这样 Windows 上同样可用 —— Windows 没有 pty。
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **spawn_kwargs()
    )
    reader = ChunkReader(proc.stdout.fileno())

    buffer = ""
    answered = set()
    url_printed = False
    deadline = time.time() + timeout
    try:
        while True:
            if proc.poll() is not None:
                break
            remaining = deadline - time.time()
            if remaining <= 0:
                _reap(proc)
                raise McpxError(
                    "授权未在时限内完成 (%.0fs)。\n"
                    "请确认已在浏览器中打开授权链接并点击授权, 然后重试。\n"
                    "可用 --timeout 加大等待时间。\n\n%s" % (timeout, OAUTH_APP_HINT)
                )
            chunk = reader.read(min(remaining, 0.5))
            if chunk is None:
                continue
            if chunk is _EOF:
                break
            buffer += chunk.decode("utf-8", "replace")

            if not url_printed:
                url = _extract_auth_url(buffer)
                if url:
                    sys.stdout.write(
                        "请在浏览器中打开以下链接完成授权:\n%s\n" % url
                    )
                    sys.stdout.flush()
                    url_printed = True

            for marker, key in LOGIN_PROMPTS:
                if key in answered:
                    continue
                if marker in buffer:
                    try:
                        proc.stdin.write(answers[key].encode("utf-8"))
                        proc.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError):
                        pass
                    answered.add(key)
                    break
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _reap(proc)
    finally:
        # 无论怎么退出都必须回收子进程, 包括本进程收到 SIGINT/SIGTERM 时。
        # aliyun configure 在等浏览器回调时阻塞在 HTTP 上, 不会回到读 stdin,
        # 所以 stdin EOF 那条保护对它无效 —— 实测泄漏过一个仍占着回调端口
        # 12345 的孤儿, 导致下一次 login 直接失败。
        if proc.poll() is None:
            _reap(proc)
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream and not stream.closed:
                    stream.close()
            except OSError:
                pass

    if proc.returncode != 0:
        raise McpxError(
            "aliyun configure 退出码 %s, 登录未完成。\n"
            "想看完整交互可自行在终端执行: aliyun configure --mode OAuth"
            % proc.returncode
        )
    sys.stdout.write("登录成功, 凭证已写入 %s。接着跑 `doctor` 验证。\n"
                     % credential_config_path())
    return EXIT_OK


GLOBAL_FLAGS_WITH_VALUE = ("--timeout",)


def hoist_leading_flags(argv):
    """把子命令之前的通用参数挪到子命令之后。

    usage 把 --timeout 列在「通用参数」下, 用户很自然会写
    `mcpx --timeout 420 call CallCLI ...`。原先这会被当成未知子命令退出 2。
    现在两种位置都接受。
    """
    leading = []
    rest = list(argv)
    while rest and rest[0].startswith("-"):
        flag = rest.pop(0)
        leading.append(flag)
        if flag in GLOBAL_FLAGS_WITH_VALUE and rest:
            leading.append(rest.pop(0))
    if not rest:
        return leading
    return [rest[0]] + rest[1:] + leading


def main(argv=None):
    argv = hoist_leading_flags(list(sys.argv[1:] if argv is None else argv))

    def _terminate(signum, _frame):
        raise SystemExit(EXIT_TRANSPORT)

    handled = [signal.SIGINT]
    if not IS_WINDOWS:
        handled.append(signal.SIGTERM)
    for sig in handled:
        try:
            signal.signal(sig, _terminate)
        except (ValueError, OSError, AttributeError):
            pass

    if not argv:
        sys.stderr.write(USAGE)
        return EXIT_USAGE

    sub = argv[0]
    rest = argv[1:]
    handlers = {
        "doctor": cmd_doctor,
        "login": cmd_login,
        "list": cmd_list,
        "schema": cmd_schema,
        "call": cmd_call,
    }
    if sub not in handlers:
        sys.stderr.write("未知子命令: %s\n\n%s" % (sub, USAGE))
        return EXIT_USAGE
    try:
        return handlers[sub](rest)
    except McpxError as exc:
        sys.stderr.write("%s\n" % exc)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
