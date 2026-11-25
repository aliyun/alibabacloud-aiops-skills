#!/usr/bin/env python3
"""Embedded constants of the skill: endpoints, the per-site matrix, limits and cache paths.

Site-neutral by construction: the two portals differ only in the data described here, never in
behaviour. This module imports nothing from the rest of the package, so it is the one place
where a volatile fact about either portal is recorded.
"""

from __future__ import annotations

import json
import os
import platform
import re
import sys
import tempfile
import uuid


SKILL_NAME = "alibabacloud-developer-docs"
# Single source of truth for the versioned User-Agent: references/manifest.json.
_MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "manifest.json"
)
with open(_MANIFEST_PATH, encoding="utf-8") as _manifest_file:
    SKILL_VERSION = json.load(_manifest_file)["version"]


CACHE_ROOT = os.path.expanduser(f"~/.cache/{SKILL_NAME}")


UNIQUE_ID = ""
_UNIQUE_ID_RE = re.compile(r"[0-9a-f]{32}")


# Keep the /help prefix: dropping it can return HTTP 200 with a WAF HTML page instead of JSON.
SEARCH_JSON_API = {
    "cn": "https://help.aliyun.com/help/json/search.json",
    "intl": "https://www.alibabacloud.com/help/json/search.json",
}

DOC_DETAIL_API = {
    "cn": "https://help.aliyun.com/help/json/document_detail.json",
    "intl": "https://www.alibabacloud.com/help/json/document_detail.json",
}


# Per-site constants (MUST 1.1.2: embedded as constants, never loaded from a data file).
# "llms_base" carries a {lang} placeholder; "path_prefix" is the URL path segment that
# precedes a product slug, used to build product-code extraction regexes and URL needles.
SITES = {
    "cn": {
        "label": "China site",
        "llms_base": "https://help.aliyun.com/{lang}",
        "path_prefix": "/{lang}/",
        "langs": ("zh", "en"),
        "default_lang": "zh",
        "index_timeout": 15,
        "result_host": "help.aliyun.com",
    },
    "intl": {
        "label": "international site",
        "llms_base": "https://www.alibabacloud.com/help/{lang}",
        "path_prefix": "/help/{lang}/",
        "langs": ("en", "zh", "tc", "ja", "id", "pt-br", "fr"),
        "default_lang": "en",
        "index_timeout": 20,
        "result_host": "www.alibabacloud.com",
    },
}


DEFAULT_SITE = "cn"


# External documentation sources: standalone llms.txt corpuses outside the Alibaba Cloud help
# center infrastructure. Each entry carries a fixed URL, a display label and a per-source timeout.
EXT_SOURCES = {
    "qoder": {
        "label": "Qoder",
        "llms_url": "https://docs.qoder.com/llms.txt",
        "timeout": 15,
    },
    "qoder-cn": {
        "label": "Qoder (China)",
        "llms_url": "https://docs.qoder.cn/llms.txt",
        "timeout": 15,
    },
    "qwenai": {
        "label": "Qwen AI (China)",
        "llms_url": "https://platform.qianwenai.com/docs/llms.txt",
        "timeout": 15,
    },
    "qwencloud": {
        "label": "Qwen Cloud (International)",
        "llms_url": "https://docs.qwencloud.com/llms.txt",
        "timeout": 20,
    },
}


# The endpoint host follows the site; website and language still explicitly select the corpus.
SEARCH_BACKENDS = {
    "search_json": {
        "endpoint": SEARCH_JSON_API,
        "items_path": ("data", "documents", "data"),
        "total_path": ("data", "documents", "totalCount"),
    },
}


# Languages whose full-text leg returns a real corpus. Any other language silently falls
# back to English server-side (verified: 28/28 combinations returned the English totalCount
# and English URL language segment), so the full-text leg is skipped for them instead.
SEARCH_LANG_WHITELIST = frozenset({"en", "zh"})


