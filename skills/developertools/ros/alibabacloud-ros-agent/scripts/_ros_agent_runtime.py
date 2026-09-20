# Managed worker, loopback manager, and CLI command source shard.
# Loaded by ros_agent.py into its shared module namespace; do not execute directly.
# ruff: noqa: F821,N802 -- names are shared; HTTP handler names are framework-defined.

def _run_start_chat(
    args: argparse.Namespace,
    workspace: pathlib.Path,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
) -> Dict[str, Any]:
    return _consume_start_chat(args, workspace, prompt, client_context, attachments)


def _consume_start_chat(
    args: argparse.Namespace,
    workspace: pathlib.Path,
    prompt: str,
    client_context: Optional[str],
    attachments: List[Dict[str, str]],
    *,
    summary_mode: Optional[str] = None,
    on_payload: Optional[Any] = None,
    worker_role: str = "primary",
    permission_response: Optional[Dict[str, Any]] = None,
    can_reconnect: Optional[Any] = None,
) -> Dict[str, Any]:
    summary = StreamSummary(args.session_id, mode=summary_mode or args.mode)
    diagnostics = []  # type: List[str]
    stream_cursor = None  # type: Optional[str]
    stream_identity = None  # type: Optional[str]
    stream_sequence = 0
    pending_applied_stream_event_id = None  # type: Optional[str]
    reconnect_attempt = 0

    def boundary_is_immediate() -> bool:
        if summary.state in TERMINAL_STATES:
            return False
        if summary.input_required is not None and not summary.input_required_from_pending:
            return True
        if summary.assistant_final or (summary.mode == "normal" and summary.state == "input-required"):
            return True
        return (
            worker_role == "sideband"
            and isinstance(permission_response, dict)
            and isinstance(summary.permission_ack, dict)
            and _permission_response_is_acknowledged(permission_response, summary.permission_ack)
        )

    def process_event(event: Dict[str, Any], invocation_id: Optional[str] = None) -> bool:
        nonlocal stream_cursor, stream_identity, stream_sequence, pending_applied_stream_event_id
        bootstrap = event.get("bootstrap")
        bootstrap_session_id = None  # type: Optional[str]
        if isinstance(bootstrap, dict):
            if bootstrap.get("invocationId") != invocation_id:
                return True
            nested = bootstrap.get("event")
            if not isinstance(nested, dict) or not isinstance(nested.get("data"), dict):
                return True
            candidate = bootstrap.get("sessionId")
            if isinstance(candidate, str) and candidate:
                bootstrap_session_id = candidate

        payload = event.get("payload")
        raw = event.get("raw")
        if not isinstance(payload, dict):
            summary.malformed_event_count += 1
            if isinstance(raw, str) and raw:
                diagnostics.append(raw)
            return True
        payload_session_id = _find_first(payload, "contextId", "context_id", "SessionId")
        if (
            isinstance(payload_session_id, str)
            and payload_session_id
            and bootstrap_session_id is not None
            and payload_session_id != bootstrap_session_id
        ):
            raise BridgeError("stream_session_mismatch", "StartChat bootstrap returned a different SessionId.")
        observed_session_id = (
            payload_session_id
            if isinstance(payload_session_id, str) and payload_session_id
            else bootstrap_session_id
        )
        if (
            isinstance(observed_session_id, str)
            and observed_session_id
            and summary.session_id
            and observed_session_id != summary.session_id
        ):
            raise BridgeError("stream_session_mismatch", "StartChat returned a different SessionId.")
        if can_reconnect is not None and can_reconnect() is False:
            if isinstance(observed_session_id, str) and observed_session_id:
                summary.session_id = observed_session_id
            if on_payload is not None:
                on_payload(None, payload, summary, False)
            return False
        event_id = event.get("id")
        heartbeat = str(payload.get("object", "")).lower() in {"heartbeat", "keepalive"}
        if heartbeat:
            summary.apply(payload)
            return True
        if event_id is None:
            raise BridgeError("missing_stream_event_id", "StartChat returned a business event without an SSE ID.")
        identity, sequence = parse_stream_event_id(event_id)
        if stream_identity is not None and identity != stream_identity:
            raise BridgeError(
                "stream_event_identity_mismatch",
                "StartChat returned an event from a different stream during reconnect.",
            )
        if stream_identity is None:
            stream_identity = identity
        if sequence <= stream_sequence:
            return True

        already_applied = pending_applied_stream_event_id == event_id
        if not already_applied:
            if not (isinstance(payload_session_id, str) and payload_session_id) and bootstrap_session_id is not None:
                summary.session_id = bootstrap_session_id
            summary.apply(payload)
            if not isinstance(summary.session_id, str) or not summary.session_id:
                raise BridgeError(
                    "missing_stream_session_id",
                    "StartChat did not provide the SessionId required for reconnect.",
                )
            pending_applied_stream_event_id = event_id

        if on_payload is not None and on_payload(event_id, payload, summary, already_applied) is False:
            return False
        stream_cursor = event_id
        stream_sequence = sequence
        pending_applied_stream_event_id = None
        return True

    def result() -> Dict[str, Any]:
        return summary.to_result(0, "\n".join(diagnostics))

    while True:
        reconnecting = stream_cursor is not None
        if reconnecting and can_reconnect is not None and can_reconnect() is False:
            return {"ok": True, "state": "worker-stopped", "_workerStopped": True}
        immediate = False
        transport_error = None  # type: Optional[BridgeError]
        cli_return_code = 0
        cli_stderr = ""
        cli_failure_seen = False

        if getattr(args, "transport", "aliyun_cli") == "code":
            parameters = (
                build_reconnect_start_chat_parameters(str(summary.session_id), stream_cursor)
                if reconnecting
                else build_start_chat_parameters(args, prompt, client_context, attachments)
            )
            response = None
            try:
                response = _open_code_request(
                    "StartChat",
                    parameters,
                    str(args.endpoint),
                    args.profile,
                    args.region_id,
                    args.aliyun_path,
                    int(args.connect_timeout),
                    int(args.read_timeout),
                    args.user_agent,
                    credential_source=getattr(args, "credential_source", None),
                )
                content_type = str(response.headers.get("Content-Type", "")).lower()
                if "text/event-stream" not in content_type:
                    raw = response.read(MAX_DIAGNOSTIC_BYTES + 1)
                    detail = sanitize_text(raw.decode("utf-8", "replace"), 2000)
                    raise BridgeError(
                        "stream_failed",
                        detail or "Alibaba Cloud ROS StartChat did not return an SSE stream.",
                        True,
                    )
                for event in iter_sse_payloads(_response_text_lines(response)):
                    if not process_event(event):
                        return {"ok": True, "state": "worker-stopped", "_workerStopped": True}
                    if boundary_is_immediate():
                        immediate = True
                        break
            except KeyboardInterrupt as exc:
                raise BridgeError(
                    "interrupted",
                    "StartChat was interrupted locally; remote cancellation is not confirmed.",
                ) from exc
            except BridgeError as exc:
                transport_error = exc
            except Exception as exc:
                transport_error = BridgeError(
                    "stream_failed", "Alibaba Cloud ROS StartChat stream ended unexpectedly.", True
                )
                transport_error.__cause__ = exc
            finally:
                if response is not None:
                    response.close()
        else:
            command = (
                build_reconnect_command(args, str(summary.session_id), stream_cursor)
                if reconnecting
                else build_command(args, prompt, client_context, attachments)
            )
            invocation_id = (
                uuid.uuid4().hex if getattr(args, "aliyun_cli_execution_mode", "local") == "remote" else None
            )
            with tempfile.TemporaryDirectory() as bootstrap_root, tempfile.TemporaryFile(mode="w+b") as stderr_file:
                process_environment = None  # type: Optional[Dict[str, str]]
                ack_path = None  # type: Optional[pathlib.Path]
                if invocation_id is not None:
                    ack_path = pathlib.Path(bootstrap_root) / "bootstrap-ack.json"
                    process_environment = dict(os.environ)
                    process_environment[REMOTE_BOOTSTRAP_INVOCATION_ENV] = invocation_id
                    process_environment[REMOTE_BOOTSTRAP_ACK_FILE_ENV] = str(ack_path)
                    process_environment[REMOTE_BOOTSTRAP_PROTOCOL_ENV] = REMOTE_BOOTSTRAP_CAPABILITY
                try:
                    process = subprocess.Popen(
                        command,
                        cwd=str(workspace),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=stderr_file,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=process_environment,
                    )
                except OSError as exc:
                    process = None
                    transport_error = BridgeError("cli_start_failed", "Alibaba Cloud CLI could not be started.", True)
                    transport_error.__cause__ = exc
                if process is not None:
                    assert process.stdout is not None
                    try:
                        for event in iter_cli_plugin_payloads(process.stdout):
                            if event.get("cliFailure") is True:
                                cli_failure_seen = True
                                raw = event.get("raw")
                                if isinstance(raw, str) and raw:
                                    diagnostics.append(raw)
                                continue
                            bootstrap = event.get("bootstrap")
                            if isinstance(bootstrap, dict) and (
                                bootstrap.get("invocationId") != invocation_id
                                or not isinstance(bootstrap.get("event"), dict)
                                or not isinstance(bootstrap["event"].get("id"), str)
                                or not isinstance(bootstrap["event"].get("data"), dict)
                            ):
                                continue
                            if not process_event(event, invocation_id):
                                _stop_process(process)
                                return {"ok": True, "state": "worker-stopped", "_workerStopped": True}
                            if (
                                isinstance(bootstrap, dict)
                                and ack_path is not None
                                and isinstance(event.get("id"), str)
                            ):
                                _atomic_json(
                                    ack_path,
                                    {
                                        "invocationId": invocation_id,
                                        "eventId": event["id"],
                                        "committed": True,
                                    },
                                )
                            if boundary_is_immediate():
                                immediate = True
                                _stop_process(process)
                                break
                        cli_return_code = process.wait()
                    except KeyboardInterrupt as exc:
                        _stop_process(process)
                        raise BridgeError(
                            "interrupted",
                            "StartChat was interrupted locally; remote cancellation is not confirmed.",
                        ) from exc
                    except BridgeError as exc:
                        _stop_process(process)
                        transport_error = exc
                    except BaseException as exc:
                        _stop_process(process)
                        transport_error = BridgeError(
                            "stream_failed", "Alibaba Cloud CLI StartChat output ended unexpectedly.", True
                        )
                        transport_error.__cause__ = exc
                    finally:
                        process.stdout.close()
                stderr_file.seek(0)
                cli_stderr = stderr_file.read(MAX_DIAGNOSTIC_BYTES).decode("utf-8", "replace")

        if immediate:
            return result()
        if transport_error is None and cli_return_code == 0 and cli_failure_seen:
            raise BridgeError(
                "aliyun_cli_failed",
                sanitize_text("\n".join(diagnostics[-8:]), 3000) or "Alibaba Cloud CLI StartChat failed.",
            )
        if transport_error is None and cli_return_code != 0:
            diagnostic_text = "\n".join(diagnostics[-8:])
            if is_retryable_cli_failure(cli_return_code, cli_stderr, diagnostic_text):
                transport_error = BridgeError(
                    "aliyun_cli_failed",
                    sanitize_text(cli_stderr, 3000) or "Alibaba Cloud CLI StartChat was interrupted.",
                    True,
                )
            else:
                return summary.to_result(cli_return_code, cli_stderr or diagnostic_text)
        if transport_error is not None:
            if not transport_error.retryable:
                raise transport_error
            if stream_cursor is None or not isinstance(summary.session_id, str) or not summary.session_id:
                raise BridgeError(
                    "missing_recovery_anchor",
                    "StartChat was interrupted before a complete recovery anchor was committed.",
                ) from transport_error
        elif summary.state in TERMINAL_STATES:
            return result()
        elif stream_cursor is None or not isinstance(summary.session_id, str) or not summary.session_id:
            raise BridgeError(
                "missing_recovery_anchor",
                "StartChat ended before a complete recovery anchor was committed.",
            )

        if can_reconnect is not None and can_reconnect() is False:
            return {"ok": True, "state": "worker-stopped", "_workerStopped": True}
        reconnect_attempt += 1
        time.sleep(min(0.1 * (2 ** min(reconnect_attempt - 1, 6)), MAX_RECONNECT_BACKOFF_SECONDS))


