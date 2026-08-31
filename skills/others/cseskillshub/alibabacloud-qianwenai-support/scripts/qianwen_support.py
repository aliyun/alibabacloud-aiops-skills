#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QianWen Support Ticket Manager

Dual-backend: qianwen CLI (preferred) or direct HTTP API (fallback).
Auto-detects backend: uses CLI if installed & authenticated, else API.

API backend:
    POST https://cli.qianwenai.com/data/v2/api.json
    Body: {"product":"Workorder","action":"<Action>","region":"cn-beijing","params":{...}}
    Auth: Bearer token (env QIANWEN_ACCESS_TOKEN or macOS keychain)

CLI backend:
    qianwen support <list|view|create|reply|close|rate> --format json

Usage:
    python3 qianwen_support.py list [--page N] [--page-size N]
    python3 qianwen_support.py view --ticket-id <id>
    python3 qianwen_support.py categories
    python3 qianwen_support.py create --category-id <id> --description <text>
    python3 qianwen_support.py reply --ticket-id <id> --message <text>
    python3 qianwen_support.py close --ticket-id <id>
    python3 qianwen_support.py rate --ticket-id <id> --rating <0-2> [--comment <text>]
    python3 qianwen_support.py doctor
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
import uuid
from typing import Optional, Dict, Any, List, Tuple