# search.json paging bounds (empirically verified on 2026-09-08):
#   pageSize > 200  -> silent degradation, totalCount=0 and the "data" key disappears;
#   pageSize == 1   -> totalCount collapses to 0 when the query hits a product name;
#   pageSize 200    -> 2.5-3.1 s, so the international leg stays at 20-50 items per page.
INTL_SEARCH_PAGESIZE_MIN = 2


INTL_SEARCH_PAGESIZE_MAX = 200


INTL_SEARCH_PAGESIZE_DEFAULT = 50


# Query guard rails for search.json: an empty "keywords" returns the whole-corpus hot list
# (93046 items) and an over-long query silently returns totalCount=0.
MAX_QUERY_LEN = 60


# Language aliases accepted on the command line and normalized before any request.
# "pt" is not a valid code: the real one is "pt-br" ("pt" 302-redirects to an empty body).
LANG_ALIASES = {"pt": "pt-br", "pt_br": "pt-br", "zh-cn": "zh", "en-us": "en"}


# Languages that exist in the front end but have no corpus of their own; their llms.txt is
# byte-identical to English (verified: ko/de master sha256 == en master sha256).
UNSUPPORTED_LANGS = frozenset({"ko", "de", "es", "th", "vi", "tr", "ru", "it"})


META_BASE = {
    "cn": "https://api.aliyun.com/meta/v1",
    "intl": "https://api.alibabacloud.com/meta/v1",
}

# Without ?language= both hosts return Chinese; unknown values silently fall back to English and
# ZH_TW returns English too, so Traditional Chinese must be ZH_HK.
META_LANGS = {"zh": "ZH_CN", "en": "EN_US", "ja": "JA_JP", "tc": "ZH_HK",
              "id": "ID_ID", "pt-br": "PT_BR", "fr": "FR_FR"}

SDK_DOC_API = {
    "cn": "https://api.aliyun.com/api/sdk/product/docNew",
    "intl": "https://api.alibabacloud.com/api/sdk/product/docNew",
}

SDK_DOC_LANGS = {"zh": "ZH_CN", "en": "EN_US"}

# Portal-internal endpoint (no stability promise): data.lastSdkInfo maps each SDK language key to
# {language, package_name, sdk_type}. The portal hides SDK_HIDDEN_KEYS and labels "-tea" keys as
# SDK V2.0 (recommended) and every other key as V1.0 (not recommended).
SDK_INFO_API = {
    "cn": "https://api.aliyun.com/api/sdk/product/info",
    "intl": "https://api.alibabacloud.com/api/sdk/product/info",
}

SDK_HIDDEN_KEYS = frozenset({"product", "version", "tea", "javav5", "nodejs-tea"})

IAC_ENDPOINT = "https://iac.cn-zhangjiakou.aliyuncs.com"
IAC_REGION = "cn-zhangjiakou"
IAC_API_VERSION = "2021-08-06"


# Registry of the official Alibaba Cloud agent skills, one host per site. Two public endpoints:
# '/search?keyword=&page=&pageSize=' lists entries, '/<skillName>' returns one entry with its
# SKILL.md body in "content". Both answer the envelope {"code","message","data"}; an unknown
# skill name answers HTTP 404 with code 404. The two sites publish different catalogues
# (verified 2026-10-30: keyword 'live' returns 14 entries on cn and 9 on intl).
SKILLS_API = {
    "cn": "https://skills.aliyun.com/api/public/skills",
    "intl": "https://skills.alibabacloud.com/api/public/skills",
}
# pageSize is clamped server-side at 100 (a request for 500 answers pageSize=100), so the walk
# over an unbounded -n asks for full pages and stops at the advertised total.
SKILLS_PAGESIZE_MAX = 100
SKILLS_PAGESIZE_DEFAULT = 20
# Hard cap on the page walk, so a wrong "total" from the server cannot turn -n 0 into a crawl.
SKILLS_MAX_PAGES = 10
SKILLS_MAX_BYTES = 4 * 1024 * 1024


