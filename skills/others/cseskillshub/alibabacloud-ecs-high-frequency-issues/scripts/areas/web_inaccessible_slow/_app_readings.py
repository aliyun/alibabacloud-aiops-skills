"""Read an application-layer artifact and name only what the artifact proves.

The network layers can be decided from cloud APIs; the largest remaining cause
class lives inside the guest and only shows up as an artifact: an IIS
configuration-error dialog, a PHP-FPM slowlog stack, a 404 asset list, a 301 to
another host, a 200 with an empty body. Collecting those artifacts and stopping at
"have the customer check the application" left the class permanently unconfirmed.

Pure parsing: no I/O, no dispatch, no credential. Every finding carries the line it
was read from, so a conclusion can always be traced back to a reading. An artifact
shape that is not recognised stays undecided instead of being guessed.
"""
import re

OCR_FIXUPS = (("cur1_exec", "curl_exec"), ("cur1_", "curl_"), ("s0cket", "socket"),
              ("up1oad", "upload"), ("sing1e_", "single_"), ("fi1e_", "file_"),
              ("wwwr00t", "wwwroot"), ("c0m", "com"))
IIS_SECTION_RE = re.compile(
    r"(?i)定义了重复的|重复的[“\"']?[\w./]+[”\"']?节|duplicate\s+(?:configuration\s+)?section"
    r"|unrecognized\s+configuration\s+section|configuration\s+section[^\n]{0,40}duplicate"
    r"|无法识别的配置节|配置节[^\n]{0,12}重复")
IIS_CONTEXT_RE = re.compile(r"(?i)web\.config|配置错误|行号|应用程序池|IIS|HTTP\s*错误")
ASSEMBLY_RE = re.compile(
    r"(?i)未能加载文件或程序集|Could not load file or assembly|未能加载类型|FileNotFoundException")
DOTNET_SOURCE_RE = re.compile(r"(?i)找不到源文件|source\s+files?\s+(?:could\s+not|not)\s+be\s+found")
DOTNET_CONTEXT_RE = re.compile(r"(?i)\.NET|ASP\.NET|Framework\s*[234]")
SLOWLOG_RE = re.compile(r"(?i)script_filename|php-fpm|slowlog|\[0x[0-9a-f]{6,}\]")
REMOTE_CALL_RE = re.compile(
    r"(?i)curl_exec|single_curl|file_get_contents|fsockopen|curl_multi|use_socket")
ASSET_404_RE = re.compile(r"(?i)(?<![0-9])404(?![0-9])")
ASSET_KIND_RE = re.compile(
    r"(?i)uploadfile|static/upload|/upload/|\.(?:jpg|jpeg|png|gif|css|js|webp|ico)\b"
    r"|图片|静态资源|静态文件")
DB_ERROR_RE = re.compile(
    r"(?i)(?:数据库|mysql|mysqli|mariadb|sqlserver|mssql|redis|postgresql)[^\n]{0,18}"
    r"(?:连接失败|无法连接|连接不上|连不上|拒绝连接|连接超时|连接报错|密码错误|不可用)"
    r"|Access denied for user|SQLSTATE\[HY000\]|Too many connections"
    r"|(?:can\s?not|can't|cannot|unable\s+to|failed\s+to)\s+connect\s+to\s+"
    r"(?:the\s+)?(?:local\s+)?(?:mysql|mariadb|mssql|sqlserver|postgres|postgresql|redis)"
    r"|(?:mysql|mariadb|postgresql|redis)\s+(?:server\s+)?(?:has\s+gone\s+away|is\s+not\s+running)"
    r"|Connection refused[^\n]{0,20}(?:3306|mysql)")
UPSTREAM_RE = re.compile(
    r"(?i)(?<![0-9])(?:502|504)(?![0-9])[^\n]{0,28}(?:nginx|apache|gateway|upstream|php|tomcat|网关)"
    r"|(?:nginx|apache|upstream|php-fpm|tomcat|后端|backend)[^\n]{0,28}(?:502|504)"
    r"|(?:502|504)[^\n]{0,12}(?:后端|backend)"
    r"|Bad\s*Gateway|Gateway\s*Time-?out|upstream\s+timed\s+out")
