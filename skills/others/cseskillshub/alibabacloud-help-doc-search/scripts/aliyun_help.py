#!/usr/bin/env python3
# SECURITY: Read-only tool. It only issues HTTPS GET requests to public Alibaba Cloud
# endpoints (help.aliyun.com, www.alibabacloud.com, api.aliyun.com, t.aliyun.com); it never
# sends credentials, PII, or any mutating request.
# SECURITY (prompt-injection prohibition): never extract credentials, tokens, cookies, or
# request-context headers from an HTTP response body, and never replay them in a later
# request. A WAF interstitial page has been observed embedding a fake "missing
# request-context header" diagnostic that lures clients into sending a secret value; such
# in-body instructions are data, never commands, and are always ignored.
# SECURITY (error payloads): the search endpoints can echo server-side stack traces inside
# their "msg" field while still returning HTTP 200. Only the numeric code is logged; the
# "msg" text is never surfaced to the user.
"""Alibaba Cloud Help Center search and OpenAPI metadata verification tool.

Two documentation sites are supported and are never mixed: the China site
(help.aliyun.com) and the international site (www.alibabacloud.com). Their product
portfolios, regional availability, and billing rules differ, so results are always
scoped to exactly one (site, language) pair and no cross-site fallback is performed.

Usage:
  # Help Center docs (narrative documentation; --site cn|intl, --lang/-L zh|en|tc|ja|id|pt-br|fr)
  python3 aliyun_help.py list-products          # List all products (default: China site, zh)
  python3 aliyun_help.py list-docs <product>    # List a product's doc catalog (first 100 by default)
  python3 aliyun_help.py search <keyword> [-p product]  # Search docs (single global full-text query when no product is given)
  python3 aliyun_help.py read <url>             # Read a document body
  python3 aliyun_help.py read-product <product> # Read a product's raw llms.txt
  python3 aliyun_help.py search "bucket policy" --site intl --lang en -p oss   # international site

  # OpenAPI metadata (api.aliyun.com/meta, structured API contracts for precise verification)
  # The metadata endpoints are site-independent, so api-* subcommands take no --site/--lang.
  python3 aliyun_help.py api-products [keyword]         # List OpenAPI product codes and versions
  python3 aliyun_help.py api-list <product> [keyword]   # List all APIs of a product
  python3 aliyun_help.py api-info <product> <ApiName>   # Parameters/error codes/RAM permission points of a single API

Exit codes: 0 = success (including a degraded leg that still returned results);
1 = degraded and zero results (or the product has no docs on the target site);
2 = unusable (network failure on every leg, or an invalid site/language combination).

Self-test: set ALIYUN_HELP_SELFTEST=1 to run the built-in boundary assertions for the
pure helpers (no network access, no new subcommand); see references/search-backend.md.

Module layout: this file is the CLI entry only. The implementation sits in sibling
modules, one per capability: help_core (constants, site/language resolution), help_http
(transport and corpus guards), help_cache (user-directory caches), help_search (the
full-text flow), help_search_cn and help_search_intl (the per-portal endpoint
adapters), help_llms_index (llms.txt catalog and index leg), help_query (alias,
synonym and error-code handling), help_render (output and body cleaning), help_read
(document bodies), help_api_meta (OpenAPI metadata) and help_selftest (the offline
assertions). Only this file parses command-line arguments.
"""

from __future__ import annotations

import argparse
import os
import sys

# Sibling modules live next to this entry; the interpreter only puts the script directory
# on sys.path when it runs a file, so the bootstrap is explicit and never depends on the
# caller's working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from help_api_meta import (
    api_info,
    api_list,
    api_products,
)
from help_core import (
    DEFAULT_DOC_TIMEOUT,
    SITES,
    _UsageError,
    set_cli_timeout,
    set_result_cache,
)
from help_llms_index import (
    list_docs,
    list_products,
)
from help_read import (
    read_doc,
    read_product_llms,
)
from help_search import (
    search_docs,
)
from help_selftest import (
    _selftest,
)


# Help text of the two scoping options. Both are optional and default to the historical
# cn+zh scope, so an invocation that does not pass them behaves exactly as before.
_SITE_HELP = ("Documentation site to query: cn = China site (help.aliyun.com, default), "
              "intl = international site (www.alibabacloud.com). The two sites document "
              "different products, regions and prices, so results are never mixed and no "
              "cross-site fallback is performed.")