# Per-run session id for platform-level tracing (Observability).
# Honour SKILL_SESSION_ID when it is already a valid 32-char lowercase hex
# string; otherwise generate a fresh one so all requests of one run share it.
def _get_session_id() -> str:
    env = os.environ.get("SKILL_SESSION_ID", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{32}", env):
        return env
    return uuid.uuid4().hex


_SESSION_ID = _get_session_id()
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-qianwenai-support/{_SESSION_ID}"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API_BASE = "https://cli.qianwenai.com/data/v2/api.json"
PRODUCT = "Workorder"
REGION = "cn-beijing"
SITE_TAG = "qianwenai"
PRODUCT_CODES = ["bailian"]
CLI_TIMEOUT = 30  # seconds per CLI invocation
API_TIMEOUT = 30  # seconds per HTTP request

# Hardcoded category fallback (mirrors qianwen CLI built-in list).
# Used when API backend cannot fetch dynamic categories.
# Source: qianwen CLI v1.4.0 built-in Ks constant + web frontend behavior.
#
# IMPORTANT: Model categories are real ticket categories (create tickets).
# App categories match the web frontend behavior: they do NOT create tickets;
# the frontend redirects users to the app's official site (helpUrl).
BUILTIN_CATEGORIES = [
    {"id": "582262", "category": "Model > Billing", "group": "Model",
     "type": "ticket"},
    {"id": "582263", "category": "Model > Invoice", "group": "Model",
     "type": "ticket"},
    {"id": "582264", "category": "Model > Feature Inquiry", "group": "Model",
     "type": "ticket"},
    {"id": "582265", "category": "Model > API/SDK", "group": "Model",
     "type": "ticket"},
    {"id": "582266", "category": "Model > Tool Integration", "group": "Model",
     "type": "ticket"},
    {"id": "miaowu", "category": "App > MiaoWu", "group": "App",
     "type": "redirect", "helpUrl": "https://meoo.com"},
    {"id": "wanxiang", "category": "App > WanXiang", "group": "App",
     "type": "redirect", "helpUrl": "https://tongyi.aliyun.com/wan"},
    {"id": "wukong", "category": "App > WuKong", "group": "App",
     "type": "redirect", "helpUrl": "https://wukong.dingtalk.com"},
    {"id": "qianwen", "category": "App > QianWen", "group": "App",
     "type": "redirect", "helpUrl": "https://www.qianwen.com"},
    {"id": "qoder", "category": "App > Qoder", "group": "App",
     "type": "redirect", "helpUrl": "https://qoder.com"},
    {"id": "qoderwork", "category": "App > QoderWork", "group": "App",
     "type": "redirect", "helpUrl": "https://qoder.com"},
]

# Terminal statuses – reply/close MUST be refused for these
TERMINAL_STATUSES = {"closed", "resolved", "confirmed"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(data: dict) -> None:
    """Print structured JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _err(msg: str) -> None:
    """Print warning to stderr (kept for observability)."""
    print(f"[WARN] {msg}", file=sys.stderr)


def _read_keychain_token() -> Optional[str]:
    """Read QianWen access token from macOS keychain."""
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-s", "qianwen-cli", "-a", "cli_credentials", "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        cred = json.loads(result.stdout.strip())
        return cred.get("access_token")
    except Exception:
        return None


def _read_testconfig_token() -> Optional[str]:
    """Read token from evals/config/testconfig.json (platform eval fallback)."""
    try:
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "evals", "config", "testconfig.json"
        )
        if not os.path.exists(cfg_path):
            return None
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg.get("credentials") or {}).get("qianwen_access_token") or None
    except Exception:
        return None


def _resolve_token() -> Optional[str]:
    """Resolve Bearer token: env var > macOS keychain > evals testconfig."""
    token = os.environ.get("QIANWEN_ACCESS_TOKEN", "").strip()
    if token:
        return token
    kc = _read_keychain_token()
    if kc:
        return kc
    return _read_testconfig_token()


# ---------------------------------------------------------------------------
# API Backend
# ---------------------------------------------------------------------------

class ApiBackend:
    """Direct HTTP API to QianWen platform."""

    def __init__(self, token: str):
        self.token = token

    def _call(self, action: str, params: Optional[Dict] = None) -> Dict:
        body = {
            "product": PRODUCT,
            "action": action,
            "region": REGION,
            "params": params or {}
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            API_BASE,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": _USER_AGENT
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": e.read().decode("utf-8", errors="replace")}
        except Exception as e:
            return {"error": str(e)}

        if str(raw.get("code")) != "200":
            return {"error": raw.get("message", "Unknown error"), "code": raw.get("code")}
        return raw.get("data", {})

    # -- Ticket operations --

    def list_tickets(self, page: int = 1, page_size: int = 10) -> Dict:
        result = self._call("ListTickets", {
            "Params": json.dumps({"CustomerLimit": False}),
            "Page": page,
            "PageSize": page_size,
            "IndependentSiteTag": SITE_TAG
        })
        if "error" in result:
            return {"backend": "api", "action": "list", **result}
        items = []
        data_info = (result.get("Data") or {}).get("DataInfo") or []
        for t in data_info:
            items.append({
                "id": t.get("vid", ""),
                "title": t.get("title", ""),
                "status": t.get("statTicketBiz", ""),
                "createdAt": t.get("createTime", 0)
            })
        pagination = (result.get("Data") or {}).get("Pagination") or {}
        return {
            "backend": "api",
            "action": "list",
            "tickets": items,
            "page": pagination.get("Page", page),
            "pageSize": pagination.get("Limit", page_size),
            "total": (result.get("Data") or {}).get("Total", 0)
        }

    def get_categories(self) -> Dict:
        # API GetCategoryTreeByProductCodes only returns top-level nodes
        # without children. Use built-in category list as reliable source.
        return {
            "backend": "api",
            "action": "categories",
            "categories": BUILTIN_CATEGORIES,
            "source": "builtin"
        }

    def suggest_category(self, content: str) -> Dict:
        """AI-powered category suggestion based on issue description."""
        import uuid as _uuid
        trace_id = _uuid.uuid4().hex[:16]
        result = self._call("SuggestCategoryNew", {
            "Channel": "ticket_pc_v2",
            "Content": content,
            "EventMethod": "input",
            "AnswerView": 5,
            "TraceId": trace_id,
            "BusinessId": trace_id,
            "SceneCategoryMode": "KNOWLEDGE"
        })
        if "error" in result:
            return {"backend": "api", "action": "suggest_category", **result}
        data = result.get("Data") or {}
        suggestions = []
        for c in (data.get("SuggestCategoryDTOS") or []):
            suggestions.append({
                "categoryId": c.get("CategoryId"),
                "categoryName": c.get("CategoryName", ""),
                "productName": c.get("ProductName", ""),
                "score": c.get("Score", 0)
            })
        return {
            "backend": "api",
            "action": "suggest_category",
            "suggestedType": data.get("SuggestServiceType", ""),
            "suggestions": suggestions
        }

    def get_ticket(self, ticket_id: str) -> Dict:
        # Region "7" is the QianWen workorder region (not a standard cloud region)
        result = self._call("GetTicket", {
            "TicketId": ticket_id,
            "Region": "7"
        })
        if "error" in result:
            return {"backend": "api", "action": "view", **result}
        # Check for API-level errors (Code 2011 = no permission / not found)
        code = result.get("Code", result.get("code", 0))
        if code not in (0, "0") and not result.get("Success", True):
            return {
                "backend": "api",
                "action": "view",
                "error": result.get("Message", "API error"),
                "code": code,
                "ticketId": ticket_id
            }
        # Response structure: Data.Values.vid, Data.Values.title, etc.
        data = result.get("Data") or {}
        vals = data.get("Values") or data
        status_obj = vals.get("status") or {}
        status = status_obj.get("label", "") if isinstance(status_obj, dict) else str(status_obj)
        return {
            "backend": "api",
            "action": "view",
            "ticket": {
                "id": vals.get("vid", ticket_id),
                "title": vals.get("title", ""),
                "status": status,
                "description": vals.get("description", ""),
                "category": vals.get("product_name", ""),
                "createdAt": vals.get("gmt_create", 0)
            }
        }

    def list_messages(self, ticket_id: str, page: int = 1, page_size: int = 20) -> Dict:
        result = self._call("ListEnhancedMessage", {
            "TicketId": ticket_id,
            "PageLimit": page_size
        })
        if "error" in result:
            return {"backend": "api", "action": "messages", **result}
        msgs = []
        data = result.get("Data") or {}
        msg_list = data.get("DataInfo") or data.get("MessageList") or []
        for m in msg_list:
            msgs.append({
                "sender": m.get("senderRole", ""),
                "content": m.get("content", ""),
                "createdAt": m.get("createTime", 0)
            })
        return {
            "backend": "api",
            "action": "messages",
            "ticketId": ticket_id,
            "messages": msgs,
            "total": data.get("Total", len(msgs))
        }

    def create_ticket(self, category_id: str, description: str,
                      accept_language: str = "zh_CN") -> Dict:
        result = self._call("CreateTicketNew", {
            "CategoryId": category_id,
            "Severity": "1",
            "Description": description,
            "AcceptLanguage": accept_language,
            "ServiceLinkVersion": "V2",
            "DirectLabor": "true",
            "IfServiceQuota": "true",
            "IndependentSiteTag": SITE_TAG
        })
        data = result.get("Data")
        if isinstance(data, dict):
            ticket_id = data.get("vid", data.get("Vid", ""))
            status = data.get("statTicketBiz", "created")
        elif isinstance(data, str) and data.strip():
            # API returns the new ticket id as a plain string
            ticket_id = data.strip()
            status = "created"
        else:
            ticket_id = ""
            status = "created"
        return {
            "backend": "api",
            "action": "create",
            "ticketId": ticket_id,
            "status": status
        }

    def reply_ticket(self, ticket_id: str, content: str) -> Dict:
        result = self._call("CreateMessage", {
            "TicketId": ticket_id,
            "Content": content
        })
        return {
            "backend": "api",
            "action": "reply",
            "ticketId": ticket_id,
            "success": result.get("Code", -1) == 0 or result.get("Success", False)
        }

    def close_ticket(self, ticket_id: str) -> Dict:
        result = self._call("CancelTicket", {
            "TicketId": ticket_id
        })
        return {
            "backend": "api",
            "action": "close",
            "ticketId": ticket_id,
            "success": result.get("Code", -1) == 0 or result.get("Success", False)
        }

    def rate_ticket(self, ticket_id: str, rating: int, comment: str = "") -> Dict:
        post_param: Dict[str, Any] = {
            "ticketId": ticket_id,
            "satisfaction": rating
        }
        if comment:
            post_param["suggest"] = comment
        result = self._call("SubmitCard", {
            "PostParam": json.dumps(post_param)
        })
        # Handle "already rated" (Code 1000) gracefully
        code = result.get("Code", result.get("code", -1))
        if code == 1000:
            return {
                "backend": "api",
                "action": "rate",
                "ticketId": ticket_id,
                "rating": rating,
                "success": False,
                "alreadyRated": True,
                "message": result.get("Message", "Ticket already finished or rated")
            }
        return {
            "backend": "api",
            "action": "rate",
            "ticketId": ticket_id,
            "rating": rating,
            "success": code == 0 or result.get("Success", False)
        }

    def doctor(self) -> Dict:
        token_ok = bool(self.token)
        result = self._call("ListTickets", {
            "Params": json.dumps({"CustomerLimit": False}),
            "Page": 1,
            "PageSize": 1,
            "IndependentSiteTag": SITE_TAG
        })
        api_ok = "error" not in result
        return {
            "backend": "api",
            "action": "doctor",
            "cli_available": False,
            "api_endpoint": API_BASE,
            "token_present": token_ok,
            "api_reachable": api_ok,
            "auth_valid": token_ok and api_ok
        }


# ---------------------------------------------------------------------------
# CLI Backend
# ---------------------------------------------------------------------------

class CliBackend:
    """Wraps `qianwen` CLI commands."""

    def _run(self, args: List[str]) -> Dict:
        cmd = ["qianwen"] + args + ["--format", "json"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT
            )
            stdout = result.stdout.strip()
            if not stdout:
                return {"error": "No output from CLI", "stderr": result.stderr.strip(),
                        "exit_code": result.returncode}
            return json.loads(stdout)
        except subprocess.TimeoutExpired:
            return {"error": f"CLI timed out after {CLI_TIMEOUT}s"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from CLI", "raw": stdout[:500]}
        except FileNotFoundError:
            return {"error": "qianwen CLI not found"}

    def list_tickets(self, page: int = 1, page_size: int = 10) -> Dict:
        raw = self._run(["support", "list",
                         "--page", str(page), "--page-size", str(page_size)])
        if "error" in raw:
            return {"backend": "cli", "action": "list", **raw}
        # CLI returns tickets directly
        tickets = raw if isinstance(raw, list) else raw.get("tickets", [raw])
        return {"backend": "cli", "action": "list", "tickets": tickets,
                "page": page, "pageSize": page_size}

    def get_categories(self) -> Dict:
        raw = self._run(["support", "create", "--list-categories"])
        if "error" in raw:
            return {"backend": "cli", "action": "categories", **raw}
        cats = raw if isinstance(raw, list) else raw.get("categories", [])
        return {"backend": "cli", "action": "categories", "categories": cats}

    def get_ticket(self, ticket_id: str) -> Dict:
        raw = self._run(["support", "view", ticket_id])
        if "error" in raw:
            return {"backend": "cli", "action": "view", **raw}
        # CLI returns {"ticket": {...}, "messages": [...], ...}
        return {"backend": "cli", "action": "view", **raw}

    def list_messages(self, ticket_id: str, page: int = 1,
                      page_size: int = 20) -> Dict:
        # CLI view includes messages
        raw = self._run(["support", "view", ticket_id])
        if "error" in raw:
            return {"backend": "cli", "action": "messages", **raw}
        messages = raw.get("messages", []) if isinstance(raw, dict) else []
        return {"backend": "cli", "action": "messages", "ticketId": ticket_id,
                "messages": messages}

    def create_ticket(self, category_id: str, description: str,
                      accept_language: str = "zh_CN") -> Dict:
        raw = self._run(["support", "create",
                         "--category-id", category_id,
                         "--description", description,
                         "--accept-language", accept_language])
        if "error" in raw:
            return {"backend": "cli", "action": "create", **raw}
        return {"backend": "cli", "action": "create", "ticket": raw}

    def reply_ticket(self, ticket_id: str, content: str) -> Dict:
        raw = self._run(["support", "reply", ticket_id, "--message", content])
        if "error" in raw:
            return {"backend": "cli", "action": "reply", **raw}
        return {"backend": "cli", "action": "reply", "ticketId": ticket_id,
                "success": True, "detail": raw}

    def close_ticket(self, ticket_id: str) -> Dict:
        raw = self._run(["support", "close", ticket_id, "--yes"])
        if "error" in raw:
            return {"backend": "cli", "action": "close", **raw}
        return {"backend": "cli", "action": "close", "ticketId": ticket_id,
                "success": True}

    def rate_ticket(self, ticket_id: str, rating: int, comment: str = "") -> Dict:
        args = ["support", "rate", ticket_id,
                "--rating", str(rating)]
        if comment:
            args += ["--comment", comment]
        raw = self._run(args)
        if "error" in raw:
            return {"backend": "cli", "action": "rate", **raw}
        # CLI returns alreadyRated info when ticket is already rated
        already_rated = raw.get("alreadyRated", False)
        return {
            "backend": "cli",
            "action": "rate",
            "ticketId": ticket_id,
            "rating": rating,
            "success": not already_rated,
            "alreadyRated": already_rated,
            "detail": raw
        }

    def doctor(self) -> Dict:
        cli_path = shutil.which("qianwen")
        cli_ok = cli_path is not None
        version = ""
        auth_ok = False
        env_diag: Dict[str, Any] = {}
        if cli_ok:
            try:
                vr = subprocess.run(["qianwen", "version"],
                                    capture_output=True, text=True, timeout=5)
                # qianwen version outputs JSON: {"version": "1.4.0"}
                try:
                    version = json.loads(vr.stdout.strip()).get("version", "")
                except (json.JSONDecodeError, ValueError):
                    version = vr.stdout.strip().split("\n")[0] if vr.stdout else ""
            except Exception:
                pass
            try:
                ar = subprocess.run(["qianwen", "auth", "status", "--format", "json"],
                                    capture_output=True, text=True, timeout=5)
                auth_data = json.loads(ar.stdout.strip()) if ar.stdout else {}
                auth_ok = auth_data.get("authenticated", False)
            except Exception:
                pass
            # Environment diagnostics (Phase 0 item 4)
            try:
                dr = subprocess.run(["qianwen", "doctor", "--format", "json"],
                                    capture_output=True, text=True, timeout=CLI_TIMEOUT)
                if dr.stdout.strip():
                    env_diag = json.loads(dr.stdout.strip())
            except Exception:
                env_diag = {"error": "qianwen doctor unavailable"}
        return {
            "backend": "cli",
            "action": "doctor",
            "cli_available": cli_ok,
            "cli_path": cli_path or "",
            "cli_version": version,
            "cli_authenticated": auth_ok,
            "environment": env_diag,
            "api_fallback": not cli_ok or not auth_ok
        }


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def select_backend(prefer: str = "auto") -> Tuple[Any, str]:
    """Select backend. 'auto' = CLI first, API fallback."""
    if prefer == "api":
        token = _resolve_token()
        if not token:
            return None, ("API mode requested but no token found. "
                          "Run `qianwen auth login` (browser device flow) or "
                          "set QIANWEN_ACCESS_TOKEN environment variable.")
        return ApiBackend(token), "api"

    # auto or cli: try CLI first
    cli_path = shutil.which("qianwen")
    if cli_path:
        # Verify CLI is authenticated
        try:
            r = subprocess.run(
                ["qianwen", "auth", "status", "--format", "json"],
                capture_output=True, text=True, timeout=5
            )
            auth = json.loads(r.stdout.strip()) if r.stdout else {}
            if auth.get("authenticated"):
                return CliBackend(), "cli"
            _err("CLI not authenticated, falling back to API")
        except Exception as e:
            _err(f"CLI auth check failed: {e}")

    # Fallback to API
    token = _resolve_token()
    if token:
        _err("Using API backend (CLI unavailable or not authenticated)")
        return ApiBackend(token), "api"

    return None, ("No backend available. Login options: "
                  "(1) CLI: run `qianwen auth login` (browser device flow); "
                  "(2) API: set QIANWEN_ACCESS_TOKEN environment variable. "
                  "If qianwen CLI is not installed: `npm install -g @qianwenai/qianwen-cli`.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="QianWen Support Ticket Manager")
    parser.add_argument("--backend", choices=["auto", "cli", "api"], default="auto",
                        help="Backend selection (default: auto)")
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="List support tickets")
    p_list.add_argument("--page", type=int, default=1)
    p_list.add_argument("--page-size", type=int, default=10)

    # view
    p_view = sub.add_parser("view", help="View ticket detail + messages")
    p_view.add_argument("--ticket-id", required=True)

    # categories
    sub.add_parser("categories", help="List ticket categories")

    # suggest-category
    p_suggest = sub.add_parser("suggest-category", help="Suggest category by issue description")
    p_suggest.add_argument("--content", required=True, help="Issue description text")

    # create
    p_create = sub.add_parser("create", help="Create a new ticket")
    p_create.add_argument("--category-id", required=True)
    p_create.add_argument("--description", required=True)
    p_create.add_argument("--accept-language", default="zh_CN")

    # reply
    p_reply = sub.add_parser("reply", help="Reply to a ticket")
    p_reply.add_argument("--ticket-id", required=True)
    p_reply.add_argument("--message", required=True)

    # close
    p_close = sub.add_parser("close", help="Close/cancel a ticket")
    p_close.add_argument("--ticket-id", required=True)

    # rate
    p_rate = sub.add_parser("rate", help="Rate a resolved ticket")
    p_rate.add_argument("--ticket-id", required=True)
    p_rate.add_argument("--rating", type=int, required=True, choices=[0, 1, 2])
    p_rate.add_argument("--comment", default="")

    # doctor
    sub.add_parser("doctor", help="Run diagnostics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    backend, mode = select_backend(args.backend)
    if backend is None:
        _out({"error": mode, "backend": "none"})
        sys.exit(1)

    # Pre-flight: terminal status check for reply/close only
    # Rating is allowed on resolved/closed tickets (verified via CLI)
    if args.command in ("reply", "close"):
        tid = args.ticket_id
        view = backend.get_ticket(tid)
        ticket = view.get("ticket", {})
        status = str(ticket.get("status", "")).lower()
        if status in TERMINAL_STATUSES:
            _out({
                "error": f"Ticket is in terminal status ({status}), cannot {args.command}",
                "ticketId": tid,
                "status": status,
                "backend": mode
            })
            sys.exit(1)

    # Dispatch
    if args.command == "list":
        result = backend.list_tickets(args.page, args.page_size)
    elif args.command == "view":
        result = backend.get_ticket(args.ticket_id)
        # Also fetch messages
        msgs = backend.list_messages(args.ticket_id)
        result["messages"] = msgs.get("messages", [])
    elif args.command == "categories":
        result = backend.get_categories()
    elif args.command == "suggest-category":
        if isinstance(backend, ApiBackend):
            result = backend.suggest_category(args.content)
        else:
            # CLI mode: use categories list + simple keyword match
            result = backend.get_categories()
            result["action"] = "suggest_category"
            result["note"] = "CLI mode does not support AI suggestion; use API mode for smart matching"
    elif args.command == "create":
        result = backend.create_ticket(
            args.category_id, args.description, args.accept_language)
    elif args.command == "reply":
        result = backend.reply_ticket(args.ticket_id, args.message)
    elif args.command == "close":
        result = backend.close_ticket(args.ticket_id)
    elif args.command == "rate":
        result = backend.rate_ticket(args.ticket_id, args.rating, args.comment)
    elif args.command == "doctor":
        result = backend.doctor()
    else:
        result = {"error": f"Unknown command: {args.command}"}

    result["backend"] = mode
    _out(result)


if __name__ == "__main__":
    main()