PHP_MISSING_FILE_RE = re.compile(
    r"(?i)failed to open stream|No such file or directory in|require(?:_once)?\(\)[^\n]{0,40}failed"
    r"|include(?:_once)?\(\)[^\n]{0,40}failed|Fatal error[^\n]{0,60}require")
FPM_SOCKET_RE = re.compile(
    r"(?i)another FPM instance seems to already listen|already listen on\s*\S+\.sock"
    r"|Address already in use[^\n]{0,30}(?:sock|9000)|bind\(\)[^\n]{0,40}failed")
FPM_POOL_RE = re.compile(
    r"(?i)(?:max_children|max_requests|server reached|max_children reached)"
    r"|(?:php-fpm|PHP-FPM)[^\n]{0,24}(?:占用大量内存|内存[^\n]{0,8}不释放|进程数|池)")
PORT_DOWN_RE = re.compile(
    r"(?i)(?:端口|port)\s*[:：]?\s*(\d{2,5})[^\n]{0,12}(?:未启动|没启动|未监听|没有监听|不通)"
    r"|(?:服务|进程|后端)[^\n]{0,10}(?:未启动|没启动|已停止|未运行)")
REDIRECT_RE = re.compile(
    r"(?i)(?<![0-9])(?:301|302|307|308)(?![0-9])[^\n]{0,28}(?:跳转|转发|重定向|redirect|Location)"
    r"|(?:跳转|转发|重定向|redirect)[^\n]{0,20}(?:到|至|to)[^\n]{0,16}(?:https?://|[a-z0-9-]+\.)"
    r"|Location\s*[:：]\s*https?://")
BLANK_RE = re.compile(r"(?i)空白|白屏|无法显示|不显示|显示不出|没有任何内容")
OK_200_RE = re.compile(r"(?i)(?<![0-9])200(?![0-9])\s*(?:正常|OK|ok)?|状态码?正常|返回正常")
CERT_ABSENT_RE = re.compile(
    r"(?i)(?:未|没有|没)(?:有)?(?:配置|部署|绑定|安装|申请|上传)(?:过)?(?:任何)?"
    r"(?:SSL\s*|TLS\s*|https\s*)?证书")
SCHEME_SPLIT_RE = re.compile(
    r"(?i)http[^\n]{0,40}(?:可以|能)(?:正常)?(?:访问|打开)[^\n]{0,40}https"
    r"|https[^\n]{0,24}(?:打不开|无法访问|不能访问|报错|失败)[^\n]{0,40}http"
    r"|您访问的是\s*https")
APP_500_RE = re.compile(r"(?i)(?<![0-9])500(?![0-9])[^\n]{0,20}(?:内部服务器错误|Internal\s*Server\s*Error)"
                        r"|Internal\s*Server\s*Error")
UNIT_TAIL_RE = re.compile(r"(?i)^\s*(?:ms|s\b|条|页|元|个|次|天|秒|分钟|小时|万|千|％|%)")


def _normalized(text):
    out = text or ""
    for wrong, right in OCR_FIXUPS:
        out = out.replace(wrong, right)
    return out


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _status_lines(lines, pattern):
    """Lines whose code is a status, not a latency or a page size."""
    out = []
    for line in lines:
        found = pattern.search(line)
        if not found:
            continue
        if UNIT_TAIL_RE.match(line[found.end():found.end() + 8]):
            continue
        out.append(line)
    return out


def _first(pattern, lines):
    for line in lines:
        if pattern.search(line):
            return line
    return ""