# Official announcements (www.aliyun.com/notice, www.alibabacloud.com/notice), one query endpoint
# per site. It is a form POST (product=bulletin&action=Query&params=<json>) that answers
# {"code":"200","data":{"Data":{"TotalCount","Info":[...]}}} anonymously, but only when a Referer
# on the site's public notice page is present: without it the envelope is code "403", data null.
# Measured 2026-11-02: cn publishes zh only (en/ja answer 0); intl publishes the same 1963 notices
# in en, zh and ja (tc/id/pt-br/fr answer 0). BulletinId/Id and time fields are ignored as filters,
# so one notice cannot be fetched by id; every list item already carries its full plain-text body.
NOTICE_API = {
    "cn": "https://fecs.console.aliyun.com/data/api.json?_fetcher_=bulletin__Query",
    "intl": "https://fecs.console.alibabacloud.com/data/api.json?_fetcher_=bulletin__Query",
}
# The public notice list of each site: the Referer the endpoint requires, and the page a user can open.
NOTICE_PAGE = {
    "cn": "https://www.aliyun.com/notice/",
    "intl": "https://www.alibabacloud.com/notice/intl/list",
}
NOTICE_LANGS = {"cn": ("zh",), "intl": ("en", "zh", "ja")}
# Top-level BulletinType values accepted by the server as a filter; an unknown value answers 0.
NOTICE_TYPES = ("loss", "security", "other")
# The server accepts pageSize 500, but every item carries a body of up to a few KB.
NOTICE_PAGESIZE_MAX = 50
NOTICE_PAGESIZE_DEFAULT = 10
NOTICE_MAX_BYTES = 4 * 1024 * 1024


_AGENT_ENV_MARKERS = (("QODER_CLI", "qoder-cli"),)
UNKNOWN_AGENT = "unknown-ai-agent"

_UA_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _ua_token(value, limit=40, fallback="unknown"):
    """Reduce an outside-supplied value to a header-safe User-Agent token."""
    return _UA_UNSAFE.sub("-", str(value or "")).strip("-")[:limit] or fallback


def _detect_agent():
    skill_dir = os.path.dirname(SCRIPTS_DIR)
    skills_dir = os.path.dirname(skill_dir)
    agent_dir = os.path.basename(os.path.dirname(skills_dir))
    if (os.path.basename(skill_dir) == SKILL_NAME and os.path.basename(skills_dir) == "skills"
            and agent_dir.startswith(".") and agent_dir.lstrip(".")):
        return _ua_token(agent_dir.lstrip("."), fallback=UNKNOWN_AGENT)
    declared = os.environ.get("ALIYUN_HELP_AGENT", "")
    if declared.strip():
        return _ua_token(declared, fallback=UNKNOWN_AGENT)
    for var, name in _AGENT_ENV_MARKERS:
        if os.environ.get(var):
            return name
    return UNKNOWN_AGENT


SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_logical_cwd = os.environ.get("PWD", "")
if (os.path.isabs(_logical_cwd) and os.path.realpath(_logical_cwd) == os.getcwd()
        and os.path.commonpath((os.getcwd(), SCRIPTS_DIR)) == os.getcwd()):
    # Python resolves cwd symlinks; the shell retains the invocation path in PWD.
    SCRIPTS_DIR = os.path.normpath(os.path.join(_logical_cwd, os.path.relpath(SCRIPTS_DIR, os.getcwd())))
UA_AGENT = _detect_agent()
# The ID lives next to the scripts, not in the user cache: each installation then has its own
# ID even when several share one HOME, and a read-only or absent HOME does not lose it.
UNIQUE_ID_PATH = os.path.join(SCRIPTS_DIR, ".unique_id")
UA_OS = f"{_ua_token(platform.system())}-{_ua_token(platform.machine())}"
UA_PYTHON = _ua_token(platform.python_version())


