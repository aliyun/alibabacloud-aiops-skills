"""Official SDK requests with bounded, non-redirecting HTTP transport.

The SDK owns ACS signing and request serialization. The pinned SDK's synchronous
transport buffers responses and follows redirects; a scoped transport replacement
preserves streaming and forbids credential-bearing redirects. No signing is copied.
"""
import json
import os
import re
import threading
import time
from urllib.parse import quote
from unittest.mock import patch
import requests
from alibabacloud_tea_openapi.client import Client
from alibabacloud_tea_openapi.utils_models import Config, Params, OpenApiRequest
from darabonba.core import DaraCore
from darabonba.response import DaraResponse
from darabonba.runtime import RuntimeOptions
from darabonba.policy.retry import RetryOptions
from .common import ClientError, require, user_agent
from .contract import API_VERSION, OPERATIONS
from .credentials import create_credentials
from .validation import validate, inspect_response, CompatibleResponse
from .settings import supported_connection

NETWORK_LOCK = threading.RLock()
RETRY_DELAYS = (1, 2)
RETRY_CODES = frozenset(('InternalError', 'ServiceUnavailable', 'Throttling',
                         'Throttling.User', 'Throttling.Api', 'NetworkInterrupted', 'TransientServiceError'))
IDEMPOTENT_ACTIONS = frozenset(('CreateSession', 'CancelRun', 'SendMessage'))