def run_chat(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace(args.cwd)
    prompt = read_prompt(workspace, args.prompt_file)
    client_context = load_client_context(workspace, args.client_context_file)
    attachments = load_attachments(workspace, args.attachments_file)
    return _run_start_chat(args, workspace, prompt, client_context, attachments)


def run_respond(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace(args.cwd)
    query, response = load_permission_query(
        workspace,
        args.input_file,
        args.decision,
        args.session_id,
        args.mode,
    )
    # Keep the Query as the sole control payload. ClientContext and attachments
    # would cause the ROS gateway to wrap or augment the text before A2A delivery.
    result = _run_start_chat(args, workspace, query, None, [])
    result["permissionResponse"] = response
    return _bound_result(result)


def _stop_process(process: Any) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _spawn_worker(job_id: str, request: Dict[str, Any]) -> int:
    root, job_path, _spool = _job_paths(job_id)
    transient_environment = request.pop("_transientEnvironment", {})
    if not isinstance(transient_environment, dict):
        raise BridgeError("invalid_input", "The transient remote CLI environment is invalid.")
    worker_environment = _remote_cli_subprocess_environment(
        request.get("aliyunCLIForwardEnv", []),
        transient_environment,
    )
    request_token = uuid.uuid4().hex
    request_path = root / ("request-{}.json".format(request_token))
    _atomic_json(request_path, request)
    canonical_job_id = uuid.UUID(job_id).hex
    command = [
        sys.executable,
        str(pathlib.Path(__file__).resolve()),
        "_worker",
        "--job-id",
        canonical_job_id,
        "--request-token",
        request_token,
    ]
    log_path = root / "worker.log"
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    if log_path.exists() and log_path.stat().st_size > MAX_DIAGNOSTIC_BYTES:
        with log_path.open("wb"):
            pass
    try:
        with log_path.open("ab", buffering=0) as log:
            if os.name != "nt":
                os.chmod(str(log_path), 0o600)
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                env=worker_environment,
                start_new_session=os.name != "nt",
                creationflags=creationflags,
            )
    except OSError as exc:
        with contextlib.suppress(OSError):
            request_path.unlink()
        request_seq = int(request.get("requestSeq") or 0)
        error = BridgeError("worker_start_failed", "The StartChat worker could not be started.", True)
        worker_token = request.get("workerToken")
        if request.get("workerRole") == "sideband" and isinstance(worker_token, str):
            _fail_sideband_job(job_id, request_seq, worker_token, error, 0)
        else:
            _fail_job(job_id, request_seq, error, 0)
        raise BridgeError("worker_start_failed", "The StartChat worker could not be started.", True) from exc
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if request.get("workerRole") == "sideband":
            job["sidebandWorkerPid"] = process.pid
            job["sidebandWorkerStartedAt"] = int(time.time())
        else:
            job["workerPid"] = process.pid
            job["workerStartedAt"] = int(time.time())
        _atomic_json(job_path, job)
    return process.pid


def _request_from_job(job: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    legacy_forward_env = (
        list(DEFAULT_REMOTE_CLI_FORWARD_ENV)
        if job.get("transport", "aliyun_cli") == "aliyun_cli"
        and job.get("aliyunCLIExecutionMode") == "remote"
        else []
    )
    return {
        "requestSeq": job["activeRequestSeq"],
        "workspace": job["workspace"],
        "prompt": prompt,
        "mode": job["mode"],
        "summaryMode": job.get("conversationMode") or job["mode"],
        "endpoint": job["endpoint"],
        # Jobs created before transport selection existed used the native CLI.
        "transport": job.get("transport", "aliyun_cli"),
        "aliyunCLIExecutionMode": job.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE),
        "aliyunCLIForwardEnv": job.get("aliyunCLIForwardEnv", legacy_forward_env),
        "sessionId": job.get("sessionId"),
        "regionId": job.get("regionId"),
        "profile": job.get("profile"),
        "credentialSource": job.get("credentialSource"),
        "noThinking": job.get("noThinking") is True,
        "connectTimeout": job.get("connectTimeout", 10),
        "readTimeout": job.get("readTimeout", DEFAULT_READ_TIMEOUT_SECONDS),
        "aliyunPath": job.get("aliyunPath", "aliyun"),
        "userAgent": job["userAgent"],
        "clientContext": None,
        "attachments": [],
        "streamCursor": None,
    }


def _start_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _trusted_manager_workspace(str(payload.get("workspace") or ""))
    prompt = payload.get("prompt")
    mode = payload.get("mode")
    endpoint = payload.get("endpoint")
    transport = payload.get("transport", DEFAULT_TRANSPORT)
    cli_execution_mode = payload.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    default_forward_env = list(DEFAULT_REMOTE_CLI_FORWARD_ENV) if cli_execution_mode == "remote" else []
    forward_env = _validate_remote_cli_forward_env_names(payload.get("aliyunCLIForwardEnv", default_forward_env))
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise BridgeError("invalid_input", "The StartChat prompt is empty or too large.")
    if mode not in SUPPORTED_AGENT_MODES:
        raise BridgeError("invalid_input", "The ROS Agent mode is invalid.")
    if not isinstance(endpoint, str):
        raise BridgeError("invalid_input", "The ROS endpoint is invalid.")
    _endpoint_kind(endpoint)
    if transport not in SUPPORTED_TRANSPORTS:
        raise BridgeError("invalid_input", "The ROS transport is invalid.")
    if cli_execution_mode not in SUPPORTED_ALIYUN_CLI_EXECUTION_MODES:
        raise BridgeError("invalid_input", "The aliyun CLI execution mode is invalid.")
    if transport != "aliyun_cli" and cli_execution_mode != DEFAULT_ALIYUN_CLI_EXECUTION_MODE:
        raise BridgeError("invalid_input", "The aliyun CLI execution mode requires the aliyun_cli transport.")
    if forward_env and not (transport == "aliyun_cli" and cli_execution_mode == "remote"):
        raise BridgeError("invalid_input", "Forwarded CLI environment requires remote aliyun CLI execution.")
    if transport == "aliyun_cli" and cli_execution_mode == "remote":
        if _endpoint_kind(endpoint) != "aliyun":
            raise BridgeError("invalid_input", "Remote aliyun CLI execution requires a public aliyuncs.com endpoint.")
        if payload.get("profile"):
            raise BridgeError("invalid_input", "Remote aliyun CLI execution does not accept a local Profile.")
        if payload.get("clientContext") is not None:
            raise BridgeError("unsupported_input", "The ROS CLI plugin does not support ClientContext.")
    aliyun_path = str(payload.get("aliyunPath") or "aliyun")
    if transport == "aliyun_cli":
        resolve_aliyun(aliyun_path)
    else:
        _load_code_sdk()
    job_id = uuid.uuid4().hex
    skill_session_id = uuid.uuid4().hex
    user_agent = _skill_user_agent(skill_session_id)
    root, job_path, spool = _job_paths(job_id)
    _secure_directory(root)
    spool.touch()
    if os.name != "nt":
        os.chmod(str(spool), 0o600)
    job = {
        "schemaVersion": JOB_SCHEMA_VERSION,
        "jobId": job_id,
        "workspace": str(workspace),
        "mode": mode,
        "endpoint": endpoint,
        "transport": transport,
        "aliyunCLIExecutionMode": cli_execution_mode,
        "aliyunCLIForwardEnv": forward_env,
        "regionId": payload.get("regionId"),
        "profile": payload.get("profile"),
        "credentialSource": payload.get("credentialSource"),
        "noThinking": payload.get("noThinking") is True,
        "connectTimeout": int(payload.get("connectTimeout") or 10),
        "readTimeout": int(payload.get("readTimeout") or DEFAULT_READ_TIMEOUT_SECONDS),
        "aliyunPath": aliyun_path,
        "skillSessionId": skill_session_id,
        "userAgent": user_agent,
        "preferredLanguage": _preferred_language(prompt),
        "state": "submitted",
        "turn": 1,
        "activeRequestSeq": 1,
        "createdAt": int(time.time()),
        "turnStartedAt": int(time.time()),
        "artifacts": [],
    }  # type: Dict[str, Any]
    _atomic_json(job_path, job)
    request = _request_from_job(job, prompt)
    request["clientContext"] = payload.get("clientContext")
    request["attachments"] = payload.get("attachments") if isinstance(payload.get("attachments"), list) else []
    request["_transientEnvironment"] = _remote_cli_environment_from_payload(job, payload)
    worker_pid = _spawn_worker(job_id, request)
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": mode,
        "preferredLanguage": job["preferredLanguage"],
        "cursor": 0,
        "turn": 1,
        "workerPid": worker_pid,
    }