def _user_agent(unique_id: str) -> str:
    suffix = f"/{unique_id}" if unique_id else ""
    return (
        f"AlibabaCloud-Agent-Skills/{SKILL_NAME}{suffix} skill-version/{SKILL_VERSION}"
        f" (agent/{UA_AGENT}; os/{UA_OS}; python/{UA_PYTHON})"
    )


UA = _user_agent(UNIQUE_ID)


def ensure_unique_id() -> str:
    global UNIQUE_ID, UA
    if UNIQUE_ID:
        return UNIQUE_ID
    try:
        try:
            with open(UNIQUE_ID_PATH, encoding="ascii") as f:
                unique_id = f.read(33)
        except FileNotFoundError:
            directory = os.path.dirname(UNIQUE_ID_PATH)
            os.makedirs(directory, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=directory,
                                             prefix=".unique_id.") as f:
                f.write(uuid.uuid4().hex)
                f.flush()
                # Publish complete contents without replacing another process's ID.
                try:
                    os.link(f.name, UNIQUE_ID_PATH)
                except FileExistsError:
                    pass
            with open(UNIQUE_ID_PATH, encoding="ascii") as f:
                unique_id = f.read(33)
        if not _UNIQUE_ID_RE.fullmatch(unique_id):
            raise ValueError("invalid cached unique_id")
    except (OSError, UnicodeError, ValueError) as e:
        unique_id = uuid.uuid4().hex
        print(f"WARN[unique-id-cache] cannot reuse persistent ID ({e}); using a process-local ID.",
              file=sys.stderr)
    UNIQUE_ID = unique_id
    UA = _user_agent(UNIQUE_ID)
    return UNIQUE_ID


TIMEOUT = SITES[DEFAULT_SITE]["index_timeout"]
# Named once so the CLI help text and the request layer cannot drift apart (N3).
DEFAULT_DOC_TIMEOUT = TIMEOUT


SEARCH_TIMEOUT = 8

# Response size caps (N4), each set above the largest legitimate body measured on 2026-09-08
# with at least double headroom: the biggest product index is 1.49 MB (intl/ja/oss, cn/oss
# 0.92 MB), a search.json page at pageSize=200 is 419 KB, and a document body fetched as .md
# peaked at 119 KB. An unexpected response beyond a cap is truncated with a WARN instead of
# being buffered in full.
LLMS_MAX_BYTES = 8 * 1024 * 1024
SEARCH_MAX_BYTES = 2 * 1024 * 1024
DOC_MAX_BYTES = 4 * 1024 * 1024


# Remembered (site, lang) of this installation: written whenever a command passes --site or
# --lang, and reused by later runs that pass neither, so a bare English error code after a
# Chinese question keeps querying the corpus the user already confirmed.
SCOPE_CACHE_PATH = os.path.join(CACHE_ROOT, "scope.json")


# categoryId mapping cache
CATEGORY_CACHE_PATH = os.path.join(CACHE_ROOT, "category_map.json")


CATEGORY_CACHE_TTL_DAYS = 30


# cn serves zh/en only (other languages answer an empty tree); intl serves all seven languages.
MAIN_MENU_API = {
    "cn": "https://help.aliyun.com/help/json/mainMenu.json?website=cn&language={lang}&channel=",
    "intl": "https://www.alibabacloud.com/help/json/mainMenu.json?website=intl&language={lang}&channel=",
}
MENU_PATH_API = {
    "cn": "https://help.aliyun.com/help/json/menupath.json",
    "intl": "https://www.alibabacloud.com/help/json/menupath.json",
}
MENU_PRODUCT_NODE_TYPE = 16
MENU_SUBPRODUCT_NODE_TYPE = 8
MENU_MAX_BYTES = 4 * 1024 * 1024
MENU_CACHE_DIR = os.path.join(CACHE_ROOT, "menu")
MENU_CACHE_TTL_SECONDS = 86400


