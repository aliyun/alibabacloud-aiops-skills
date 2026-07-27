from __future__ import annotations

import argparse
import json
import shlex
import sys

from .agent_card_cache import read_agent_card_record, write_agent_card_record
from .agent_discovery import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_TIMEOUT_SEC,
    AgentDiscoveryError,
    discover_agents,
)
from .config import endpoint_for_agent_id, normalize_agenthub_endpoint
from .credentials import prepare_agenthub_credentials
from .diagnostics import diagnose
from .hosted_skill_catalog import (
    DEFAULT_TIMEOUT_SEC as HOSTED_SKILL_DEFAULT_TIMEOUT_SEC,
    HostedSkillCatalogError,
    list_hosted_skills,
)
from .input_store import allocate_input, consume_input, validate_input_text
from .profile_commands import configure_ak_profile, configure_oauth_profile
from .proxy import ProxyCommand, ProxyResult, ProxyRunner
from .session import resolve_session_id
from .trusted_actions import issue_follow_action, resolve_follow_action

try:
    from scripts.a2a_proxy.references import task_store as a2a_task_store
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.references import task_store as a2a_task_store


TASK_OPERATIONS = {"check_task", "cancel_task", "view_task", "continue_task"}
TOKEN_REQUIRED_PROXY_OPERATIONS = {
    "send_message",
    "send_streaming_message",
    "check_task",
    "follow_task",
    "cancel_task",
    "continue_task",
}
FOLLOW_WINDOW_SEC = 180
FOLLOW_INTERVAL_SEC = 5


def _add_input_group(parser: argparse.ArgumentParser, kind: str, *, required: bool = True) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(f"--{kind}-stdin", action="store_true", help=f"从标准输入读取{kind}")
    group.add_argument(f"--{kind}-input-id", help=f"消费 allocate_input 创建的一次性 {kind} handle")


