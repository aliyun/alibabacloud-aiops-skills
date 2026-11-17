"""Local Chat inputs and optional minimal session records; no service calls."""
from __future__ import annotations

import argparse
import json
import math
import os
import select
import stat
import tempfile
import time


MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 128
TARGET_KEYS = ("name", "region", "profile", "endpoint")
SESSION_KEYS = {"target", "threadId", "messageId", "callId", "phase"}


class InputError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse messages can include supplied values. Keep user data out of diagnostics.
        raise InputError("INVALID_ARGUMENT", "Invalid arguments; use --help for usage.")


def _nonempty(value):
    if not value.strip() or "\0" in value:
        raise argparse.ArgumentTypeError("must be a nonempty string")
    return value


def parse_args(argv):
    output_help = "Execution returns one complete JSON result on stdout; diagnostics go to stderr."
    parser = _Parser(description="Chat with SLS DataAgents through the Aliyun CLI.",
                     epilog=output_help, allow_abbrev=False)
    parser.set_defaults(message=None, message_file=None, interaction_result=None,
                        interaction_result_file=None, variables=None)
    entries = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    for command, description, context_help, requirements in (
        ("send", "Send a message in a new or existing thread.",
         "Previous full JSON result for checking pending interactions (optional)",
         "Provide name and region directly or through a session file.\n"
         "Without a thread ID in arguments or session, a new thread is created.\n"
         "Continue an existing thread only after its request ends with no pending interactions."),
        ("respond", "Return the user's response to one pending interaction.",
         "Latest complete JSON result containing pending interactions (required)",
         "Provide name, region and thread ID directly or through a session file.\n"
         "index is zero-based within context.interactions; result follows the selected interaction."),
        ("reconnect", "Continue receiving output from an existing request.",
         "Previous full JSON result; required for known pending interactions",
         "Provide name, region and thread ID directly or through a session file.\n"
         "First verify that the original request is still running.\n"
         "This command does not check history or resend messages."),
    ):
        entry = entries.add_parser(
            command, help=description, description=description, allow_abbrev=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=requirements + "\nExplicit values must match saved session bindings.\n"
            "Context does not supply target or thread identifiers.\n\n" + output_help)
        location = entry.add_argument_group("Target and session")
        for name, metavar, help_text in (
            ("name", "NAME", "DataAgent resource name"),
            ("region", "REGION", "Chat service region"),
            ("profile", "PROFILE", "Aliyun CLI credential profile"),
            ("endpoint", "ENDPOINT", "Chat service endpoint"),
            ("thread-id", "ID", "Existing thread ID"),
            ("session-file", "FILE", "Read and update saved target and thread identifiers"),
        ):
            location.add_argument("--" + name, type=_nonempty, metavar=metavar, help=help_text)
        inputs = entry.add_argument_group("Inputs")
        inputs.add_argument("--context-file", type=_nonempty, required=command == "respond",
                            metavar="FILE", help=context_help)
        if command == "send":
            message = inputs.add_mutually_exclusive_group(required=True)
            message.add_argument("--message", metavar="TEXT", help="Message text")
            message.add_argument("--message-file", type=_nonempty, metavar="FILE",
                                 help="Read the message from a UTF-8 file; - for stdin")
            inputs.add_argument("--variables", type=_parse_variables, metavar="JSON",
                                help="JSON context variables for this send; not saved in session")
        elif command == "respond":
            result = inputs.add_mutually_exclusive_group(required=True)
            result.add_argument("--interaction-result", metavar="JSON",
                                help='One user result: {"index":0,"result":...}')
            result.add_argument("--interaction-result-file", type=_nonempty, metavar="FILE",
                                help="Read the same object from a UTF-8 file; - for stdin")
        options = entry.add_argument_group("Run options")
        options.add_argument("--progress", action=argparse.BooleanOptionalAction, default=True,
                             help="Show occasional progress on stderr (default: %(default)s); use --no-progress to disable")
    return parser.parse_args(argv)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InputError("INVALID_JSON", "JSON contains a duplicate object key.")
        result[key] = value
    return result


def _constant(value):
    raise InputError("INVALID_JSON", "JSON contains a non-finite number.")


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        _constant(value)
    return number