# Local cache for product llms.txt: every search with -p fetches the full
# product llms.txt (~1MB); cache it for 3 days to avoid repeated downloads; on expiry/read failure,
# silently refetch from origin and refresh.
LLMS_CACHE_DIR = os.path.join(CACHE_ROOT, "llms")


EXT_CACHE_DIR = os.path.join(CACHE_ROOT, "ext")


LLMS_CACHE_TTL_DAYS = 3

# Disk budget of the llms.txt cache (N1). A whole-catalogue walk caches one file per product
# (~78 KB average, 1 MB for the largest), so an unbounded cache grows by ~33 MB per site+language
# scanned; the trim keeps the newest entries and drops the oldest past the budget.
LLMS_CACHE_MAX_BYTES = 300 * 1024 * 1024
LLMS_CACHE_TRIM_TO = 0.8


# Paging is endpoint knowledge and lives with the endpoint: the search.json pageSize clamp is
# _clamp_page_size in help_search (guard S7). The leg never walks several pages, so no
# page-count cap exists.


# Union of the languages both sites host, in the order used by user-facing error messages.
_ALL_LANGS = ("zh", "en", "tc", "ja", "id", "pt-br", "fr")


# Every language code that can legitimately appear as a URL path segment: the hosted languages
# plus the front-end-only ones the server silently redirects away from. _url_lang_segment uses it
# to tell a language segment from an ordinary first path segment ('document_detail'), which the
# China site puts directly after the host.
_KNOWN_LANG_SEGMENTS = frozenset(_ALL_LANGS) | UNSUPPORTED_LANGS


# Entry shape shared by every llms.txt parser (catalog listing and the two index-leg scanners)
# so they can never disagree about what an entry is.
# The ': summary' part is OPTIONAL on purpose: a required summary group hid every entry that
# carries none, which is 492 of 4359 lines (11.3%) in the cn/zh OSS index and 198 of 1568
# (12.6%) in ECS (measured 2026-09-08). Most of them are navigation nodes, but a navigation
# node is still a real catalog entry the caller may want to descend into. re.findall() yields ''
# for the absent group, so every downstream 'desc[:120]' / 'desc.lower()' stays safe.
_DOC_ENTRY_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\)(?::\s*(.*))?$", re.MULTILINE)


class _UsageError(Exception):
    """Invalid site/language combination on the command line; main() maps it to exit code 2."""


# ---------------------------------------------------------------------------
# Per-process run options, set once from the command line and read by every leg.
# Each switch has a single named setter so no call site carries its own timeout arithmetic
# or cache-bypass flag.
# ---------------------------------------------------------------------------

# N3: a caller may widen or narrow every request deadline from the command line (0 = keep the
# per-endpoint default). The override is applied only through effective_timeout(), so no call
# site carries its own timeout arithmetic.
_cli_timeout = 0


def set_cli_timeout(seconds) -> None:
    """Record the --timeout override; a non-positive or unparsable value means 'no override'."""
    global _cli_timeout
    try:
        _cli_timeout = int(seconds or 0)
    except (TypeError, ValueError):
        _cli_timeout = 0
    if _cli_timeout < 0:
        _cli_timeout = 0


def effective_timeout(base: int) -> int:
    """Deadline of one request: the CLI override when given, else the endpoint's own value."""
    return _cli_timeout if _cli_timeout > 0 else base


# N8: the short-TTL full-text result cache is on by default and disabled per run by
# --no-result-cache, so a caller can force live endpoint behaviour for one invocation.
_result_cache_off = False


def set_result_cache(enabled) -> None:
    """Record the --no-result-cache choice (anything falsy disables the cache)."""
    global _result_cache_off
    _result_cache_off = not bool(enabled)


def result_cache_enabled() -> bool:
    """Whether a full-text result set may be reused inside the short TTL window."""
    return not _result_cache_off