def _add_session(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "稳定的本地客户端会话 ID；Codex/Qwen/Claude Code 可自动解析，"
            "自分配客户端必须保留客户端前缀，并让生成后缀与 SKILL_SESSION_ID 一致"
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agenthub", description="阿里云 AgentHub skill 命令行")
    subcommands = parser.add_subparsers(dest="command", required=True)

    allocate = subcommands.add_parser("allocate_input", help="创建一次性私有输入 handle")
    allocate.add_argument("--kind", required=True, choices=["message", "keyword"])

    discover = subcommands.add_parser("discover_agents", help="按用户意图召回候选远程 Agent")
    _add_input_group(discover, "keyword")
    discover.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    discover.add_argument("--timeout-sec", type=float, default=DEFAULT_TIMEOUT_SEC)

    list_hosted = subcommands.add_parser(
        "list_hosted_skills",
        help="列出阿里云官方托管技能目录",
    )
    list_hosted.add_argument(
        "--timeout-sec",
        type=float,
        default=HOSTED_SKILL_DEFAULT_TIMEOUT_SEC,
    )

    send = subcommands.add_parser("send", help="把用户原文发送给已选择的远程 A2A Agent")
    _add_input_group(send, "message")
    send.add_argument("--agent-id", required=True)
    _add_session(send)
    send.add_argument("--sync", action="store_true", help="强制使用同步 SendMessage")

    list_tasks = subcommands.add_parser("list_tasks", help="列出当前会话的本地任务与安全续接动作")
    list_tasks.add_argument("--agent-id", default=None)
    _add_session(list_tasks)
    list_tasks.add_argument("--include-delivered", action="store_true")

    for name in ("check_task", "cancel_task", "view_task"):
        task_cmd = subcommands.add_parser(name, help=f"按 taskId 执行 {name}")
        task_cmd.add_argument("--task-id", required=True)
        _add_session(task_cmd)

    continue_task = subcommands.add_parser("continue_task", help="继续 INPUT_REQUIRED 任务")
    continue_task.add_argument("--task-id", required=True)
    _add_input_group(continue_task, "message")
    _add_session(continue_task)

    follow = subcommands.add_parser("follow_task", help="使用可信 action reference 续接审批任务")
    follow.add_argument("--session-id", required=True, help="当前客户端会话 ID，仅用于交叉验证")
    follow.add_argument("--task-id", required=True, help="预期任务 ID，仅用于交叉验证")
    follow.add_argument("--action-ref", required=True)

    subcommands.add_parser("diagnose", help="检查本地 AgentHub skill 前置条件")
    auth_init = subcommands.add_parser("auth_init", help="初始化并验证中国站 AgentHub 凭证")
    auth_init.add_argument("--refresh", action="store_true", help="强制刷新 AgentHub token 缓存")
    auth_init.add_argument(
        "--credential-source",
        choices=("aliyun_cli", "agenthub_oauth"),
        help="首次初始化时明确选择 aliyun CLI 或 AgentHub OAuth",
    )

    configure_ak = subcommands.add_parser("configure_ak", help="在本地交互终端写入 AgentHub AK profile")
    configure_ak.add_argument("--profile", default="aliyun_agenthub")

    configure_oauth = subcommands.add_parser("configure_oauth", help="在本地交互终端完成 AgentHub OAuth 授权")
    configure_oauth.add_argument("--profile", default="aliyun_agenthub_oauth")
    configure_oauth.add_argument("--no-browser", action="store_true")
    configure_oauth.add_argument("--timeout-sec", type=int, default=300)
    return parser


def _resolve_input(args, kind: str, stderr) -> str | None:
    try:
        input_id = getattr(args, f"{kind}_input_id", None)
        if input_id:
            return consume_input(input_id, kind)
        if getattr(args, f"{kind}_stdin", False):
            return validate_input_text(sys.stdin.read(), kind)
    except (OSError, RuntimeError, ValueError) as exc:
        stderr.write(f"{kind} 输入无效: {exc}\n")
        return None
    return None


def _resolve_session_or_error(explicit_session_id: str | None, stderr) -> str | None:
    session_id = resolve_session_id(explicit_session_id)
    if session_id:
        return session_id
    stderr.write(
        "缺少会话 ID：请在受支持客户端中运行；QoderWork 或其他自分配客户端必须首次生成 "
        "SKILL_SESSION_ID=<32-char-lowercase-hex>，再将完整业务 ID 固定派生为 "
        "qoderwork-${SKILL_SESSION_ID} 或 <client-name>-${SKILL_SESSION_ID}；不要删除客户端前缀。\n"
    )
    return None


def _run_credential_preflight(
    stdout,
    credential_preparer,
    *,
    refresh: bool = False,
    credential_source: str | None = None,
):
    prepare_kwargs = {"refresh": refresh}
    if credential_source is not None:
        prepare_kwargs["credential_source"] = credential_source
    result = credential_preparer(**prepare_kwargs)
    message = getattr(result, "message", "")
    if message:
        stdout.write(message)
        if not message.endswith("\n"):
            stdout.write("\n")
        stdout.flush()
    return result


def _credential_exit_code(
    credential_preparer,
    stdout,
    *,
    refresh: bool = False,
    credential_source: str | None = None,
) -> int:
    result = _run_credential_preflight(
        stdout,
        credential_preparer,
        refresh=refresh,
        credential_source=credential_source,
    )
    if getattr(result, "ok", False):
        return 0
    return int(getattr(result, "exit_code", 1) or 1)


def _trusted_route(agent_id: str, endpoint: str | None = None) -> tuple[str, str]:
    derived = endpoint_for_agent_id(agent_id) if endpoint is None else endpoint
    return agent_id, normalize_agenthub_endpoint(derived, agent_id=agent_id)


def _lookup_task_record(session_id: str, task_id: str | None, stderr):
    if not task_id:
        stderr.write("缺少 taskId。\n")
        return None
    try:
        a2a_task_store.validate_path_id(task_id, "task_id")
        matches = []
        for namespace_session, agent_id in a2a_task_store.list_namespaces(session_id):
            for record in a2a_task_store.list_records(
                namespace_session,
                agent_id,
                include_delivered=True,
            ):
                if record.get("taskId") == task_id:
                    matches.append(record)
        if not matches:
            return None
        routes = {
            (record.get("agentId"), record.get("endpoint"))
            for record in matches
        }
        if len(routes) != 1:
            stderr.write(
                f"当前会话中 taskId {task_id} 对应多个 Agent，拒绝猜测路由。\n"
            )
            return None
        return max(
            matches,
            key=lambda record: (
                record.get("stateRevision", -1),
                record.get("updatedAt", ""),
            ),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        stderr.write(f"taskId 无效: {exc}\n")
        return None


def _route_from_task_record(record) -> tuple[str, str]:
    return _trusted_route(record["agentId"], record["endpoint"])


def _resolve_task_agent(args, session_id: str, stderr) -> tuple[str, str] | None:
    record = _lookup_task_record(session_id, args.task_id, stderr)
    try:
        if record:
            return _route_from_task_record(record)
    except (KeyError, TypeError, ValueError) as exc:
        stderr.write(f"不可信的 AgentHub 路由: {exc}\n")
        return None
    stderr.write(f"未在当前会话找到任务 {args.task_id}；请确认仍在原会话中。\n")
    return None


def _resolve_continue_task_agent(args, session_id: str, stderr) -> tuple[str, str] | None:
    record = _lookup_task_record(session_id, args.task_id, stderr)
    if not record:
        stderr.write("continue_task 仅适用于当前会话的 input_required 任务。\n")
        return None
    state = record.get("activeState") or record.get("archiveState")
    if state != "input_required":
        stderr.write(f"任务 {args.task_id} 当前状态为 {state}，不能 continue_task。\n")
        return None
    try:
        return _route_from_task_record(record)
    except (KeyError, TypeError, ValueError) as exc:
        stderr.write(f"任务记录包含不可信路由: {exc}\n")
        return None


def _card_event(result: ProxyResult) -> dict | None:
    for event in result.control_events:
        if (
            isinstance(event, dict)
            and event.get("v") == 1
            and event.get("type") == "agent_card"
            and type(event.get("supportsStreaming")) is bool
            and event.get("rpcPath") == "/rpc"
            and set(event) == {"v", "type", "supportsStreaming", "rpcPath"}
        ):
            return event
    return None


def _send_operation_from_card(supports_streaming: bool, stdout) -> str:
    if supports_streaming:
        return "send_streaming_message"
    stdout.write("远程 Agent Card 未声明支持流式响应，使用 send_message。\n")
    stdout.flush()
    return "send_message"


def _choose_send_operation(
    endpoint: str,
    agent_id: str,
    session_id: str,
    proxy_runner: ProxyRunner,
    stdout,
    stderr,
    *,
    sync: bool = False,
) -> tuple[str, str, str] | None:
    if sync:
        return "send_message", endpoint, "/rpc"
    try:
        cached_card = read_agent_card_record(session_id, agent_id, endpoint)
    except (OSError, RuntimeError, ValueError) as exc:
        stderr.write(f"Agent Card 本地缓存不安全或不可读: {exc}\n")
        return None
    if cached_card:
        return (
            _send_operation_from_card(cached_card.supports_streaming, stdout),
            endpoint,
            "/rpc",
        )
    result = proxy_runner.run_capture(
        ProxyCommand(
            operation="get_agent_card",
            endpoint=endpoint,
            agent_id=agent_id,
            session_id=session_id,
        )
    )
    if result.returncode != 0:
        stderr.write("Agent Card 检查失败，停止发送。\n")
        return None

    event = _card_event(result)
    if event is None:
        stderr.write("Agent Card 未返回可信控制事件，停止发送。\n")
        return None
    supports_streaming = event["supportsStreaming"]
    rpc_path = event["rpcPath"]
    try:
        write_agent_card_record(
            session_id,
            agent_id,
            endpoint,
            result.stdout,
            supports_streaming,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        stderr.write(f"Agent Card 本地缓存写入失败: {exc}\n")
        return None
    return (
        _send_operation_from_card(supports_streaming, stdout),
        endpoint,
        rpc_path,
    )


def _matching_pending_record(session_id: str, agent_id: str, endpoint: str, event: dict) -> dict | None:
    if event.get("type") != "task_state" or event.get("state") != "auth_required":
        return None
    try:
        trusted_endpoint = normalize_agenthub_endpoint(endpoint, agent_id=agent_id)
        records = a2a_task_store.list_records(session_id, agent_id)
    except (OSError, RuntimeError, ValueError):
        return None
    for record in records:
        if record.get("activeState") != a2a_task_store.STATE_PENDING:
            continue
        if record.get("taskId") != event.get("taskId"):
            continue
        if record.get("hitlRound") != event.get("hitlRound"):
            continue
        try:
            recorded_endpoint = normalize_agenthub_endpoint(record.get("endpoint"), agent_id=agent_id)
        except ValueError:
            continue
        if recorded_endpoint == trusted_endpoint:
            return record
    return None


def _follow_action_command(record: dict, action_ref: str) -> str:
    session_id = a2a_task_store.validate_path_id(record.get("sessionId"), "session_id")
    task_id = a2a_task_store.validate_path_id(record.get("taskId"), "task_id")
    return (
        f"follow_task --session-id {shlex.quote(session_id)} "
        f"--task-id {shlex.quote(task_id)} --action-ref {action_ref}"
    )


def _emit_follow_actions(events, session_id: str, agent_id: str, endpoint: str, stdout) -> None:
    emitted: set[str] = set()
    for event in events or ():
        if not isinstance(event, dict):
            continue
        record = _matching_pending_record(session_id, agent_id, endpoint, event)
        if record is None:
            continue
        try:
            action_ref = issue_follow_action(record)
        except ValueError:
            continue
        if action_ref in emitted:
            continue
        emitted.add(action_ref)
        stdout.write(f"{_follow_action_command(record, action_ref)}\n")
    stdout.flush()


def _matching_notification_record(
    session_id: str,
    agent_id: str,
    endpoint: str,
    task_id: str,
    local_state: str,
) -> dict | None:
    try:
        trusted_endpoint = normalize_agenthub_endpoint(endpoint, agent_id=agent_id)
        records = a2a_task_store.list_records(session_id, agent_id)
    except (OSError, RuntimeError, ValueError):
        return None
    for record in records:
        if record.get("taskId") != task_id or record.get("activeState") != local_state:
            continue
        try:
            recorded_endpoint = normalize_agenthub_endpoint(record.get("endpoint"), agent_id=agent_id)
        except ValueError:
            continue
        if recorded_endpoint == trusted_endpoint:
            return record
    return None


def _write_input_required_record(record: dict, stdout) -> None:
    task_id = record.get("taskId")
    if not isinstance(task_id, str) or not task_id:
        return
    stdout.write(f"input_required taskId={task_id}\n")
    prompt = record.get("prompt")
    if isinstance(prompt, str) and prompt:
        stdout.write(f"{prompt}\n")


def _emit_task_notifications(events, session_id: str, agent_id: str, endpoint: str, stdout) -> None:
    emitted: set[str] = set()
    for event in events or ():
        if not isinstance(event, dict) or event.get("type") != "task_notifications":
            continue
        for item in event.get("inputRequired") or ():
            if not isinstance(item, dict):
                continue
            task_id = item.get("taskId")
            if not isinstance(task_id, str) or not task_id or task_id in emitted:
                continue
            record = _matching_notification_record(
                session_id,
                agent_id,
                endpoint,
                task_id,
                a2a_task_store.STATE_INPUT_REQUIRED,
            )
            if record is None:
                continue
            _write_input_required_record(record, stdout)
            emitted.add(task_id)
    stdout.flush()


def _run_and_handle_events(command: ProxyCommand, proxy_runner, stdout) -> int:
    exit_code = proxy_runner.run(command)
    events = getattr(proxy_runner, "last_control_events", ())
    _emit_follow_actions(
        events,
        command.session_id,
        command.agent_id,
        command.endpoint,
        stdout,
    )
    _emit_task_notifications(
        events,
        command.session_id,
        command.agent_id,
        command.endpoint,
        stdout,
    )
    return int(exit_code or 0)


def _write_non_pending_task(record: dict, stdout) -> bool:
    state = record.get("activeState") or record.get("archiveState")
    task_id = record.get("taskId")
    if not isinstance(state, str) or not state or not isinstance(task_id, str) or not task_id:
        return False
    if state == a2a_task_store.STATE_INPUT_REQUIRED:
        _write_input_required_record(record, stdout)
    else:
        stdout.write(f"{state} taskId={task_id}\n")
    return True


def _list_task_actions(session_id: str, agent_ids: list[str], include_delivered: bool, stdout) -> None:
    emitted = 0
    for agent_id in agent_ids:
        try:
            records = a2a_task_store.list_records(
                session_id,
                agent_id,
                include_delivered=include_delivered,
            )
        except (OSError, RuntimeError, ValueError):
            continue
        for record in records:
            if record.get("activeState") != a2a_task_store.STATE_PENDING:
                emitted += int(_write_non_pending_task(record, stdout))
                continue
            try:
                action_ref = issue_follow_action(record)
            except ValueError:
                continue
            stdout.write(f"{_follow_action_command(record, action_ref)}\n")
            emitted += 1
    if emitted == 0:
        stdout.write("当前会话没有本地任务。\n")
    stdout.flush()


def _diagnostic_tuple(item) -> tuple[str, str, str]:
    if isinstance(item, dict):
        return str(item.get("name", "")), str(item.get("status", "")).upper(), str(item.get("detail", ""))
    if isinstance(item, tuple) and len(item) == 3:
        return str(item[0]), str(item[1]).upper(), str(item[2])
    return (
        str(getattr(item, "name", "")),
        str(getattr(item, "status", "")).upper(),
        str(getattr(item, "detail", "")),
    )


def main(
    argv=None,
    proxy_runner=None,
    stdout=None,
    stderr=None,
    discovery_fetcher=None,
    credential_preparer=None,
    hosted_skill_fetcher=None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = _build_parser().parse_args(argv)

    if args.command == "list_hosted_skills":
        try:
            response = list_hosted_skills(
                timeout_sec=args.timeout_sec,
                fetch_json=hosted_skill_fetcher,
            )
        except HostedSkillCatalogError as exc:
            stderr.write(f"实时托管能力目录不可用: {exc}\n")
            return 1
        stdout.write(json.dumps(response.to_dict(), ensure_ascii=False, indent=2) + "\n")
        stdout.flush()
        return 0

    proxy_runner = proxy_runner or ProxyRunner()
    credential_preparer = credential_preparer or prepare_agenthub_credentials

    if args.command == "allocate_input":
        try:
            allocation = allocate_input(args.kind)
        except (OSError, RuntimeError, ValueError) as exc:
            stderr.write(f"创建输入 handle 失败: {exc}\n")
            return 1
        stdout.write(json.dumps(allocation, ensure_ascii=False, separators=(",", ":")) + "\n")
        stdout.flush()
        return 0

    resolved_input = None
    input_kind = None
    if args.command == "discover_agents":
        input_kind = "keyword"
    elif args.command in {"send", "continue_task"}:
        input_kind = "message"
    if input_kind:
        resolved_input = _resolve_input(args, input_kind, stderr)
        if resolved_input is None:
            return 2

    if args.command == "discover_agents":
        try:
            response = discover_agents(
                resolved_input,
                max_results=args.max_results,
                timeout_sec=args.timeout_sec,
                fetch_json=discovery_fetcher,
            )
        except (AgentDiscoveryError, ValueError) as exc:
            stderr.write(f"发现候选远程 Agent 失败: {exc}\n")
            return 1
        stdout.write(json.dumps(response.to_dict(), ensure_ascii=False, indent=2) + "\n")
        stdout.flush()
        return 0

    if args.command == "diagnose":
        failed = False
        for raw in diagnose():
            name, status, detail = _diagnostic_tuple(raw)
            stdout.write(f"{status}\t{name}\t{detail}\n")
            failed = failed or status == "FAIL"
        stdout.flush()
        return 1 if failed else 0

    if args.command == "auth_init":
        return _credential_exit_code(
            credential_preparer,
            stdout,
            refresh=args.refresh,
            credential_source=args.credential_source,
        )
    if args.command == "configure_ak":
        return configure_ak_profile(profile_name=args.profile, stdout=stdout, stderr=stderr)
    if args.command == "configure_oauth":
        return configure_oauth_profile(
            profile_name=args.profile,
            no_browser=args.no_browser,
            timeout_sec=args.timeout_sec,
            stdout=stdout,
            stderr=stderr,
        )

    if args.command == "follow_task":
        try:
            asserted_session_id = a2a_task_store.validate_path_id(args.session_id, "session_id")
            asserted_task_id = a2a_task_store.validate_path_id(args.task_id, "task_id")
            record = resolve_follow_action(args.action_ref)
            if (
                record.get("sessionId") != asserted_session_id
                or record.get("taskId") != asserted_task_id
            ):
                raise ValueError("follow action 与 session/task 交叉断言不匹配")
            session_id = record["sessionId"]
            agent_id, endpoint = _trusted_route(record["agentId"], record["endpoint"])
            task_id = record["taskId"]
        except (KeyError, TypeError, ValueError) as exc:
            stderr.write(f"follow action 已失效或不可信: {exc}\n")
            return 2
        card_result = proxy_runner.run_capture(
            ProxyCommand(
                operation="get_agent_card",
                endpoint=endpoint,
                agent_id=agent_id,
                session_id=session_id,
            )
        )
        event = _card_event(card_result) if card_result.returncode == 0 else None
        operation = "subscribe_task" if event and event["supportsStreaming"] else "follow_task"
        credential_result = _run_credential_preflight(stdout, credential_preparer)
        if not getattr(credential_result, "ok", False):
            return int(getattr(credential_result, "exit_code", 1) or 1)
        try:
            current = resolve_follow_action(args.action_ref)
            if (
                current.get("sessionId") != asserted_session_id
                or current.get("taskId") != asserted_task_id
            ):
                raise ValueError("follow action 与 session/task 交叉断言不匹配")
            current_identity = (
                current["sessionId"],
                current["agentId"],
                current["endpoint"],
                current["taskId"],
                current["hitlRound"],
            )
            original_identity = (
                record["sessionId"],
                record["agentId"],
                record["endpoint"],
                record["taskId"],
                record["hitlRound"],
            )
            if current_identity != original_identity:
                raise ValueError("approval task round changed")
        except (KeyError, TypeError, ValueError) as exc:
            stderr.write(f"follow action 在执行前已失效: {exc}\n")
            return 2
        command = ProxyCommand(
            operation=operation,
            endpoint=endpoint,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            rpc_path="/rpc",
            follow_window_sec=FOLLOW_WINDOW_SEC,
            follow_interval_sec=FOLLOW_INTERVAL_SEC,
        )
        return _run_and_handle_events(command, proxy_runner, stdout)

    session_id = _resolve_session_or_error(getattr(args, "session_id", None), stderr)
    if not session_id:
        return 2

    if args.command == "list_tasks":
        if args.agent_id:
            try:
                agent_ids = [_trusted_route(args.agent_id)[0]]
            except ValueError as exc:
                stderr.write(f"agentId 无效: {exc}\n")
                return 2
        else:
            try:
                agent_ids = sorted(
                    agent_id
                    for _namespace_session, agent_id in a2a_task_store.list_namespaces(session_id)
                )
            except (OSError, RuntimeError, ValueError) as exc:
                stderr.write(f"会话任务列表无效: {exc}\n")
                return 2
        _list_task_actions(session_id, agent_ids, args.include_delivered, stdout)
        return 0

    if args.command == "send":
        try:
            agent_id, endpoint = _trusted_route(args.agent_id)
        except ValueError as exc:
            stderr.write(f"agentId 无效: {exc}\n")
            return 2
        selected = _choose_send_operation(
            endpoint,
            agent_id,
            session_id,
            proxy_runner,
            stdout,
            stderr,
            sync=bool(args.sync),
        )
        if selected is None:
            return 1
        operation, selected_endpoint, rpc_path = selected
        credential_result = _run_credential_preflight(stdout, credential_preparer)
        if not getattr(credential_result, "ok", False):
            return int(getattr(credential_result, "exit_code", 1) or 1)
        return _run_and_handle_events(
            ProxyCommand(
                operation=operation,
                endpoint=selected_endpoint,
                agent_id=agent_id,
                session_id=session_id,
                message=resolved_input,
                rpc_path=rpc_path,
            ),
            proxy_runner,
            stdout,
        )

    if args.command in TASK_OPERATIONS:
        resolved = (
            _resolve_continue_task_agent(args, session_id, stderr)
            if args.command == "continue_task"
            else _resolve_task_agent(args, session_id, stderr)
        )
        if not resolved:
            return 1
        agent_id, endpoint = resolved
        if args.command in TOKEN_REQUIRED_PROXY_OPERATIONS:
            credential_result = _run_credential_preflight(stdout, credential_preparer)
            if not getattr(credential_result, "ok", False):
                return int(getattr(credential_result, "exit_code", 1) or 1)
        return _run_and_handle_events(
            ProxyCommand(
                operation=args.command,
                endpoint=endpoint,
                agent_id=agent_id,
                session_id=session_id,
                message=resolved_input,
                task_id=args.task_id,
            ),
            proxy_runner,
            stdout,
        )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