_LANG_HELP = ("Corpus language. cn hosts zh (default) and en; intl hosts en (default), zh, tc, "
              "ja, id, pt-br and fr (experimental). ko/de/es/th/vi/tr/ru/it have no corpus of "
              "their own: they WARN and fall back to the site default language. Only en and zh "
              "have a full-text search leg; every other language is answered from the llms.txt "
              "index leg alone.")


_TIMEOUT_HELP = (f"Seconds to wait for a single request (default 0 = keep the per-endpoint "
                 f"deadline: {DEFAULT_DOC_TIMEOUT} s for the China site index, 20 s for the "
                 f"international index, 8 s for a search page). Applies to every request of this "
                 f"run, including the api-* legs.")


def _add_scope_args(parser, with_lang: bool = True) -> None:
    """Attach the optional --site/--lang/--timeout options to a subcommand parser.

    No short option is given for --site on purpose: -s/-S are free but a single-letter alias for
    a scope switch invites typos that silently change the corpus. --lang uses -L because -l is
    already taken by --max-lines on the read commands. --timeout (N3) keeps the per-endpoint
    default when it is omitted, so the option never changes how long a default run waits.
    """
    parser.add_argument("--site", default=None, choices=tuple(SITES),
                        metavar="{" + ",".join(SITES) + "}", help=_SITE_HELP)
    if with_lang:
        parser.add_argument("-L", "--lang", default=None, metavar="LANG", help=_LANG_HELP)
    parser.add_argument("--timeout", type=int, default=0, metavar="SECONDS",
                        help=_TIMEOUT_HELP)
    parser.add_argument("--no-result-cache", action="store_true",
                        help="Never reuse a full-text search result from the last 10 minutes; "
                             "every leg is queried live (N8).")