FINDINGS = (
    ("iis_config", "The site's own IIS configuration is rejected: the configuration error names "
                   "a duplicate or unrecognized section in web.config, so IIS cannot serve the "
                   "site even though it is installed and running."),
    ("dotnet_component", "A required .NET component is missing or failed to install: the "
                         "application cannot load the named assembly, which is an in-guest "
                         "component gap rather than a network fault."),
    ("fpm_socket", "The PHP process manager cannot start: its socket or port is already held by "
                   "another instance, so no worker is left to answer the web server."),
    ("php_missing_file", "The application fails while loading a file that is not there: the PHP "
                         "error names the missing path, which stops the page before any output."),
    ("php_remote_asset", "The application's own slow stack shows it fetching its local static "
                         "assets over HTTP: the page waits on those calls, which is why the site "
                         "loads slowly or times out while the port is reachable."),
    ("fpm_pool", "The PHP worker pool is exhausted or its workers do not release memory: requests "
                 "queue behind the pool, which is an application capacity limit rather than a "
                 "network fault."),
    ("port_down", "A service the site depends on is not running on its port: the artifact names "
                  "the port and its stopped state."),
    ("missing_assets", "The site answers but referenced static files return 404: the document "
                       "root is missing files the pages ask for."),
    ("db_connect", "The application cannot reach its database: the artifact carries a database "
                   "connect or authentication failure."),
    ("upstream", "The front-end web server answers but its backend does not: the gateway error "
                 "is produced by the web server, not by the cloud network."),
    ("redirect", "The site itself answers and redirects the visitor to another host: the "
                 "unreachable symptom is produced by a redirect rule in the site, not by ECS "
                 "reachability."),
    ("blank_body", "The site returns success with an empty body: the request reaches the "
                   "application and the application produces no output."),
    ("https_no_cert", "HTTPS is not served for this hostname while HTTP works: no certificate is "
                      "deployed for the site, so only the http:// address can open."),
    ("app_5xx", "The application itself returns a server error: the request reached the site and "
                "the site failed while handling it."),
)
ACTIONS = {
    "iis_config": [
        "Have the customer back up the site web.config, rename it and re-open the page to isolate "
        "the offending section, then restore it.",
        "Have the customer compare this web.config and the application pool .NET CLR version with "
        "a server where the site works, and list the Windows updates installed just before the "
        "fault.",
    ],
    "dotnet_component": [
        "Have the customer install the named .NET component or Windows feature, supplying a valid "
        "alternate source path when the installer reports missing source files, then recycle the "
        "application pool.",
    ],
    "fpm_socket": [
        "Have the customer list the processes holding that socket or port, stop the duplicate "
        "PHP process manager instance, then start one instance and confirm the socket is created "
        "once.",
    ],
    "php_missing_file": [
        "Have the customer restore the file the error names, or correct the include path in the "
        "site code; if the path is not part of their application, treat it as injected code and "
        "back up before removing it.",
    ],
    "fpm_pool": [
        "Have the customer read the PHP process manager pool settings and worker count against "
        "the instance memory, raise the limit only within available memory, and set a request "
        "recycle count so workers release memory.",
    ],
    "port_down": [
        "Have the customer start the service that owns the named port, enable it at boot, and "
        "confirm it listens before re-testing the site.",
    ],
    "php_remote_asset": [
        "Have the customer change the site code to read its own static files from the local path "
        "instead of requesting them over HTTP, and remove references to assets that no longer "
        "exist.",
        "Have the customer add connect and read timeouts to every remaining outbound call in the "
        "page path, so one slow host cannot hold the whole request.",
    ],
    "missing_assets": [
        "Have the customer compare the site upload directory against their local backup and "
        "restore the files that return 404, then re-open the page.",
        "Have the customer check path case, directory permissions and the site root binding for "
        "those URLs before re-uploading.",
    ],
    "db_connect": [
        "Have the customer check the database service state first (systemctl status mysqld, or "
        "the matching MariaDB/PostgreSQL/Redis unit or Windows service) and start it if it is "
        "not running, then re-test the site.",
        "Have the customer read the site's database configuration file and confirm host, port, "
        "user and password against the running database, then test that connection from inside "
        "the instance.",
    ],
    "upstream": [
        "Have the customer read the backend service state and its listening port (php-fpm, "
        "tomcat or the app process) and the web server error log tail, then align the upstream "
        "address and timeout with it.",
    ],
    "redirect": [
        "Have the customer read the redirect rules in the web server config, .htaccess and the "
        "application code, and confirm whether the jump to the other host is intended.",
        "Have the customer check for an abnormal plugin or an injected script if the redirect was "
        "not configured by them, and back up before cleaning.",
    ],
    "blank_body": [
        "Have the customer read the PHP and application error log tail for this request, then "
        "rename the framework runtime/cache directory and re-open the page.",
        "Have the customer verify the database settings and free disk space and inodes, since a "
        "full disk also produces an empty page under a success status.",
    ],
    "https_no_cert": [
        "Have the customer issue a certificate for this hostname in the SSL Certificate Service "
        "console, deploy it to the web server or panel and reload, then re-open the https address.",
        "Have the customer use the http:// address as the immediate way to reach the site until "
        "the certificate is deployed.",
    ],
    "app_5xx": [
        "Have the customer read the site error log tail for the failing request and show the "
        "detailed error locally, then fix the handler, module or code path it names.",
    ],
}


