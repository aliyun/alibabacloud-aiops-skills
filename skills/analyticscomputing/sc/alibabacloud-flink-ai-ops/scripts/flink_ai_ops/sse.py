"""Own stream resources and validate SSE framing around the pinned SDK.

Private function-global copies replace the transport/session factories and
event parser for one stream. Signing, retry policy and HTTP error handling
still use the official SDK. SDK modules and aiohttp globals stay untouched.
"""

from contextlib import AsyncExitStack
import inspect
from types import FunctionType, MethodType

from .common import OpsError


_MAX_SSE_EVENT_BYTES = 8 * 1024 * 1024


async def _read_sse_events(stream):
    """Yield complete SSE events without silently dropping overlong or partial frames."""
    from darabonba.event import Event

    line = bytearray()
    event_id = None
    event_type = ""
    data = []
    metadata_pending = False
    frame_bytes = 0
    first_line = True
    skip_lf = False
    async for chunk in stream:
        if not chunk:
            continue
        if skip_lf and chunk.startswith(b"\n"):
            chunk = chunk[1:]
        skip_lf = chunk.endswith(b"\r")

        for part in chunk.splitlines(keepends=True):
            # Count each line ending once, including CRLF split across chunks.
            frame_bytes += len(part) - part.endswith(b"\r\n")
            if frame_bytes > _MAX_SSE_EVENT_BYTES:
                raise OpsError("CHAT_INCOMPLETE_STREAM", "An assistant SSE frame exceeded the 8 MiB limit.")
            if not part.endswith((b"\n", b"\r")):
                line.extend(part)
                continue

            line.extend(part.rstrip(b"\r\n"))
            try:
                decoded = line.decode("utf-8-sig" if first_line else "utf-8")
            except UnicodeDecodeError as error:
                raise OpsError("InvalidResponse", "The assistant SSE stream contains invalid UTF-8.") from error
            line.clear()
            first_line = False

            if not decoded:
                if data:
                    yield Event(id=event_id, event=event_type or "message", data="\n".join(data))
                event_type = ""
                data.clear()
                metadata_pending = False
                frame_bytes = 0
                continue

            name, _, value = decoded.partition(":")
            value = value.removeprefix(" ")
            if name == "data":
                data.append(value)
            elif name == "event":
                event_type = value
                metadata_pending = True
            elif name == "id" and "\x00" not in value:
                event_id = value
                metadata_pending = True

    # A trailing heartbeat is harmless. Pending event fields require a separator.
    tail = bytes(line).removeprefix(b"\xef\xbb\xbf") if first_line else line
    if data or metadata_pending or (tail.strip() and not tail.startswith(b":")):
        raise OpsError("CHAT_INCOMPLETE_STREAM", "The assistant SSE stream ended before the current frame was delimited.")


class _Delegate:
    """Override named attributes while delegating everything else unchanged."""

    def __init__(self, original, **overrides):
        self._original = original
        self.__dict__.update(overrides)

    def __getattr__(self, name):
        return getattr(self._original, name)


def _private_binding(function, **overrides):
    """Bind official function code to isolated globals for this invocation."""
    source = getattr(function, "__func__", function)
    if not isinstance(source, FunctionType):
        return function
    if not overrides.keys() <= source.__globals__.keys():
        raise OpsError("DependencyError", "The SDK SSE implementation does not match the adapter; use the locked dependencies.")
    private = FunctionType(source.__code__, {**source.__globals__, **overrides},
                           source.__name__, source.__defaults__, source.__closure__)
    private.__kwdefaults__ = source.__kwdefaults__
    return MethodType(private, function.__self__) if inspect.ismethod(function) else private


async def _close(resource):
    """Close an owned SDK body or session, supporting sync and async closers."""
    close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
    if close is not None:
        result = close()
        if inspect.isawaitable(result):
            await result


class SDKStreamResources:
    """Capture bodies and sessions before cancellation can lose their ownership."""

    def __init__(self):
        self._bodies = []
        self._sessions = []
        self.request_id = ""

    def open(self, client, params, request, runtime):
        factory = client.call_sseapi_async
        source = getattr(factory, "__func__", factory)
        if isinstance(source, FunctionType):
            self._core = source.__globals__.get("DaraCore")
            stream_utils = source.__globals__.get("DaraStream")
            if self._core is None or stream_utils is None:
                raise OpsError("DependencyError", "The SDK SSE implementation does not match the adapter; use the locked dependencies.")
            factory = _private_binding(
                factory, DaraCore=_Delegate(self._core, async_do_sse_action=self._send),
                DaraStream=_Delegate(stream_utils, read_as_sse_async=_read_sse_events),
            )
        return factory(params, request, runtime)

    def _create_session(self, *args, **kwargs):
        session = self._session_factory(*args, **kwargs)
        self._sessions.append(session)
        return session

    async def _send(self, request, runtime_option=None):
        transport = self._core.async_do_sse_action
        source = getattr(transport, "__func__", transport)
        if isinstance(source, FunctionType):
            http = source.__globals__.get("aiohttp")
            if http is None:
                raise OpsError("DependencyError", "The SDK SSE transport implementation does not match the adapter; use the locked dependencies.")
            self._session_factory = http.ClientSession
            transport = _private_binding(transport, aiohttp=_Delegate(
                http, ClientSession=self._create_session))
        response = await transport(request, runtime_option)
        self._bodies.append(response.body)
        self.request_id = (response.headers or {}).get("x-acs-request-id", "")
        return response

    async def aclose(self):
        """Release only this stream's resources, even if one closer fails."""
        async with AsyncExitStack() as stack:
            for session in self._sessions:
                if not session.closed:
                    stack.push_async_callback(_close, session)
            for body in self._bodies:
                stack.push_async_callback(_close, body)


async def finish_stream(stream, resources=None, *, primary=None, request_id=""):
    """Finish all owned closers without replacing an active failure or cancellation."""
    errors = []
    closers = []
    if stream is not None and hasattr(stream, "aclose"):
        closers.append(stream.aclose)
    if resources is not None:
        closers.append(resources.aclose)
    for close in closers:
        try:
            await close()
        except BaseException as error:
            errors.append(error)
    if not errors:
        return
    details = [{"code": getattr(error, "code", type(error).__name__),
                "message": str(error)} for error in errors]
    if primary is not None and not isinstance(primary, GeneratorExit):
        primary.cleanup_errors = [*getattr(primary, "cleanup_errors", []), *details]
        return
    for error in errors:
        if not isinstance(error, Exception):
            raise error
    if len(errors) == 1 and isinstance(errors[0], OpsError):
        raise errors[0]
    raise OpsError("StreamCleanupError", "Assistant stream resource cleanup failed; inspect the cleanup error evidence.",
                   request_id=request_id, data={"cleanupErrors": details}) from errors[0]