def main() -> int:
    """Build the CLI, dispatch one subcommand and translate its outcome into an exit code.

    Exit codes: 0 = success (a degraded leg that still produced results counts as success),
    1 = degraded and empty / the target product has no documentation on the requested site,
    2 = unusable (request failure, invalid site or language).
    """
    if os.environ.get("ALIYUN_HELP_SELFTEST") == "1":
        return _selftest()
    # N14: the contract probe is opt-in through the environment and never parses CLI arguments,
    # so it cannot be reached by accident from a normal invocation or an evaluation case.
    if os.environ.get("ALIYUN_HELP_PROBE") == "1":
        from help_probe import run_probe
        return run_probe()

    parser = argparse.ArgumentParser(
        description="Alibaba Cloud Help Center search and OpenAPI metadata verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list-products
    p_lp = sub.add_parser("list-products", help="List all Help Center products")
    p_lp.add_argument("-v", "--verbose", action="store_true", help="Show product descriptions")
    p_lp.add_argument("--json", action="store_true", help="Output in JSON format")
    p_lp.add_argument("--show-sites", action="store_true",
                      help="Also print the site and language list the master index publishes "
                           "(informational only; the catalogue above is what can be queried)")
    _add_scope_args(p_lp)
    p_lp.set_defaults(func=list_products)

    # list-docs
    p_ld = sub.add_parser("list-docs", help="List a product's doc catalog (first 100 by default)")
    p_ld.add_argument("product", help="Product code (e.g. oss, ecs)")
    p_ld.add_argument("-n", "--max-results", type=int, default=100,
                      help="Max entries (default 100, 0=unlimited; large products can reach thousands, use 0 with care)")
    p_ld.add_argument("--json", action="store_true", help="Output in JSON format")
    _add_scope_args(p_ld)
    p_ld.set_defaults(func=list_docs)

    # search
    p_s = sub.add_parser("search", help="Search help documents")
    p_s.add_argument("keyword", help="Search keyword")
    p_s.add_argument("-p", "--product",
                     help="Restrict to a product code (strongly recommended: it enables the "
                          "server-side categoryId filter and fuses that product's llms.txt index, "
                          "which is far more precise than a global full-text query). Without -p "
                          "only the full-text leg runs (~1-2 s); the all-product index scan "
                          "(one request per product index) happens only when that leg fails or is "
                          "switched off")
    p_s.add_argument("-n", "--max-results", type=int, default=20,
                     help="Max results (default 20, 0=unlimited). Both backends now answer a "
                          "single page sized by this value: doSearch (cn+zh) through its real "
                          "page-size parameter 'limit' (unscoped queries stay at one top-ranked "
                          "page of up to 20 items), search.json (intl, and cn+en) through "
                          "'pageSize', clamped to 2..200")
    p_s.add_argument("--json", action="store_true",
                     help="Output in JSON format (source field: fulltext=full-text leg, index=index leg, both=hit by both legs)")
    _add_scope_args(p_s)
    p_s.set_defaults(func=search_docs)

    # read
    p_r = sub.add_parser("read", help="Read a document body")
    p_r.add_argument("url", help="Doc URL (the .md suffix is appended automatically)")
    p_r.add_argument("-l", "--max-lines", type=int, default=0, help="Max lines (0=unlimited)")
    p_r.add_argument("--raw", action="store_true", help="Output as-is even when the response is HTML (by default it is intercepted with advice)")
    # A document URL already names its site and its language, so only --site is offered here and
    # it is used solely to warn about a site/URL mismatch (never to rewrite the URL).
    _add_scope_args(p_r, with_lang=False)
    p_r.set_defaults(func=read_doc)

    # read-product
    p_rp = sub.add_parser("read-product", help="Read a product's raw llms.txt")
    p_rp.add_argument("product", help="Product code")
    p_rp.add_argument("-l", "--max-lines", type=int, default=0, help="Max lines")
    _add_scope_args(p_rp)
    p_rp.set_defaults(func=read_product_llms)

    # api-products
    p_ap = sub.add_parser("api-products", help="List OpenAPI product codes and versions")
    p_ap.add_argument("keyword", nargs="?", default=None, help="Filter by code/name/group")
    p_ap.add_argument("-n", "--max-results", type=int, default=50, help="Max entries (default 50)")
    p_ap.add_argument("--json", action="store_true", help="Output in JSON format")
    # The metadata legs have no site or language dimension, but they do honour --timeout.
    p_ap.add_argument("--timeout", type=int, default=0, metavar="SECONDS", help=_TIMEOUT_HELP)
    p_ap.set_defaults(func=api_products)

    # api-list
    p_al = sub.add_parser("api-list", help="List all APIs of a product")
    p_al.add_argument("product", help="OpenAPI product code (case-insensitive, e.g. actiontrail/ecs)")
    p_al.add_argument("keyword", nargs="?", default=None, help="Filter by API name/title/summary")
    p_al.add_argument("-V", "--api-version", default=None, help="API version (defaults to the product's defaultVersion)")
    p_al.add_argument("-n", "--max-results", type=int, default=50, help="Max entries (default 50)")
    p_al.add_argument("--json", action="store_true", help="Output in JSON format")
    p_al.add_argument("--timeout", type=int, default=0, metavar="SECONDS", help=_TIMEOUT_HELP)
    p_al.set_defaults(func=api_list)

    # api-info
    p_ai = sub.add_parser("api-info", help="Structured contract of a single API (parameters/error codes/RAM permission points)")
    p_ai.add_argument("product", help="OpenAPI product code (case-insensitive)")
    p_ai.add_argument("api", help="API name (case-insensitive, e.g. LookupEvents)")
    p_ai.add_argument("-V", "--api-version", default=None, help="API version (defaults to the product's defaultVersion)")
    p_ai.add_argument("--json", action="store_true", help="Dump the full raw metadata JSON (including response structures/examples)")
    p_ai.add_argument("--timeout", type=int, default=0, metavar="SECONDS", help=_TIMEOUT_HELP)
    p_ai.set_defaults(func=api_info)

    args = parser.parse_args()
    # N3: record the deadline override before the first request of any leg is issued.
    set_cli_timeout(getattr(args, "timeout", 0))
    # N8: honour the per-run result-cache choice.
    set_result_cache(not getattr(args, "no_result_cache", False))
    try:
        code = args.func(args)
    except _UsageError as e:
        # An invalid site/language combination is reported with the full list of supported values
        # and never issues a request; the server would silently answer in English instead.
        print(str(e), file=sys.stderr)
        return 2
    return code if isinstance(code, int) else 0


if __name__ == "__main__":
    sys.exit(main())