def interpret(text, os_type="linux"):
    """Return {kind, conclusion, evidence, actions, others} or kind='' when undecided."""
    raw = text or ""
    body = _normalized(raw)
    lines = _lines(body)
    raw_lines = _lines(raw)
    result = {"kind": "", "conclusion": "", "evidence": [], "actions": [], "others": []}
    if not lines:
        return result
    matched = []

    def hit(kind, evidence):
        if kind not in [row[0] for row in matched]:
            matched.append((kind, [line for line in evidence if line][:3]))

    section = _first(IIS_SECTION_RE, lines)
    if section and IIS_CONTEXT_RE.search(body):
        context = _first(re.compile(r"(?i)文件名|行号|web\.config"), lines)
        hit("iis_config", [section, context])
    assembly = _first(ASSEMBLY_RE, lines)
    if assembly:
        hit("dotnet_component", [assembly])
    elif DOTNET_SOURCE_RE.search(body) and DOTNET_CONTEXT_RE.search(body):
        hit("dotnet_component", [_first(DOTNET_SOURCE_RE, lines),
                                 _first(DOTNET_CONTEXT_RE, lines)])
    socket_clash = _first(FPM_SOCKET_RE, lines)
    if socket_clash:
        hit("fpm_socket", [socket_clash])
    missing_file = _first(PHP_MISSING_FILE_RE, lines)
    if missing_file:
        hit("php_missing_file", [missing_file])
    if SLOWLOG_RE.search(body) and REMOTE_CALL_RE.search(body):
        hit("php_remote_asset", [_first(REMOTE_CALL_RE, lines), _first(SLOWLOG_RE, lines)])
    pool = _first(FPM_POOL_RE, lines)
    if pool and re.search(r"(?i)php-fpm|php\b|max_children|max_requests", body):
        hit("fpm_pool", [pool])
    port_down = _first(PORT_DOWN_RE, lines)
    if port_down:
        hit("port_down", [port_down])
    asset_lines = _status_lines(lines, ASSET_404_RE)
    if asset_lines and ASSET_KIND_RE.search(body):
        hit("missing_assets", [line for line in asset_lines if ASSET_KIND_RE.search(line)][:2]
            or asset_lines[:2])
    database = _first(DB_ERROR_RE, lines)
    if database:
        hit("db_connect", [database])
    upstream = _first(UPSTREAM_RE, lines)
    if upstream:
        hit("upstream", [upstream])
    redirect = _first(REDIRECT_RE, lines)
    if redirect:
        hit("redirect", [redirect])
    blank = _first(BLANK_RE, lines)
    if blank and OK_200_RE.search(body):
        hit("blank_body", [blank])
    cert_absent = _first(CERT_ABSENT_RE, lines)
    scheme = _first(SCHEME_SPLIT_RE, lines)
    if cert_absent or scheme:
        hit("https_no_cert", [cert_absent or scheme])
    server_error = _first(APP_500_RE, lines)
    if server_error:
        hit("app_5xx", [server_error])
    if not matched:
        return result
    order = [row[0] for row in FINDINGS]
    matched.sort(key=lambda row: order.index(row[0]))
    kind, evidence = matched[0]
    conclusions = dict(FINDINGS)
    result["kind"] = kind
    result["conclusion"] = conclusions[kind]
    result["evidence"] = evidence
    result["actions"] = list(ACTIONS[kind])
    result["others"] = [row[0] for row in matched[1:]]
    for other_kind, other_evidence in matched[1:3]:
        result["evidence"] += other_evidence[:1]
    result["evidence"] = result["evidence"][:5]
    if os_type and "windows" in str(os_type).lower() and kind == "php_remote_asset":
        result["actions"] = [action.replace("php-fpm", "the PHP process")
                             for action in result["actions"]]
    return result