class Transport:
    def __init__(self, connection, credential=None):
        agent = user_agent()
        require(supported_connection(connection), 'SetupRequired', 'The saved connection is not supported by this release. Save a supported connection with setup configure.')
        endpoint = connection['endpoint']
        require(os.environ.get('DEBUG', '').lower() != 'sdk', 'UnsafeDebug', 'Disable SDK HTTP debug output before using credentials.')
        self.client = Client(Config(endpoint=endpoint, protocol='https', region_id=connection['region'],
                                    credential=credential or create_credentials(connection['credentials']),
                                    user_agent=agent, retry_options=RetryOptions(max_attempts=1)))
        self.session = requests.Session()
        self.response = None
        self.started = time.monotonic()
        self.runtime = RuntimeOptions(connect_timeout=10000, read_timeout=60000, ignore_ssl=False)

    def close(self):
        if self.response is not None:
            self.response.close()
        self.session.close()

    def _send(self, request, runtime):
        # Request headers and payload already come from the official SDK.
        self.started = time.monotonic()
        response = self.session.request(request.method, DaraCore.compose_url(request),
                                        headers=request.headers, data=request.body.encode('utf-8') if isinstance(request.body, str) else request.body,
                                        timeout=(10, 60), stream=True, allow_redirects=False)
        self.response = response
        require(not 300 <= response.status_code < 400, 'RedirectRejected', 'The service returned a redirect; no credentials were forwarded.')
        result = DaraResponse()
        result.status_code = response.status_code
        result.status_message = response.reason
        result.headers = dict(response.headers)
        is_stream = request.headers.get('accept') == 'text/event-stream'
        if response.status_code == 200 and is_stream:
            require(response.headers.get('content-type', '').split(';')[0].strip().lower() == 'text/event-stream',
                    'ContractMismatch', 'Expected a live task stream. Check for a skill update.')
            def bounded_chunks():
                for chunk in response.iter_content(chunk_size=1):
                    require(time.monotonic() - self.started <= 300, 'ObservationTimeout', 'The observation window ended. The cloud task was not cancelled; recover it using its saved identifiers.')
                    yield chunk
            result.body = bounded_chunks()
        else:
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                require(size <= 8 * 1024 * 1024, 'ResponseTooLarge', 'The response exceeds the size limit.')
                chunks.append(chunk)
            result.body = b''.join(chunks)
            response.close()
        return result

    def call(self, action, *, path=None, body=None, query=None, key=None):
        operation = OPERATIONS.get(action, {})
        safe = (operation.get('method') == 'GET' or
                action in IDEMPOTENT_ACTIONS and bool(key) or
                action == 'SendMessage' and (body or {}).get('type') == 'RECONNECT')
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                return self._call_once(action, path=path, body=body, query=query, key=key)
            except ClientError as exc:
                retryable = exc.result['code'] in RETRY_CODES
                if not safe or not retryable or attempt == len(RETRY_DELAYS):
                    exc.result.update(attempts=attempt + 1, retry_exhausted=bool(safe and retryable))
                    raise
                if self.response is not None:
                    self.response.close()
                time.sleep(RETRY_DELAYS[attempt])

    def _call_once(self, action, *, path=None, body=None, query=None, key=None):
        require(action in OPERATIONS, 'UnknownOperation', 'This operation is not in the installed public contract.')
        operation = OPERATIONS[action]
        self.response = None
        pathname = operation['path']
        for name, value in (path or {}).items():
            require(isinstance(value, str) and 0 < len(value) <= 1024, 'InvalidIdentifier', 'A valid resource identifier is required.')
            pathname = pathname.replace('{' + name + '}', quote(value, safe=''))
        require('{' not in pathname, 'MissingIdentifier', 'A resource identifier is required.')
        if action in ('CreateSession', 'CancelRun', 'SendMessage'):
            validate(body or {}, 'api', action + 'Request')
        if action in ('ListMessages', 'ListSessions'):
            logical = {**(path or {}), **(query or {})}
            validate(logical, 'api', action + 'Parameters')
        stream = action == 'SendMessage'
        headers = {'accept': 'text/event-stream' if stream else 'application/json'}
        if key:
            headers['X-OpenAgent-Idempotency-Key'] = key
        params = Params(action=action, version=API_VERSION, protocol='HTTPS', pathname=pathname,
                        method=operation['method'], auth_type='AK', style='ROA',
                        req_body_type='json', body_type='binary' if stream else 'json')
        request = OpenApiRequest(headers=headers, body=body, query={k: str(v) for k, v in (query or {}).items()})
        try:
            with NETWORK_LOCK, patch.object(DaraCore, 'do_action', self._send):
                result = self.client.call_api(params, request, self.runtime)
            require(result.get('statusCode') == 200, 'UnexpectedStatus', 'The service returned an unexpected status.')
            if stream:
                return result['body']
            data = result['body']
            require(isinstance(data, dict), 'ResponseUnavailable',
                    'The service returned no readable response object. Recover the saved task; do not replay a change.')
            require(data.get('success') is not False and not data.get('errorCode'),
                    'ServiceRejected', 'The service reported a failed call.')
            resource = 'message' if action == 'ListMessages' else 'api'
            if action in ('CreateSession', 'GetSession', 'ListSessions', 'ListMessages', 'GetRun', 'CancelRun'):
                diagnostic = inspect_response(data, resource, action + 'Response')
                if diagnostic:
                    # Keep server fields intact, including extensions such as assistant.error.
                    data = CompatibleResponse(data)
                    data.compatibility = {'warning': 'response_shape_difference',
                            'diagnostic': diagnostic,
                            'next_step': 'Use the available data. If this step needs missing information, recover the same task or request the missing detail; do not replay an unconfirmed change.'}
            return data
        except ClientError:
            raise
        except Exception as exc:
            # Never serialize SDK exceptions, request bodies or credential diagnostics.
            exc = getattr(exc, 'inner_exception', exc)
            if isinstance(exc, ClientError):
                raise exc from None
            code = 'NetworkInterrupted' if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)) else getattr(exc, 'code', None)
            error_data = getattr(exc, 'data', None)
            if code in (None, 'None', 'null') and isinstance(error_data, dict):
                code = error_data.get('errorCode')
            safe_code = code if isinstance(code, str) and code not in ('None', 'null') and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,100}', code) else 'TransportFailure'
            if safe_code == 'TransportFailure' and self.response is not None and self.response.status_code in (429, 500, 502, 503, 504):
                safe_code = 'TransientServiceError'
            request_id = getattr(exc, 'request_id', None)
            if request_id is None and isinstance(getattr(exc, 'data', None), dict):
                request_id = exc.data.get('RequestId') or exc.data.get('requestId')
            details = {'request_id': request_id} if isinstance(request_id, str) and re.fullmatch(r'[A-Za-z0-9-]{1,128}', request_id) else {}
            message = 'The call failed; no successful result is available.'
            if safe_code == 'InternalError':
                details['category'] = 'service_error'
                message = 'The service reported an internal error; no successful result is available. This response does not establish a credential or permission problem. If recovery is exhausted, report the error and request reference. Do not change credentials based on this error alone.'
            raise ClientError(safe_code, message, **details) from None