def _continue_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        prompt = payload.get("prompt")
        if not isinstance(prompt, str):
            prompt_file = payload.get("promptFile")
            if not isinstance(prompt_file, str):
                raise BridgeError("invalid_input", "continue requires a prompt file.")
            prompt = read_prompt(pathlib.Path(job["workspace"]), prompt_file)
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise BridgeError("invalid_input", "The continuation prompt is empty or too large.")
        if isinstance(job.get("workerPid"), int) and _pid_alive(job["workerPid"]):
            raise BridgeError("job_busy", "The current StartChat request is still running.", True)
        session_id = job.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise BridgeError("job_not_ready", "The ROS Agent job has not received a SessionId yet.", True)
        pending = job.get("inputRequired")
        if isinstance(pending, dict) and pending.get("kind") == "permission":
            raise BridgeError("input_response_mismatch", "A permission must be answered with respond, not continue.")
        pipeline_handoff = (
            job.get("mode") == "pipeline"
            and job.get("state") == "completed"
            and (job.get("normalHandoffReady") is True or job.get("conversationMode") == "normal")
        )
        if not isinstance(pending, dict) and job.get("state") != "turn-completed" and not pipeline_handoff:
            raise BridgeError(
                "input_response_mismatch", "The ROS Agent job is not waiting for a natural-language message."
            )
        cursor = len(_read_spool(spool))
        if job.get("state") == "turn-completed" or pipeline_handoff:
            job["turn"] = int(job.get("turn") or 1) + 1
            job["turnStartedAt"] = int(time.time())
            job.pop("finalText", None)
            job.pop("finalTextComplete", None)
        if pipeline_handoff:
            previous_task_id = job.pop("taskId", None)
            if isinstance(previous_task_id, str):
                history = job.setdefault("taskHistory", [])
                if previous_task_id not in history:
                    history.append(previous_task_id)
            job["conversationMode"] = "normal"
            job.pop("pipelineResult", None)
        job["activeRequestSeq"] = int(job.get("activeRequestSeq") or 0) + 1
        for key in ("streamCursor", "streamIdentity", "streamSequence"):
            job.pop(key, None)
        job["state"] = "submitted"
        job.pop("inputRequired", None)
        job.pop("error", None)
        job.pop("permissionAck", None)
        _atomic_json(job_path, job)
    request = _request_from_job(job, prompt)
    request["_transientEnvironment"] = _remote_cli_environment_from_payload(job, payload)
    worker_pid = _spawn_worker(job_id, request)
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": job["mode"],
        "conversationMode": job.get("conversationMode") or job["mode"],
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": cursor,
        "turn": int(job.get("turn") or 1),
        "sessionId": job["sessionId"],
        "workerPid": worker_pid,
    }


