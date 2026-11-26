"""Send allowlisted read-only RPC requests through the official SDK or aliyun CLI."""

import json
import os
import random
import re
import time

from context_graph_contract import (SkillError, endpoint_allowlist, resolve_endpoint,
                                    safe_output, validate_request, validate_response)
from context_graph_observability import user_agent, validate_session_id
from context_graph_cli_transport import AliyunCliTransport, validate_backend


def _metadata(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value) else None


def _exception_chain(error):
    visited = set()
    while error is not None and id(error) not in visited:
        visited.add(id(error))
        yield error
        error = getattr(error, "inner_exception", None) or error.__cause__ or error.__context__


def classify_error(error):
    """Never expose raw SDK exceptions, which may contain headers, signed URLs, or credentials."""
    from requests.exceptions import ConnectionError, SSLError, Timeout, TooManyRedirects

    chain = list(_exception_chain(error))
    if any(isinstance(item, TooManyRedirects) for item in chain):
        return SkillError("RedirectRejected", "The service returned a redirect; the request stopped. Check region and service configuration.")
    if any(isinstance(item, SSLError) for item in chain):
        return SkillError("TlsError", "TLS certificate verification failed; the request stopped.")
    for item in chain:
        code = _metadata(getattr(item, "code", None))
        request_id = _metadata(getattr(item, "request_id", None))
        status = getattr(item, "status_code", None)
        if code:
            transient = code.lower().startswith(("throttl", "serviceunavailable")) or status in (429, 503)
            return SkillError(code, "OpenAPI call failed; use the error code to check parameters, credentials, permissions, or service status.",
                              request_id=request_id, retryable=transient)
    if any(isinstance(item, (Timeout, ConnectionError)) for item in chain):
        return SkillError("TransportUnavailable", "Service connection or read temporarily failed.", retryable=True)
    return SkillError("SdkError", "SDK call failed; check pinned dependencies, network, and credential configuration.")


class OpenApiTransport:
    def __init__(self, region, access_key_id, access_key_secret, security_token=None, *, endpoint=None,
                 session_id=None, allowed_hosts=()):
        endpoint = resolve_endpoint(region, endpoint, allowed_hosts=allowed_hosts)
        attribution = user_agent(session_id)
        try:
            from alibabacloud_tea_openapi.client import Client
            from alibabacloud_tea_openapi.models import Config, OpenApiRequest, Params
            from alibabacloud_tea_util.models import RuntimeOptions
            from darabonba.core import DaraCore
            from darabonba.policy.retry import RetryOptions
            from darabonba.request import DaraRequest
        except ImportError:
            raise SkillError("DependencyMissing", "Install the pinned SDK dependencies from scripts/requirements.txt first.") from None
        # Use only the validated endpoint so SDK suffix variables cannot rewrite it or bypass session guards.
        config = Config(access_key_id=access_key_id, access_key_secret=access_key_secret,
                        security_token=security_token, region_id=region, endpoint=endpoint,
                        endpoint_suffix="aliyuncs.com", protocol="HTTPS", max_idle_conns=1,
                        retry_options=RetryOptions(retryable=False),
                        user_agent=attribution)
        self.client = Client(config)
        self.Params, self.Request = Params, OpenApiRequest
        self.runtime = RuntimeOptions(autoretry=False, max_attempts=1, connect_timeout=10000,
                                      read_timeout=65000, max_idle_conns=1, ignore_ssl=False)
        # The pinned SDK uses cached sessions; reject every redirect for the selected endpoint.
        session_key = f"https://{endpoint}:{DaraRequest().port}:pool=1:ipv4Only=False"
        self.session = DaraCore._get_session(session_key=session_key, protocol="HTTPS", verify=True, pool_size=1)
        self.session.max_redirects = 0

    def call(self, action, parameters):
        parameters = validate_request(action, parameters)
        body = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                for key, value in parameters.items()}
        params = self.Params(action=action, version="2024-05-18", protocol="HTTPS", pathname="/",
                             method="POST", auth_type="AK", style="RPC", req_body_type="formData", body_type="json")
        response = self.client.call_api(params, self.Request(body=body), self.runtime)
        return response.get("body") if isinstance(response, dict) else None


class ContextGraphClient:
    def __init__(self, region, *, environ=None, transport=None, sleep=time.sleep, jitter=random.random,
                 backend="sdk", profile=None):
        validate_backend(backend, profile)
        self.backend, self.profile = backend, profile
        self.environ = os.environ if environ is None else environ
        self.allowed_hosts = endpoint_allowlist(self.environ)
        self.endpoint = resolve_endpoint(region, self.environ.get("DATAWORKS_ENDPOINT"),
                                         allowed_hosts=self.allowed_hosts)
        self.region = region
        self.transport = transport
        self.sleep, self.jitter = sleep, jitter
        self.secrets = tuple(self.environ.get(key, "") for key in (
            "ALIBABA_CLOUD_ACCESS_KEY_ID", "ALIBABA_CLOUD_ACCESS_KEY_SECRET", "ALIBABA_CLOUD_SECURITY_TOKEN"))

    def _transport(self):
        if str(self.environ.get("DEBUG", "")).lower() == "sdk" or os.environ.get("DEBUG", "").lower() == "sdk":
            raise SkillError("UnsafeDebugConfiguration", "Disable DEBUG=sdk; that mode may log credentials and signatures.")
        if self.transport is None:
            if self.backend == "aliyun":
                session_id = (validate_session_id(self.environ["SKILL_SESSION_ID"])
                              if "SKILL_SESSION_ID" in self.environ else None)
                self.transport = AliyunCliTransport(self.region, environ=self.environ, profile=self.profile,
                                                   endpoint=self.endpoint, session_id=session_id)
                return self.transport
            access_key, secret, token = self.secrets
            if not access_key or not access_key.strip() or not secret or not secret.strip() or (token and not token.strip()):
                raise SkillError("CredentialsMissing", "Configure a valid AccessKey ID and Secret in the environment; temporary credentials also require SecurityToken.")
            session_id = (validate_session_id(self.environ["SKILL_SESSION_ID"])
                          if "SKILL_SESSION_ID" in self.environ else None)
            self.transport = OpenApiTransport(self.region, access_key, secret, token or None,
                                              endpoint=self.endpoint, session_id=session_id,
                                              allowed_hosts=self.allowed_hosts)
        return self.transport

    def invoke(self, action, parameters, *, include_source_urls=False):
        params = validate_request(action, parameters)
        transport = self._transport()
        for attempt in range(3):
            try:
                payload = transport.call(action, params)
                if isinstance(payload, dict) and payload.get("Success") is not True and payload.get("Code"):
                    code = _metadata(payload.get("Code")) or "BusinessError"
                    raise SkillError(code, "OpenAPI returned a business error; check its error code.",
                                     request_id=_metadata(payload.get("RequestId")),
                                     retryable=code.lower().startswith(("throttl", "serviceunavailable")))
                validate_response(action, params, payload)
                result = dict(payload)
                result["Action"] = action
                return safe_output(result, self.secrets, include_source_urls=include_source_urls)
            except SkillError as error:
                failure = error
            except Exception as error:
                failure = classify_error(error)
            if not failure.retryable or attempt == 2:
                # The caller sanitizes the full output again in case an untrusted RequestId contains credentials.
                raise failure from None
            self.sleep((2 ** attempt) + self.jitter())