def _check_strings(value, depth=0):
    if isinstance(value, (list, dict)) and depth >= MAX_JSON_DEPTH:
        raise InputError("JSON_TOO_DEEP", "JSON nesting exceeds the 128-level limit.")
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, list):
        for item in value:
            _check_strings(item, depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            key.encode("utf-8")
            _check_strings(item, depth + 1)


def parse_json(text):
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
        _check_strings(value)
    except UnicodeError as exc:
        raise InputError("INVALID_ENCODING", "JSON strings must be valid UTF-8 text.") from exc
    except (ValueError, RecursionError) as exc:
        raise InputError("INVALID_JSON", "Input is not valid JSON.") from exc
    if not isinstance(value, (dict, list)):
        raise InputError("INVALID_JSON", "JSON input must be an object or array.")
    return value


def _checked_text(data):
    if isinstance(data, bytes):
        if len(data) > MAX_INPUT_BYTES:
            raise InputError("INPUT_TOO_LARGE", "Input exceeds the 16 MiB limit.")
        try:
            data = data.decode("utf-8")
        except UnicodeError as exc:
            raise InputError("INVALID_ENCODING", "Input must use UTF-8.") from exc
    if not isinstance(data, str):
        raise InputError("INVALID_INPUT", "Input must contain text.")
    try:
        size = len(data.encode("utf-8"))
    except UnicodeError as exc:
        raise InputError("INVALID_ENCODING", "Input must use UTF-8.") from exc
    if size > MAX_INPUT_BYTES:
        raise InputError("INPUT_TOO_LARGE", "Input exceeds the 16 MiB limit.")
    return data


def _parse_variables(text):
    variables = parse_json(_checked_text(text))
    if not isinstance(variables, dict):
        raise InputError("INVALID_VARIABLES", "Variables must be a JSON object.")
    if {"userinteractive", "userinteractivestr"}.intersection(key.casefold() for key in variables):
        raise InputError("INVALID_VARIABLES", "Interaction variables must be supplied through respond.")
    return variables


def _read_text(stream):
    return _checked_text(stream.read(MAX_INPUT_BYTES + 1))


def _input_remaining(deadline):
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise InputError("INPUT_TIMEOUT", "The shared execution deadline expired while reading input.")
    return remaining


def _read_stdin(stdin, deadline):
    stream = getattr(stdin, "buffer", stdin)
    try:
        descriptor = stream.fileno()
    except (AttributeError, OSError, ValueError):
        # In-memory streams have no descriptor and cannot await a pipe EOF.
        return _read_text(stream)
    data = bytearray()
    try:
        while True:
            ready, _, _ = select.select([descriptor], [], [], _input_remaining(deadline))
            if not ready:
                raise InputError("INPUT_TIMEOUT", "The shared execution deadline expired while reading input.")
            chunk = os.read(descriptor, min(65536, MAX_INPUT_BYTES + 1 - len(data)))
            if not chunk:
                return _checked_text(bytes(data))
            data.extend(chunk)
            if len(data) > MAX_INPUT_BYTES:
                raise InputError("INPUT_TOO_LARGE", "Input exceeds the 16 MiB limit.")
    except (OSError, ValueError) as exc:
        raise InputError("INPUT_FILE_ERROR", "Unable to read stdin.") from exc


def _read_file(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise InputError("INPUT_FILE_ERROR", "Input file must be a regular file; use - for stdin.")
            return _read_text(stream)
    except OSError as exc:
        raise InputError("INPUT_FILE_ERROR", "Unable to read the input file.") from exc


def load_json_file(path):
    return parse_json(_read_file(path))


def read_input(args, stdin, *, deadline=None):
    _input_remaining(deadline)
    if args.command == "reconnect":
        return None
    if args.command == "send":
        direct, path = args.message, args.message_file
    else:
        direct, path = args.interaction_result, args.interaction_result_file
    if (direct is None) == (path is None):
        raise InputError("INVALID_ARGUMENT", "Provide exactly one direct or file input.")
    if path == "-":
        text = _read_stdin(stdin, deadline)
    else:
        text = _read_file(path) if path is not None else direct
    _input_remaining(deadline)
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as exc:
        raise InputError("INVALID_ENCODING", "Input must use UTF-8.") from exc
    if size > MAX_INPUT_BYTES:
        raise InputError("INPUT_TOO_LARGE", "Input exceeds the 16 MiB limit.")
    if args.command == "send":
        if not text.strip():
            raise InputError("INVALID_ARGUMENT", "Message must not be blank.")
        return text
    return parse_json(text)


def _string(value, name):
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise InputError("INVALID_LOCATION", "Invalid " + name + ".")
    return value


def load_session(path):
    if path is None:
        return {}
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent) or not os.access(parent, os.W_OK | os.X_OK):
        raise InputError("SESSION_FILE_ERROR", "The session directory must exist and be writable.")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise InputError("SESSION_FILE_ERROR", "Unable to safely open the session file.") from exc
    try:
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
                raise InputError("SESSION_FILE_ERROR", "Session must be a private regular file owned by this user.")
            value = parse_json(_read_text(stream))
    except OSError as exc:
        raise InputError("SESSION_FILE_ERROR", "Unable to read the session file.") from exc
    if not isinstance(value, dict) or set(value) - SESSION_KEYS or not isinstance(value.get("target"), dict):
        raise InputError("INVALID_SESSION", "Session must contain only minimal location records.")
    target = value["target"]
    if set(target) - set(TARGET_KEYS):
        raise InputError("INVALID_SESSION", "Session target contains unsupported fields.")
    for key in ("name", "region"):
        _string(target.get(key), key)
    for key in target:
        _string(target[key], key)
    for key in set(value) - {"target"}:
        _string(value[key], key)
    return value


def resolve_target(args, session, context):
    target = {}
    recorded = session.get("target", {})
    for key in TARGET_KEYS:
        explicit = getattr(args, key)
        previous = recorded.get(key)
        if explicit is not None and previous is not None and explicit != previous:
            raise InputError("TARGET_CONFLICT", "Explicit target conflicts with the session binding.")
        selected = explicit if explicit is not None else previous
        if selected is not None:
            target[key] = _string(selected, key)
    for key in ("name", "region"):
        if key not in target:
            raise InputError("INVALID_ARGUMENT", "Missing --" + key + ".")
    thread_id = args.thread_id
    recorded_thread = session.get("threadId")
    if thread_id is not None and recorded_thread is not None and thread_id != recorded_thread:
        raise InputError("TARGET_CONFLICT", "Explicit thread conflicts with the session binding.")
    thread_id = thread_id if thread_id is not None else recorded_thread
    if thread_id is not None:
        target["threadId"] = _string(thread_id, "threadId")
    if context is not None:
        if not isinstance(context, dict):
            raise InputError("INVALID_CONTEXT", "Context must be a JSON object.")
        context_thread = _string(context.get("threadId"), "context threadId")
        if thread_id is None or context_thread != thread_id:
            raise InputError("TARGET_CONFLICT", "Context does not match the selected thread.")
        if "interactions" in context and not isinstance(context["interactions"], list):
            raise InputError("INVALID_CONTEXT", "Context interactions must be an array.")
        if "messageId" in context:
            _string(context["messageId"], "context messageId")
    if args.command in ("respond", "reconnect") and thread_id is None:
        raise InputError("INVALID_ARGUMENT", "This operation requires the original --thread-id or session location.")
    return target


def save_session(path, target, phase, message_id=None, call_id=None):
    if path is None:
        return
    # Validate an existing record before replacing it; never follow a symlink.
    if os.path.lexists(path):
        load_session(path)
    for key in ("name", "region"):
        _string(target.get(key), key)
    record = {"target": {key: _string(target[key], key) for key in TARGET_KEYS if key in target},
              "phase": _string(phase, "phase")}
    for key, value in (("threadId", target.get("threadId")), ("messageId", message_id), ("callId", call_id)):
        if value is not None:
            record[key] = _string(value, key)
    directory = os.path.dirname(os.path.abspath(path))
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".chat-session-", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(record, stream, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.path.islink(path):
            raise InputError("SESSION_FILE_ERROR", "Session file must not be a symbolic link.")
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        raise InputError("SESSION_FILE_ERROR", "Unable to atomically update the private session file.") from exc
    finally:
        if temp_path is not None:
            os.unlink(temp_path)