def _managed_permission_candidates(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []  # type: List[Dict[str, Any]]
    seen_input_ids = set()  # type: set
    values = [job.get("inputRequired")]
    pending_permissions = job.get("pendingPermissions")
    if isinstance(pending_permissions, list):
        values.extend(pending_permissions)
    for value in values:
        if not isinstance(value, dict) or value.get("kind") != "permission":
            continue
        input_id = value.get("inputId")
        if not isinstance(input_id, str) or not input_id or input_id in seen_input_ids:
            continue
        seen_input_ids.add(input_id)
        candidates.append(value)
    return candidates


def _select_managed_permission(job: Dict[str, Any], permission_ref: Any) -> Optional[Dict[str, Any]]:
    candidates = _managed_permission_candidates(job)
    if permission_ref is None:
        if len(candidates) > 1:
            raise BridgeError(
                "permission_selection_required",
                "Multiple permissions are waiting; respond with the permissionRef shown for the selected action.",
            )
        return candidates[0] if candidates else None
    if not isinstance(permission_ref, str) or not permission_ref:
        raise BridgeError("invalid_input", "permissionRef must be a non-empty string.")
    matches = [value for value in candidates if _permission_ref(value) == permission_ref]
    if len(matches) != 1:
        raise BridgeError("input_response_mismatch", "permissionRef does not match a pending permission.")
    return matches[0]


def _respond_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        session_id = job.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            raise BridgeError("job_not_ready", "The ROS Agent job has no SessionId.")
        decision = payload.get("decision")
        if not isinstance(decision, str) or decision not in PERMISSION_DECISIONS:
            raise BridgeError("invalid_input", "respond requires allow_once or deny.")
        response_mode = job.get("conversationMode") or job["mode"]
        pending = job.get("inputRequired")
        input_file = payload.get("inputFile")
        if isinstance(input_file, str):
            workspace = pathlib.Path(job["workspace"])
            query, response = load_permission_query(workspace, input_file, decision, session_id, response_mode)
        else:
            pending = _select_managed_permission(job, payload.get("permissionRef"))
            if pending is None:
                last_response = job.get("lastPermissionResponse")
                acknowledgement = job.get("permissionAck")
                if isinstance(last_response, dict) and decision == last_response.get("decision"):
                    if _permission_response_is_acknowledged(last_response, acknowledgement):
                        return {
                            "ok": True,
                            "jobId": job_id,
                            "state": "permission-responded",
                            "mode": job["mode"],
                            "preferredLanguage": job.get("preferredLanguage", "en"),
                            "cursor": len(_read_spool(spool)),
                            "turn": int(job.get("turn") or 1),
                            "sessionId": session_id,
                            "permissionResponse": last_response,
                            "permissionAck": acknowledgement,
                            "duplicate": True,
                        }
                    raise BridgeError("job_busy", "The permission response is already running.", True)
                if isinstance(last_response, dict):
                    raise BridgeError(
                        "input_response_mismatch",
                        "The permission response conflicts with the stored decision.",
                    )
                raise BridgeError("input_response_mismatch", "The ROS Agent job is not waiting for permission.")
            query, response = build_permission_query(pending, decision, session_id, response_mode)
        if not isinstance(pending, dict) or pending.get("kind") != "permission":
            last_response = job.get("lastPermissionResponse")
            acknowledgement = job.get("permissionAck")
            if response == last_response and _permission_response_is_acknowledged(response, acknowledgement):
                return {
                    "ok": True,
                    "jobId": job_id,
                    "state": "permission-responded",
                    "mode": job["mode"],
                    "preferredLanguage": job.get("preferredLanguage", "en"),
                    "cursor": len(_read_spool(spool)),
                    "turn": int(job.get("turn") or 1),
                    "sessionId": session_id,
                    "permissionResponse": response,
                    "permissionAck": acknowledgement,
                    "duplicate": True,
                }
            if isinstance(last_response, dict) and all(
                response.get(key) == last_response.get(key)
                for key in ("requestTaskId", "contextId", "inputId", "toolUseId")
            ):
                raise BridgeError(
                    "input_response_mismatch",
                    "The permission response conflicts with the stored decision.",
                )
            raise BridgeError("input_response_mismatch", "The ROS Agent job is not waiting for permission.")
        for key in ("requestTaskId", "contextId", "inputId", "toolUseId"):
            if response.get(key) != pending.get(key):
                raise BridgeError(
                    "input_response_mismatch", "The permission response does not match the pending input."
                )
        cursor = len(_read_spool(spool))
        primary_worker_alive = isinstance(job.get("workerPid"), int) and _pid_alive(job["workerPid"])
        sub_pipeline = pending.get("permissionClass") == "sub_pipeline"
        sideband = sub_pipeline
        worker_token = None  # type: Optional[str]
        if sideband:
            if job.get("mode") != "pipeline":
                raise BridgeError("input_response_mismatch", "A Sub Pipeline permission requires Pipeline mode.")
            if sub_pipeline and not primary_worker_alive:
                raise BridgeError(
                    "stream_detached",
                    "The parent Pipeline StartChat stream ended before its Sub Pipeline permission was answered.",
                    True,
                )
            if isinstance(job.get("sidebandWorkerToken"), str):
                raise BridgeError("job_busy", "A Pipeline permission response is already running.", True)
            worker_token = uuid.uuid4().hex
            job["sidebandWorkerToken"] = worker_token
            job["sidebandResponseInputId"] = response.get("inputId")
            job["sidebandResponse"] = pending
            job["state"] = "working"
            for key in ("sidebandStreamCursor", "sidebandStreamIdentity", "sidebandStreamSequence"):
                job.pop(key, None)
        else:
            if primary_worker_alive:
                raise BridgeError("job_busy", "The current StartChat request is still running.", True)
            job["activeRequestSeq"] = int(job.get("activeRequestSeq") or 0) + 1
            for key in ("streamCursor", "streamIdentity", "streamSequence"):
                job.pop(key, None)
            job["state"] = "submitted"
            job["permissionResponseInput"] = pending
        job["lastPermissionResponse"] = response
        remaining = [
            value
            for value in job.get("pendingPermissions", [])
            if isinstance(value, dict) and value.get("inputId") != response.get("inputId")
        ]
        job.pop("inputRequired", None)
        if remaining:
            job["pendingPermissions"] = remaining
            job["inputRequired"] = remaining[0]
        else:
            job.pop("pendingPermissions", None)
        job.pop("permissionAck", None)
        job.pop("sidebandError", None)
        job.pop("error", None)
        _atomic_json(job_path, job)
    request = _request_from_job(job, query)
    request["permissionResponse"] = response
    request["_transientEnvironment"] = _remote_cli_environment_from_payload(job, payload)
    if sideband:
        request["workerRole"] = "sideband"
        request["workerToken"] = worker_token
    worker_pid = _spawn_worker(job_id, request)
    return {
        "ok": True,
        "jobId": job_id,
        "state": "submitted",
        "mode": job["mode"],
        "preferredLanguage": job.get("preferredLanguage", "en"),
        "cursor": cursor,
        "turn": int(job.get("turn") or 1),
        "sessionId": session_id,
        "workerPid": worker_pid,
        "permissionResponse": response,
    }


def _run_stop_chat(job: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    if job.get("transport", "aliyun_cli") == "code":
        response = _open_code_request(
            "StopChat",
            {"AgentVersion": "V2", "SessionId": session_id},
            str(job.get("endpoint") or ""),
            job.get("profile") if isinstance(job.get("profile"), str) else None,
            job.get("regionId") if isinstance(job.get("regionId"), str) else None,
            str(job.get("aliyunPath") or "aliyun"),
            max(1, min(int(job.get("connectTimeout") or 10), 30)),
            int(STOP_REQUEST_TIMEOUT_SECONDS),
            str(job["userAgent"]),
            credential_source=(
                job.get("credentialSource") if job.get("credentialSource") == "profile" else None
            ),
            error_code="stop_chat_failed",
        )
        try:
            raw = response.read(MAX_DIAGNOSTIC_BYTES + 1)
        finally:
            response.close()
        if len(raw) > MAX_DIAGNOSTIC_BYTES:
            raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat response was too large.", True)
        stdout = raw.decode("utf-8", "replace")
    else:
        command = build_stop_command(job, session_id)
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_remote_cli_subprocess_environment(
                    job.get("aliyunCLIForwardEnv", []),
                    job.get("_transientEnvironment", {}),
                ),
                timeout=STOP_REQUEST_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BridgeError("stop_chat_failed", "Alibaba Cloud CLI could not complete StopChat.", True) from exc
        stdout = (completed.stdout or b"").decode("utf-8", "replace")
        stderr = (completed.stderr or b"").decode("utf-8", "replace")
        if completed.returncode != 0:
            raise BridgeError(
                "stop_chat_failed",
                sanitize_text(stderr, 2000) or "Alibaba Cloud ROS StopChat failed.",
                True,
            )
    try:
        value = json.loads(stdout)
    except ValueError as exc:
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned invalid JSON.", True) from exc
    if not isinstance(value, dict):
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned invalid JSON.", True)
    status = value.get("Status", value.get("status"))
    returned_session_id = value.get("SessionId", value.get("sessionId", value.get("session_id")))
    if status not in {"Stopped", "Stopping", "NoActiveStream", "Failed"}:
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned an unknown status.", True)
    if returned_session_id not in (None, session_id):
        raise BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat returned a different SessionId.")
    result = {"status": status, "sessionId": session_id}
    request_id = value.get("RequestId", value.get("requestId", value.get("request_id")))
    if isinstance(request_id, str) and request_id:
        result["requestId"] = request_id
    return result


def _claim_stop_dispatch(job_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    root, job_path, _spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("stopRequestedAt") is None:
            return None
        if isinstance(session_id, str) and session_id:
            existing = job.get("sessionId")
            if isinstance(existing, str) and existing and existing != session_id:
                return None
            job["sessionId"] = session_id
        effective_session_id = job.get("sessionId")
        if (
            not isinstance(effective_session_id, str)
            or not effective_session_id
            or job.get("stopDispatchStartedAt") is not None
        ):
            if isinstance(session_id, str) and session_id:
                _atomic_json(job_path, job)
            return None
        job["stopDispatchStartedAt"] = int(time.time())
        _atomic_json(job_path, job)
        return dict(job)


def _settle_stop_dispatch(
    job_id: str,
    stopped: Optional[Dict[str, Any]] = None,
    error: Optional[BridgeError] = None,
) -> Dict[str, Any]:
    root, job_path, _spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        job.setdefault("stopRequestedAt", int(time.time()))
        stop_status = stopped.get("status") if isinstance(stopped, dict) else None
        if error is not None or stop_status == "Failed" or stop_status not in {"Stopped", "Stopping", "NoActiveStream"}:
            job["stopStatus"] = "Failed"
            job["state"] = "failed"
            job["error"] = {
                "code": "stop_chat_failed",
                "message": sanitize_text(error.message, 2000)
                if isinstance(error, BridgeError)
                else "Alibaba Cloud ROS could not stop the active chat.",
                "retryable": True,
            }
        else:
            job["stopStatus"] = stop_status
            job["state"] = {
                "Stopped": "canceled",
                "Stopping": "canceling",
                "NoActiveStream": "not-active",
            }[stop_status]
            job.pop("inputRequired", None)
            job.pop("pendingPermissions", None)
        if isinstance(stopped, dict) and isinstance(stopped.get("requestId"), str):
            job["stopRequestId"] = stopped["requestId"]
        _atomic_json(job_path, job)
        return job


def _dispatch_claimed_stop(job_id: str, claimed_job: Dict[str, Any]) -> Dict[str, Any]:
    session_id = claimed_job.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        return _settle_stop_dispatch(
            job_id,
            error=BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat has no SessionId.", True),
        )
    stop_job = dict(claimed_job)
    try:
        stop_job["_transientEnvironment"] = _capture_remote_cli_environment(
            stop_job.get("aliyunCLIForwardEnv", [])
        )
        stopped = _run_stop_chat(stop_job, session_id)
    except BridgeError as exc:
        return _settle_stop_dispatch(job_id, error=exc)
    except BaseException as exc:
        error = BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat failed.", True)
        error.__cause__ = exc
        return _settle_stop_dispatch(job_id, error=error)
    return _settle_stop_dispatch(job_id, stopped=stopped)


def _record_stopped_worker_exit(
    job_id: str,
    request_seq: int,
    worker_role: Any,
    worker_token: Any,
    worker_pid: int,
) -> None:
    root, job_path, _spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        if job.get("activeRequestSeq") != request_seq:
            return
        if worker_role == "sideband":
            if job.get("sidebandWorkerToken") != worker_token:
                return
            if job.get("sidebandWorkerPid") == worker_pid:
                job.pop("sidebandWorkerPid", None)
            job.pop("sidebandWorkerToken", None)
        elif job.get("workerPid") == worker_pid:
            job.pop("workerPid", None)
        _atomic_json(job_path, job)


def _cancel_job_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_id = str(payload.get("jobId") or "")
    root, job_path, spool = _job_paths(job_id)
    with StateLock(root / ".job.lock"):
        job = _load_state_json(job_path)
        job.setdefault("stopRequestedAt", int(time.time()))
        _atomic_json(job_path, job)

    deadline = time.monotonic() + STOP_SESSION_WAIT_SECONDS
    claimed_job = _claim_stop_dispatch(job_id)
    while True:
        job = _load_state_json(job_path)
        if claimed_job is not None or job.get("stopStatus") is not None:
            break
        claimed_job = _claim_stop_dispatch(job_id)
        if claimed_job is not None:
            break
        if time.monotonic() >= deadline:
            with StateLock(root / ".job.lock"):
                latest = _load_state_json(job_path)
                if latest.get("stopStatus") is None and latest.get("state") not in TERMINAL_STATES | {"failed"}:
                    latest["state"] = "canceling"
                    _atomic_json(job_path, latest)
            return {
                "ok": True,
                "jobId": job_id,
                "state": "canceling",
                "mode": latest.get("mode"),
                "preferredLanguage": latest.get("preferredLanguage", "en"),
                "cursor": len(_read_spool(spool)),
                "turn": int(latest.get("turn") or 1),
                "presentationRequired": True,
            }
        time.sleep(0.1)

    if claimed_job is not None:
        claimed_job["_transientEnvironment"] = _remote_cli_environment_from_payload(claimed_job, payload)
        try:
            stopped = _run_stop_chat(claimed_job, str(claimed_job["sessionId"]))
        except BridgeError as exc:
            latest = _settle_stop_dispatch(job_id, error=exc)
        except BaseException as exc:
            error = BridgeError("stop_chat_failed", "Alibaba Cloud ROS StopChat failed.", True)
            error.__cause__ = exc
            latest = _settle_stop_dispatch(job_id, error=error)
        else:
            latest = _settle_stop_dispatch(job_id, stopped=stopped)
    else:
        while time.monotonic() < deadline:
            latest = _load_state_json(job_path)
            if latest.get("stopStatus") is not None:
                break
            time.sleep(0.1)
        else:
            latest = _load_state_json(job_path)

    stop_status = str(latest.get("stopStatus") or "Stopping")
    state_by_status = {
        "Stopped": "canceled",
        "Stopping": "canceling",
        "NoActiveStream": "not-active",
        "Failed": "cancel-failed",
    }
    result = {
        "ok": stop_status != "Failed",
        "jobId": job_id,
        "state": state_by_status[stop_status],
        "stopStatus": stop_status,
        "mode": latest.get("mode"),
        "preferredLanguage": latest.get("preferredLanguage", "en"),
        "cursor": len(_read_spool(spool)),
        "turn": int(latest.get("turn") or 1),
        "presentationRequired": True,
    }  # type: Dict[str, Any]
    session_id = latest.get("sessionId")
    if isinstance(session_id, str) and session_id:
        result["sessionId"] = session_id
    if latest.get("conversationMode") in SUPPORTED_AGENT_MODES:
        result["conversationMode"] = latest["conversationMode"]
    if isinstance(latest.get("stopRequestId"), str):
        result["requestId"] = latest["stopRequestId"]
    if stop_status == "Failed":
        result["error"] = {
            "code": "stop_chat_failed",
            "message": "Alibaba Cloud ROS could not stop the active chat.",
            "retryable": True,
        }
    return result


def run_worker(job_id: str, request_token: str) -> int:
    try:
        canonical_job_id = uuid.UUID(job_id).hex
        canonical_request_token = uuid.UUID(request_token).hex
    except (AttributeError, ValueError) as exc:
        raise BridgeError("invalid_input", "The worker launch capability is invalid.") from exc
    if canonical_job_id != job_id or canonical_request_token != request_token:
        raise BridgeError("invalid_input", "The worker launch capability is invalid.")
    root, _job_path, _spool = _job_paths(canonical_job_id)
    request_path = root / ("request-{}.json".format(canonical_request_token))
    request = _load_state_json(request_path, "invalid_input")
    with contextlib.suppress(OSError):
        request_path.unlink()
    request_seq = int(request.get("requestSeq") or 0)
    worker_pid = os.getpid()
    worker_role = request.get("workerRole")
    worker_token = request.get("workerToken")

    def fail_worker(error: BridgeError) -> None:
        if worker_role == "sideband" and isinstance(worker_token, str):
            _fail_sideband_job(job_id, request_seq, worker_token, error, worker_pid)
        else:
            _fail_job(job_id, request_seq, error, worker_pid)

    args = argparse.Namespace(
        aliyun_path=request.get("aliyunPath", "aliyun"),
        transport=request.get("transport", "aliyun_cli"),
        aliyun_cli_execution_mode=request.get("aliyunCLIExecutionMode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE),
        endpoint=request.get("endpoint"),
        connect_timeout=int(request.get("connectTimeout") or 10),
        read_timeout=int(request.get("readTimeout") or DEFAULT_READ_TIMEOUT_SECONDS),
        profile=request.get("profile"),
        credential_source=request.get("credentialSource"),
        region_id=request.get("regionId"),
        no_thinking=request.get("noThinking") is True,
        mode=request.get("mode"),
        session_id=request.get("sessionId"),
        user_agent=request.get("userAgent"),
    )
    prompt = request.get("prompt")
    if not isinstance(prompt, str):
        fail_worker(BridgeError("invalid_input", "The worker prompt is invalid."))
        return 1
    workspace = _trusted_manager_workspace(str(request.get("workspace") or ""))
    client_context = request.get("clientContext") if isinstance(request.get("clientContext"), str) else None
    attachments = request.get("attachments") if isinstance(request.get("attachments"), list) else []
    summary_mode = request.get("summaryMode") if request.get("summaryMode") in SUPPORTED_AGENT_MODES else args.mode

    def worker_can_continue() -> bool:
        _current_root, current_job_path, _current_spool = _job_paths(job_id)
        with StateLock(_current_root / ".job.lock"):
            current = _load_state_json(current_job_path)
            if current.get("activeRequestSeq") != request_seq or current.get("stopRequestedAt") is not None:
                return False
            if worker_role == "sideband" and current.get("sidebandWorkerToken") != worker_token:
                return False
            return True

    def project(
        stream_event_id: Optional[str],
        payload: Dict[str, Any],
        summary: StreamSummary,
        _already_applied: bool,
    ) -> bool:
        return _append_projection(
            job_id,
            _project_managed_stream_event(
                payload,
                summary,
                summary_mode,
                request_seq,
                str(worker_role or "primary"),
                worker_token,
            ),
            stream_event_id,
        )

    try:
        result = _consume_start_chat(
            args,
            workspace,
            prompt,
            client_context,
            attachments,
            summary_mode=summary_mode,
            on_payload=project,
            worker_role=str(worker_role or "primary"),
            permission_response=(
                request.get("permissionResponse")
                if isinstance(request.get("permissionResponse"), dict)
                else None
            ),
            can_reconnect=worker_can_continue,
        )
    except BaseException as exc:
        error = exc if isinstance(exc, BridgeError) else BridgeError("stream_failed", str(exc), True)
        if not worker_can_continue():
            claimed_job = _claim_stop_dispatch(job_id)
            if claimed_job is not None:
                _dispatch_claimed_stop(job_id, claimed_job)
            _record_stopped_worker_exit(job_id, request_seq, worker_role, worker_token, worker_pid)
            latest = _load_state_json(_job_paths(job_id)[1])
            return 1 if latest.get("state") == "failed" else 0
        fail_worker(error)
        return 1
    if result.get("_workerStopped") is True:
        claimed_job = _claim_stop_dispatch(job_id)
        if claimed_job is not None:
            _dispatch_claimed_stop(job_id, claimed_job)
        _record_stopped_worker_exit(job_id, request_seq, worker_role, worker_token, worker_pid)
        latest = _load_state_json(_job_paths(job_id)[1])
        return 1 if latest.get("state") == "failed" else 0

    permission_response = request.get("permissionResponse")
    if isinstance(permission_response, dict):
        result["permissionResponse"] = permission_response
    if worker_role == "sideband" and isinstance(worker_token, str):
        _finish_sideband_job(job_id, request_seq, worker_token, result, worker_pid)
        if not worker_can_continue():
            claimed_job = _claim_stop_dispatch(job_id)
            if claimed_job is not None:
                _dispatch_claimed_stop(job_id, claimed_job)
            _record_stopped_worker_exit(job_id, request_seq, worker_role, worker_token, worker_pid)
    else:
        finished = _finish_job(job_id, request_seq, result, worker_pid)
        if not finished:
            claimed_job = _claim_stop_dispatch(job_id)
            if claimed_job is not None:
                _dispatch_claimed_stop(job_id, claimed_job)
            _record_stopped_worker_exit(job_id, request_seq, worker_role, worker_token, worker_pid)
    return 0 if result.get("ok") is True else 1


def _manager_record_path() -> pathlib.Path:
    return _state_root() / "manager" / "manager.json"


def _manager_activity_path() -> pathlib.Path:
    return _state_root() / "manager" / "activity"


def _touch_manager_activity() -> None:
    path = _manager_activity_path()
    with contextlib.suppress(OSError):
        _secure_directory(path.parent)
        path.touch()


def _manager_request(
    record: Dict[str, Any],
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    url = "http://127.0.0.1:{}{}".format(record.get("port"), path)
    data = _json_bytes(payload) if payload is not None else None
    headers = {"Accept": "application/json", "Authorization": "Bearer " + str(record.get("token") or "")}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_MANAGER_REQUEST_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raw = exc.read(MAX_MANAGER_REQUEST_BYTES + 1)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError):
            value = {}
        error = value.get("error") if isinstance(value, dict) else None
        if isinstance(error, dict):
            raise BridgeError(
                str(error.get("code") or "manager_failed"),
                sanitize_text(str(error.get("message") or "The local ROS Agent manager rejected the request."), 3000),
                error.get("retryable") is True,
            ) from exc
        raise BridgeError("manager_failed", "The local ROS Agent manager rejected the request.", True) from exc
    except (OSError, urllib.error.URLError) as exc:
        raise BridgeError("manager_unavailable", "The local ROS Agent manager did not respond.", True) from exc
    if len(raw) > MAX_MANAGER_REQUEST_BYTES:
        raise BridgeError("manager_failed", "The local ROS Agent manager response exceeded its limit.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BridgeError("manager_failed", "The local ROS Agent manager returned invalid JSON.") from exc
    if not isinstance(value, dict):
        raise BridgeError("manager_failed", "The local ROS Agent manager returned invalid JSON.")
    return value


def _manager_matches(record: Dict[str, Any]) -> bool:
    if (
        record.get("schemaVersion") != MANAGER_SCHEMA_VERSION
        or record.get("scriptPath") != str(pathlib.Path(__file__).resolve())
        or not _pid_alive(record.get("pid"))
        or not isinstance(record.get("token"), str)
        or not isinstance(record.get("generation"), str)
        or not isinstance(record.get("port"), int)
    ):
        return False
    try:
        health = _manager_request(record, "/health", timeout=2)
    except BridgeError:
        return False
    return (
        health.get("ok") is True
        and health.get("generation") == record.get("generation")
        and health.get("schemaVersion") == MANAGER_SCHEMA_VERSION
    )


def _stop_spawned_process(process: Any) -> None:
    if process.poll() is not None:
        return
    with contextlib.suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=5)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    with contextlib.suppress(OSError):
        process.kill()


def _normalized_manager_idle_seconds(value: Optional[float]) -> float:
    idle_seconds = MANAGER_IDLE_SECONDS if value is None else value
    if (
        isinstance(idle_seconds, bool)
        or not isinstance(idle_seconds, (int, float))
        or idle_seconds != idle_seconds
        or idle_seconds <= 0
        or idle_seconds > MAX_MANAGER_IDLE_SECONDS
    ):
        raise BridgeError("invalid_config", "The manager idle timeout is invalid.")
    return float(idle_seconds)


def ensure_manager(idle_seconds: Optional[float] = None) -> Dict[str, Any]:
    desired_idle_seconds = _normalized_manager_idle_seconds(idle_seconds)
    record_path = _manager_record_path()
    root = record_path.parent
    _secure_directory(root)
    with StateLock(root / ".manager.lock"):
        if record_path.is_file():
            with contextlib.suppress(BridgeError):
                current = _load_state_json(record_path, "manager_unavailable")
                if _manager_matches(current):
                    if current.get("idleSeconds") != desired_idle_seconds:
                        current["idleSeconds"] = desired_idle_seconds
                        _atomic_json(record_path, current)
                    return current
        record = {
            "schemaVersion": MANAGER_SCHEMA_VERSION,
            "scriptPath": str(pathlib.Path(__file__).resolve()),
            "generation": uuid.uuid4().hex,
            "port": _free_port(),
            "token": secrets.token_urlsafe(32),
            "pid": 0,
            "startedAt": int(time.time()),
            "idleSeconds": desired_idle_seconds,
        }  # type: Dict[str, Any]
        _atomic_json(record_path, record)
        command = [
            sys.executable,
            str(pathlib.Path(__file__).resolve()),
            "_server",
            "--record-file",
            str(record_path),
        ]
        log_path = root / "manager.log"
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        process = None
        ready = False
        try:
            with log_path.open("ab", buffering=0) as log:
                process = subprocess.Popen(
                    command,
                    cwd=str(root),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=os.name != "nt",
                    creationflags=creationflags,
                )
            record["pid"] = process.pid
            record["logPath"] = str(log_path)
            _atomic_json(record_path, record)
            deadline = time.monotonic() + MANAGER_START_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    break
                if _manager_matches(record):
                    ready = True
                    return record
                time.sleep(0.1)
            raise BridgeError("manager_start_failed", "The local ROS Agent manager failed its health check.", True)
        finally:
            if process is not None and not ready:
                _stop_spawned_process(process)
                with contextlib.suppress(OSError):
                    record_path.unlink()


def _active_worker_exists() -> bool:
    jobs_root = _state_root() / "jobs"
    if not jobs_root.is_dir():
        return False
    for path in jobs_root.glob("*/job.json"):
        with contextlib.suppress(BridgeError):
            job = _load_state_json(path)
            if _pid_alive(job.get("workerPid")) or _pid_alive(job.get("sidebandWorkerPid")):
                return True
    return False


class _ManagerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: Tuple[str, int], record: Dict[str, Any]) -> None:
        super().__init__(address, _ManagerHandler)
        self.record = record
        self.last_activity = time.monotonic()
        self.activity_mtime_ns = 0
        self.startup_deadline = self.last_activity + MANAGER_START_TIMEOUT_SECONDS
        self.startup_health_checked = False


class _ManagerHandler(BaseHTTPRequestHandler):
    server: _ManagerServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _authorized(self) -> bool:
        expected = "Bearer " + str(self.server.record.get("token") or "")
        supplied = self.headers.get("Authorization", "")
        return bool(expected) and secrets.compare_digest(supplied, expected)

    def _write(self, status: int, value: Dict[str, Any]) -> None:
        data = _json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()
        self.server.last_activity = time.monotonic()
        self.close_connection = True

    def do_GET(self) -> None:
        if not self._authorized():
            self._write(401, {"ok": False, "error": {"code": "unauthorized", "message": "Unauthorized."}})
            return
        self.server.last_activity = time.monotonic()
        if self.path != "/health":
            self._write(404, {"ok": False, "error": {"code": "not_found", "message": "Not found."}})
            return
        self._write(
            200,
            {
                "ok": True,
                "schemaVersion": MANAGER_SCHEMA_VERSION,
                "generation": self.server.record.get("generation"),
                "pid": os.getpid(),
            },
        )
        self.server.startup_health_checked = True

    def do_POST(self) -> None:
        if not self._authorized():
            self._write(401, {"ok": False, "error": {"code": "unauthorized", "message": "Unauthorized."}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_MANAGER_REQUEST_BYTES:
                raise BridgeError("invalid_input", "The manager request size is invalid.")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise BridgeError("invalid_input", "The manager request must be a JSON object.")
            self.server.last_activity = time.monotonic()
            if self.path == "/start":
                result = _start_job_local(value)
            elif self.path == "/continue":
                result = _continue_job_local(value)
            elif self.path == "/respond":
                result = _respond_job_local(value)
            elif self.path == "/cancel":
                result = _cancel_job_local(value)
            elif self.path == "/follow":
                result = _follow_job_local(
                    str(value.get("jobId") or ""),
                    int(value.get("cursor") or 0),
                    float(value.get("waitSeconds") or 0),
                )
            else:
                self._write(404, {"ok": False, "error": {"code": "not_found", "message": "Not found."}})
                return
        except BridgeError as exc:
            self._write(
                400,
                {
                    "ok": False,
                    "state": "failed",
                    "error": {
                        "code": exc.code,
                        "message": sanitize_text(exc.message, 3000),
                        "retryable": exc.retryable,
                    },
                },
            )
            return
        except (TypeError, ValueError, UnicodeError) as exc:
            self._write(
                400,
                {
                    "ok": False,
                    "state": "failed",
                    "error": {"code": "invalid_input", "message": sanitize_text(str(exc), 1000)},
                },
            )
            return
        self._write(200, result)


def run_manager_server(record_file: str) -> int:
    record_path = pathlib.Path(record_file).resolve()
    record = _load_state_json(record_path, "manager_start_failed")
    if record.get("scriptPath") != str(pathlib.Path(__file__).resolve()):
        raise BridgeError("manager_start_failed", "The manager script identity does not match.")
    server = _ManagerServer(("127.0.0.1", int(record["port"])), record)
    activity_path = _manager_activity_path()
    _touch_manager_activity()
    with contextlib.suppress(OSError):
        server.activity_mtime_ns = activity_path.stat().st_mtime_ns
    server.timeout = 0.5
    try:
        while True:
            server.handle_request()
            with contextlib.suppress(OSError):
                activity_mtime_ns = activity_path.stat().st_mtime_ns
                if activity_mtime_ns > server.activity_mtime_ns:
                    server.activity_mtime_ns = activity_mtime_ns
                    server.last_activity = time.monotonic()
            if not server.startup_health_checked:
                if time.monotonic() >= server.startup_deadline:
                    break
                continue
            if _active_worker_exists():
                server.last_activity = time.monotonic()
                continue
            idle_seconds = float(record.get("idleSeconds") or MANAGER_IDLE_SECONDS)
            with contextlib.suppress(BridgeError):
                latest_record = _load_state_json(record_path, "manager_unavailable")
                if latest_record.get("generation") == record.get("generation"):
                    idle_seconds = _normalized_manager_idle_seconds(latest_record.get("idleSeconds"))
            if time.monotonic() - server.last_activity >= idle_seconds:
                break
    finally:
        server.server_close()
    return 0


def _run_check_command(command: List[str], required: bool = False) -> Optional[subprocess.CompletedProcess]:
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if required:
            raise BridgeError("cli_check_failed", "Alibaba Cloud CLI could not be checked.", True) from exc
        return None
    if result.returncode != 0:
        if required:
            error = (result.stderr or b"").decode("utf-8", "replace")
            raise BridgeError("cli_check_failed", sanitize_text(error, 1000) or "Alibaba Cloud CLI check failed.", True)
        return None
    return result


def _parse_profile_fields(output: bytes) -> Dict[str, str]:
    values = {}  # type: Dict[str, str]
    for raw_line in output.decode("utf-8", "replace").splitlines():
        key, separator, raw_value = raw_line.partition("=")
        if not separator or key not in {"profile", "mode", "language"}:
            continue
        value = sanitize_text(raw_value, 200)
        if value:
            values[key] = value
    return values


def run_check(args: argparse.Namespace) -> Dict[str, Any]:
    sdk = None  # type: Optional[Dict[str, Any]]
    cli_execution_mode = getattr(args, "aliyun_cli_execution_mode", DEFAULT_ALIYUN_CLI_EXECUTION_MODE)
    if args.transport == "code":
        sdk = _load_code_sdk()

    plugin_status = None  # type: Optional[Dict[str, Any]]
    plugin_auto_install = None  # type: Optional[bool]
    reconnect_ready = args.transport == "code"
    reconnect_blockers = []  # type: List[str]
    if args.transport == "aliyun_cli" and cli_execution_mode == "remote":
        resolve_aliyun(args.aliyun_path)
        current_profile = {"configured": True, "mode": "RemoteSandbox"}
        cli = "aliyun"
        version = None
        executor_version = sanitize_text(os.environ.get(REMOTE_EXECUTOR_VERSION_ENV, ""), 120)
        raw_capabilities = os.environ.get(REMOTE_EXECUTOR_CAPABILITIES_ENV, "")
        executor_capabilities = {
            value.strip() for value in raw_capabilities.split(",") if value.strip()
        }
        reconnect_ready = bool(
            executor_version
            and REMOTE_BOOTSTRAP_CAPABILITY in executor_capabilities
        )
        if not executor_version:
            reconnect_blockers.append("remote_executor_version_unavailable")
        if REMOTE_BOOTSTRAP_CAPABILITY not in executor_capabilities:
            reconnect_blockers.append("remote_bootstrap_capability_unavailable")
    elif args.transport == "code" and not args.profile_pinned:
        assert sdk is not None
        region_id = _environment_region() or "cn-hangzhou"
        try:
            _code_credentials(sdk, args.aliyun_path, None, region_id, None)
        except BridgeError:
            raise
        except Exception as exc:
            raise BridgeError(
                "credential_failed",
                "Alibaba Cloud SDK default credential chain could not resolve credentials.",
                True,
            ) from exc
        current_profile = {
            "configured": True,
            "mode": "DefaultCredentialChain",
            "regionId": region_id,
        }  # type: Dict[str, Any]
        cli = None
        version = None
    else:
        selected = _selected_cli_profile_record(args.profile)
        region_id = _environment_region() or selected.get("regionId") or "cn-hangzhou"
        current_profile = {"configured": True, "name": selected["name"], "mode": selected["mode"]}
        if selected.get("language"):
            current_profile["language"] = selected["language"]
        current_profile["regionId"] = region_id
        if args.transport == "code":
            assert sdk is not None
            try:
                _code_credentials(sdk, args.aliyun_path, selected["name"], region_id, "profile")
            except BridgeError:
                raise
            except Exception as exc:
                raise BridgeError(
                    "credential_failed",
                    "Alibaba Cloud SDK could not load or refresh the selected CLI Profile.",
                    True,
                ) from exc
            cli = None
            version = None
        else:
            aliyun = resolve_aliyun(args.aliyun_path)
            version_result = _run_check_command([aliyun, "version"], required=True)
            assert version_result is not None
            cli = "aliyun"
            version = sanitize_text((version_result.stdout or b"").decode("utf-8", "replace"), 200)
            plugin_status = _local_ros_plugin_status()
            plugin_auto_install = bool(selected.get("autoPluginInstall"))
            reconnect_ready = plugin_status.get("reconnectReady") is True
            if not reconnect_ready:
                reconnect_blockers.append("ros_cli_plugin_reconnect_version_unavailable")

    result = {
        "ok": True,
        "cli": cli,
        "version": version,
        "transport": args.transport,
        "aliyunCLIExecutionMode": cli_execution_mode,
        "endpoint": args.endpoint,
        "allowedAgentModes": args.allowed_agent_modes,
        "managerIdleSeconds": args.manager_idle_seconds,
        "enableThinking": args.enable_thinking,
        "aliyunCLIProfile": args.aliyun_cli_profile,
        "currentProfile": current_profile,
        "startChatReconnectReady": reconnect_ready,
    }  # type: Dict[str, Any]
    if reconnect_blockers:
        result["startChatReconnectBlockers"] = reconnect_blockers
    if args.transport == "aliyun_cli" and cli_execution_mode == "remote":
        result["aliyunCLIForwardEnv"] = args.aliyun_cli_forward_env
        result["aliyunCLIForwardEnvPresent"] = [
            name for name in args.aliyun_cli_forward_env if os.environ.get(name) is not None
        ]
        if executor_version:
            result["remoteExecutorVersion"] = executor_version
        result["remoteExecutorCapabilities"] = sorted(executor_capabilities)
    if plugin_status is not None:
        result["rosPluginReady"] = plugin_status["ready"]
        result["pluginAutoInstallEnabled"] = plugin_auto_install
        result["pluginInstallRequired"] = plugin_status.get("reconnectReady") is not True
        if plugin_status.get("version"):
            result["rosPluginVersion"] = plugin_status["version"]
    return result


def _follow_after_command(args: argparse.Namespace, result: Dict[str, Any]) -> Dict[str, Any]:
    if not getattr(args, "follow", False):
        return result
    followed = run_follow_job(
        argparse.Namespace(
            job_id=result["jobId"],
            cursor=result["cursor"],
            wait_seconds=getattr(args, "follow_seconds", DEFAULT_FOLLOW_SECONDS),
            manager_idle_seconds=getattr(args, "manager_idle_seconds", MANAGER_IDLE_SECONDS),
        )
    )
    followed["workerPid"] = result.get("workerPid")
    return _bound_follow_result(followed)


def run_start_job(args: argparse.Namespace) -> Dict[str, Any]:
    workspace = _workspace()
    prompt = read_prompt(workspace, args.prompt_file)
    client_context = load_client_context(workspace, args.client_context_file)
    attachments = load_attachments(workspace, args.attachments_file)
    _resolve_start_identity(args)
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/start",
        {
            "workspace": str(workspace),
            "prompt": prompt,
            "mode": args.mode,
            "transport": args.transport,
            "aliyunCLIExecutionMode": args.aliyun_cli_execution_mode,
            "aliyunCLIForwardEnv": args.aliyun_cli_forward_env,
            "transientEnvironment": _capture_remote_cli_environment(args.aliyun_cli_forward_env),
            "endpoint": args.endpoint,
            "regionId": args.region_id,
            "profile": args.profile,
            "credentialSource": args.credential_source,
            "noThinking": args.no_thinking,
            "connectTimeout": args.connect_timeout,
            "readTimeout": args.read_timeout,
            "aliyunPath": args.aliyun_path,
            "clientContext": client_context,
            "attachments": attachments,
        },
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_follow_job(args: argparse.Namespace) -> Dict[str, Any]:
    wait_seconds = max(0.0, min(float(args.wait_seconds), MAX_FOLLOW_SECONDS))
    record = ensure_manager(args.manager_idle_seconds)
    return _manager_request(
        record,
        "/follow",
        {"jobId": args.job_id, "cursor": int(args.cursor), "waitSeconds": wait_seconds},
        timeout=wait_seconds + 15,
    )


def run_continue_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/continue",
        {
            "jobId": args.job_id,
            "promptFile": str(pathlib.Path(args.prompt_file).expanduser().resolve()),
            "transientEnvironment": _capture_remote_cli_environment(args.aliyun_cli_forward_env),
        },
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_respond_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    result = _manager_request(
        record,
        "/respond",
        {
            "jobId": args.job_id,
            "inputFile": (
                str(pathlib.Path(args.input_file).expanduser().resolve()) if args.input_file is not None else None
            ),
            "permissionRef": args.permission_ref,
            "decision": args.decision,
            "transientEnvironment": _capture_remote_cli_environment(args.aliyun_cli_forward_env),
        },
        timeout=15,
    )
    return _follow_after_command(args, result)


def run_cancel_job(args: argparse.Namespace) -> Dict[str, Any]:
    record = ensure_manager(args.manager_idle_seconds)
    return _manager_request(
        record,
        "/cancel",
        {
            "jobId": args.job_id,
            "transientEnvironment": _capture_remote_cli_environment(args.aliyun_cli_forward_env),
        },
        timeout=STOP_REQUEST_TIMEOUT_SECONDS + 15,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use Alibaba Cloud ROS Agent through Alibaba Cloud CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Check Alibaba Cloud CLI without calling StartChat.")
    check.add_argument("--aliyun-path", default="aliyun")

    start = subparsers.add_parser("start", help="Start a managed StartChat job.")
    start.add_argument("--prompt-file", required=True)
    start.add_argument("--mode", choices=("normal", "pipeline"), default="normal")
    start.add_argument("--region-id")
    start.add_argument("--endpoint")
    start.add_argument("--profile")
    start.add_argument("--client-context-file")
    start.add_argument("--attachments-file")
    start.add_argument("--no-thinking", action="store_true")
    start.add_argument("--connect-timeout", type=int, default=10)
    start.add_argument("--read-timeout", type=int, default=DEFAULT_READ_TIMEOUT_SECONDS)
    start.add_argument("--aliyun-path", default="aliyun")
    start.add_argument("--follow", action="store_true")
    start.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    follow = subparsers.add_parser("follow", help="Wait for the next managed StartChat boundary.")
    follow.add_argument("--job-id", required=True)
    follow.add_argument("--cursor", type=int, default=0)
    follow.add_argument("--wait-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    continued = subparsers.add_parser("continue", help="Send a natural-language continuation for a managed job.")
    continued.add_argument("--job-id", required=True)
    continued.add_argument("--prompt-file", required=True)
    continued.add_argument("--follow", action="store_true")
    continued.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    respond = subparsers.add_parser("respond", help="Approve or deny a managed StartChat permission.")
    respond.add_argument("--job-id", required=True)
    respond.add_argument("--permission-ref")
    respond.add_argument("--input-file", help=argparse.SUPPRESS)
    respond.add_argument("--decision", choices=("allow_once", "deny"), required=True)
    respond.add_argument("--follow", action="store_true")
    respond.add_argument("--follow-seconds", type=float, default=DEFAULT_FOLLOW_SECONDS)

    cancel = subparsers.add_parser("cancel", help="Stop the remote chat for a managed job.")
    cancel.add_argument("--job-id", required=True)

    server = subparsers.add_parser("_server", help=argparse.SUPPRESS)
    server.add_argument("--record-file", required=True)
    worker = subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    worker.add_argument("--job-id", required=True)
    worker.add_argument("--request-token", required=True)
    return parser


def _print_json(value: Dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "_server":
            return run_manager_server(args.record_file)
        if args.command == "_worker":
            return run_worker(args.job_id, args.request_token)
        apply_skill_config(args, load_skill_config())
        if args.command == "check":
            result = run_check(args)
        elif args.command == "start":
            if args.connect_timeout <= 0 or args.read_timeout <= 0:
                raise BridgeError("invalid_input", "Timeout values must be positive integers.")
            result = run_start_job(args)
        elif args.command == "follow":
            result = run_follow_job(args)
        elif args.command == "continue":
            result = run_continue_job(args)
        elif args.command == "cancel":
            result = run_cancel_job(args)
        else:
            result = run_respond_job(args)
    except BridgeError as exc:
        failure = {
            "ok": False,
            "state": "failed",
            "error": {
                "code": exc.code,
                "message": sanitize_text(exc.message, 3000),
                "retryable": exc.retryable,
            },
        }
        if args.command != "check":
            failure["presentationRequired"] = True
        _print_json(failure)
        return 1
    _print_json(result)
    return 0 if result.get("ok") is True else 1
