#!/usr/bin/env python3
"""Create Python deployments and query the metadata needed for creation.

Upload artifacts through VVP File Management or aliyun ossutil, according to
get-storage-mode. Use get-deployment to verify the newly created configuration.
For operations on deployed jobs, use alibabacloud-flink-workspace-ops.
"""

import argparse
import copy
import json
import os
import re
import secrets
import sys
from pathlib import Path

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_foasconsole20211028.client import Client as FoasConsoleClient
from alibabacloud_foasconsole20211028 import models as foasconsole_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

SKILL_NAME = 'alibabacloud-flink-python-job-submission'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', secrets.token_hex(16))
MANIFEST_PATH = Path(__file__).resolve().parents[1] / 'references' / 'manifest.json'
API_VERSION = '2022-07-18'
CONNECT_TIMEOUT_MS = 10_000
READ_TIMEOUT_MS = 60_000
SENSITIVE_KEY_FRAGMENTS = (
    'accesskey', 'credential', 'password', 'passwd', 'privatekey', 'secret', 'token',
    'authorization', 'cookie',
)
REDACTED_VALUE = '***REDACTED***'


def _build_user_agent():
    """Validate local observability metadata before any cloud request."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        version = manifest.get('version') if isinstance(manifest, dict) else None
        if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]*', version):
            raise ValueError('version must be a non-empty user-agent token')
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'Cannot read a valid skill version from {MANIFEST_PATH}: {exc}') from exc
    if not re.fullmatch(r'[0-9a-f]{32}', SESSION_ID):
        raise ValueError('SKILL_SESSION_ID must be 32 lowercase hexadecimal characters')
    return f'AlibabaCloud-Agent-Skills/{SKILL_NAME}/{SESSION_ID} skill-version/{version}'


def create_client(region):
    """Create an OpenAPI client for the Ververica endpoint in *region*."""
    user_agent = _build_user_agent()
    credential = CredentialClient()
    endpoint = f'ververica.{region}.aliyuncs.com'
    config = open_api_models.Config(
        credential=credential,
        endpoint=endpoint,
        user_agent=user_agent,
    )
    return OpenApiClient(config)


def create_workspace_client(region):
    """Create a selling-console client for workspace metadata queries."""
    user_agent = _build_user_agent()
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint='foasconsole.aliyuncs.com',
        region_id=region,
        user_agent=user_agent,
    )
    return FoasConsoleClient(config)


def _runtime_options():
    """Build bounded runtime options shared by every SDK request."""
    return util_models.RuntimeOptions(
        connect_timeout=CONNECT_TIMEOUT_MS,
        read_timeout=READ_TIMEOUT_MS,
    )


def call_api(
    client,
    *,
    action,
    method,
    pathname,
    workspace,
    body=None,
):
    """ROA API call with an explicit action and workspace header.

    Args:
        client:    Initialised OpenApiClient.
        action:    Ververica OpenAPI action for this operation.
        method:    HTTP method (GET, POST, ...).
        pathname:  ROA path, e.g. ``/api/v2/namespaces/ns1/deployments``.
        workspace: Workspace identifier injected into the request header.
        body:      Optional JSON-serialisable request body (dict).

    Returns:
        The raw response dict from the SDK (keys: statusCode, headers, body).
    """
    params = open_api_models.Params(
        action=action,
        version=API_VERSION,
        protocol='HTTPS',
        method=method,
        auth_type='AK',
        style='ROA',
        pathname=pathname,
        req_body_type='json',
        body_type='json',
    )

    headers = {'workspace': workspace}

    request_kwargs = {'headers': headers}
    if body is not None:
        request_kwargs['body'] = body

    request = open_api_models.OpenApiRequest(**request_kwargs)
    runtime = _runtime_options()
    return client.call_api(params, request, runtime)


def _print_response(response):
    """Pretty-print an API response to stdout."""
    print(json.dumps(response, indent=2, ensure_ascii=False, default=str))


def _response_body(response, operation):
    """Return a successful dictionary response body or reject ambiguity."""
    if not isinstance(response, dict):
        raise TypeError(f'{operation} returned a non-dictionary response')
    body = response.get('body')
    if not isinstance(body, dict):
        raise TypeError(f'{operation} returned no dictionary body')
    if body.get('success') is False:
        raise RuntimeError(
            f'{operation} returned success=false: '
            f'{body.get("errorCode")}: {body.get("errorMessage")}'
        )
    return body


def _parse_list_arg(value):
    """Split a comma-separated string into a list, stripping whitespace."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _non_empty_arg(value):
    """Return a stripped CLI value or reject an empty argument."""
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError('value must not be empty')
    return value


def _reject_duplicate_json_keys(pairs):
    """Build a JSON object while rejecting duplicate keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key!r}')
        result[key] = value
    return result


def _load_json_document(value, *, allow_at_file, description):
    """Load one strict JSON document from a CLI value or an @file."""
    source = value
    if allow_at_file and value.startswith('@'):
        path = value[1:]
        if not path or path == '-':
            raise argparse.ArgumentTypeError(
                f'{description} @file must name a JSON file'
            )
        try:
            with open(os.path.expanduser(path), encoding='utf-8') as handle:
                source = handle.read()
        except OSError as exc:
            raise argparse.ArgumentTypeError(
                f'cannot read {description} file {path!r}: {exc}'
            ) from exc

    try:
        return json.loads(
            source,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            f'{description} must be valid JSON: {exc}'
        ) from exc


def _flink_conf_arg(value):
    """Parse one complete Flink configuration JSON object or @file."""
    result = _load_json_document(
        value,
        allow_at_file=True,
        description='Flink configuration',
    )
    if not isinstance(result, dict):
        raise argparse.ArgumentTypeError(
            'Flink configuration must be a JSON object'
        )
    for key, config_value in result.items():
        if not isinstance(key, str) or not key:
            raise argparse.ArgumentTypeError(
                'Flink configuration keys must be non-empty strings'
            )
        if not isinstance(config_value, str):
            raise argparse.ArgumentTypeError(
                'Flink configuration values must be strings'
            )
    return result


class _StoreOnceAction(argparse.Action):
    """Store one option value and reject a second occurrence."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(namespace, self.dest, None) is not None:
            parser.error(f'{option_string} may be specified only once')
        setattr(namespace, self.dest, values)


def _exit_api_error(operation, exc, expected, parameters, remediation):
    """Print actionable, non-secret API failure context and exit."""
    parameter_text = ', '.join(
        f'{name}={value!r}' for name, value in parameters.items()
    )
    print(
        f'Error during {operation}.\n'
        f'Expected: {expected}.\n'
        f'Parameters: {parameter_text}.\n'
        f'Request timeouts: connect={CONNECT_TIMEOUT_MS} ms, '
        f'read={READ_TIMEOUT_MS} ms.\n'
        f'Actual: {type(exc).__name__}: {exc}\n'
        f'How to fix: {remediation}',
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


def _workspace_identifiers(instance):
    """Return the sales and VVP identifiers exposed for an instance."""
    cluster_state = getattr(instance, 'cluster_state', None)
    cluster_stage = getattr(cluster_state, 'cluster_stage', None)
    cluster_used_storage = getattr(instance, 'cluster_used_storage', None)
    cluster_used_resources = getattr(instance, 'cluster_used_resources', None)
    identifiers = {
        getattr(instance, 'instance_id', None),
        getattr(instance, 'ask_cluster_id', None),
        getattr(cluster_state, 'cluster_id', None),
        getattr(cluster_stage, 'cluster_id', None),
        getattr(cluster_used_storage, 'cluster_id', None),
        getattr(cluster_used_resources, 'cluster_id', None),
    }
    return {identifier for identifier in identifiers if identifier}


def _storage_result(instance, workspace):
    """Build storage routing and console metadata for a matched workspace."""
    cluster_state = getattr(instance, 'cluster_state', None)
    console_url = getattr(cluster_state, 'url', None)
    if not console_url:
        raise RuntimeError(
            'DescribeInstances returned no ClusterState.Url for the matched '
            'workspace'
        )
    console_url = console_url.rstrip('/')

    storage = getattr(instance, 'storage', None)
    fully_managed = getattr(storage, 'fully_managed', None)
    if fully_managed is True:
        return {
            'workspace': workspace,
            'instanceId': getattr(instance, 'instance_id', None),
            'consoleUrl': console_url,
            'storageMode': 'FULLY_MANAGED',
            'ossBucket': None,
        }

    oss = getattr(storage, 'oss', None)
    bucket = getattr(oss, 'bucket', None)
    if fully_managed is False and bucket:
        return {
            'workspace': workspace,
            'instanceId': getattr(instance, 'instance_id', None),
            'consoleUrl': console_url,
            'storageMode': 'USER_MANAGED_OSS',
            'ossBucket': bucket,
        }

    raise RuntimeError(
        'DescribeInstances returned an incomplete storage configuration: '
        f'FullyManaged={fully_managed!r}, Oss.Bucket={bucket!r}'
    )


def _engine_version_result(body, workspace):
    """Return the workspace default engine version."""
    data = body.get('data')
    if not isinstance(data, dict):
        raise TypeError('ListEngineVersionMetadata returned no dictionary data')
    metadata = data.get('engineVersionMetadata') or []
    if not isinstance(metadata, list):
        raise TypeError(
            'ListEngineVersionMetadata returned non-list engine metadata'
        )

    for item in metadata:
        if not isinstance(item, dict):
            raise TypeError(
                'ListEngineVersionMetadata returned a non-dictionary item'
            )

    default_engine_version = data.get('defaultEngineVersion')
    if not (
        isinstance(default_engine_version, str)
        and default_engine_version.strip()
    ):
        raise RuntimeError(
            'ListEngineVersionMetadata returned no defaultEngineVersion'
        )

    return {
        'workspace': workspace,
        'defaultEngineVersion': default_engine_version,
        'selectionBasis': 'OPENAPI_DEFAULT_ENGINE_VERSION',
        'engineVersionMetadata': metadata,
    }


def _deployment_data(response, operation):
    """Extract one deployment object from a successful API response."""
    body = _response_body(response, operation)
    deployment = body.get('data')
    if not isinstance(deployment, dict):
        raise TypeError(f'{operation} returned no deployment data object')
    return deployment


def _is_sensitive_key(key):
    """Identify configuration keys whose values must not be printed."""
    normalized = re.sub(r'[^a-z0-9]', '', str(key).lower())
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def _redact_sensitive(value):
    """Recursively redact values selected by sensitive key names."""
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)

    named_key = value.get('name', value.get('key'))
    named_value_is_sensitive = (
        isinstance(named_key, str) and _is_sensitive_key(named_key)
    )
    result = {}
    for key, item in value.items():
        if _is_sensitive_key(key) or (
            named_value_is_sensitive
            and str(key).lower() in {'value', 'defaultvalue'}
        ):
            result[key] = REDACTED_VALUE
        else:
            result[key] = _redact_sensitive(item)
    return result


def cmd_get_storage_mode(args):
    """Detect workspace storage and console URL through DescribeInstances."""
    try:
        client = create_workspace_client(args.region)
        page_index = 1
        matches = []
        while True:
            request = foasconsole_models.DescribeInstancesRequest(
                region=args.region,
                page_index=page_index,
                page_size=100,
            )
            response = client.describe_instances_with_options(
                request,
                _runtime_options(),
            )
            body = response.body
            if body.success is False:
                raise RuntimeError('DescribeInstances returned Success=false')

            for instance in body.instances or []:
                if args.workspace in _workspace_identifiers(instance):
                    matches.append(instance)

            if page_index >= (body.total_page or 1):
                break
            page_index += 1

        if len(matches) != 1:
            raise LookupError(
                'expected exactly one DescribeInstances result for the '
                f'supplied workspace ID, found {len(matches)}'
            )
        _print_response(_storage_result(matches[0], args.workspace))
    except Exception as exc:
        _exit_api_error(
            'get-storage-mode',
            exc,
            'one workspace with an explicit console URL and FULLY_MANAGED or '
            'USER_MANAGED_OSS storage mode',
            {
                'region': args.region,
                'workspace': args.workspace,
                'namespace': args.namespace,
            },
            'Verify that --workspace is the VVP workspace/cluster ID from the '
            'console URL or the sales instance ID, verify --region and '
            'confirm stream:DescribeVvpInstances permission. Also confirm the '
            'matched instance exposes ClusterState.Url. The namespace is used '
            'for artifact routing after detection, not as an API filter.',
        )


def cmd_list_engine_versions(args):
    """List engine versions and return the workspace default one."""
    try:
        client = create_client(args.region)
        response = call_api(
            client,
            action='ListEngineVersionMetadata',
            method='GET',
            pathname='/api/v2/engine-version-meta.json',
            workspace=args.workspace,
        )
        body = _response_body(response, 'ListEngineVersionMetadata')
        _print_response(_engine_version_result(body, args.workspace))
    except Exception as exc:
        _exit_api_error(
            'list-engine-versions',
            exc,
            'workspace-supported engine metadata with a non-empty '
            'defaultEngineVersion',
            {
                'region': args.region,
                'workspace': args.workspace,
            },
            'Verify the workspace and region, confirm the caller has '
            'stream:ListEngineVersionMetadata permission, and confirm the '
            'response contains defaultEngineVersion.',
        )


def cmd_create_deployment(args):
    """Create a Flink Python deployment."""
    flink_conf = getattr(args, 'flink_conf', None)
    python_artifact = {
        'pythonArtifactUri': args.artifact_uri,
        'entryModule': args.entry_module,
        'mainArgs': args.main_args,
        'additionalDependencies': _parse_list_arg(args.additional_deps),
        'additionalPythonLibraries': _parse_list_arg(args.libraries),
        'additionalPythonArchives': _parse_list_arg(args.archives),
    }

    body = {
        'name': args.name,
        'executionMode': args.execution_mode,
        'engineVersion': args.flink_version,
        'artifact': {
            'kind': 'PYTHON',
            'pythonArtifact': python_artifact,
        },
        'deploymentTarget': {
            'mode': 'PER_JOB',
            'name': args.resource_queue,
        },
        'streamingResourceSetting': {
            'resourceSettingMode': 'BASIC',
            'basicResourceSetting': {
                'parallelism': int(args.parallelism),
                'jobmanagerResourceSettingSpec': {
                    'cpu': float(args.jm_cpu),
                    'memory': args.jm_memory,
                },
                'taskmanagerResourceSettingSpec': {
                    'cpu': float(args.tm_cpu),
                    'memory': args.tm_memory,
                },
            },
        },
    }
    if flink_conf is not None:
        body['flinkConf'] = copy.deepcopy(flink_conf)

    pathname = f'/api/v2/namespaces/{args.namespace}/deployments'
    response = None

    try:
        client = create_client(args.region)
        response = call_api(
            client,
            action='CreateDeployment',
            method='POST',
            pathname=pathname,
            workspace=args.workspace,
            body=body,
        )
        deployment = _deployment_data(response, 'CreateDeployment')
        deployment_id = deployment.get('deploymentId')
        if not isinstance(deployment_id, str) or not deployment_id.strip():
            raise RuntimeError(
                'CreateDeployment returned no usable deploymentId; '
                'creation outcome is unknown'
            )
        _print_response(_redact_sensitive(response))
    except Exception as exc:
        if response is not None:
            print('CreateDeployment response (sensitive values redacted):', file=sys.stderr)
            print(json.dumps(_redact_sensitive(response), indent=2, ensure_ascii=False,
                             default=str), file=sys.stderr)
        _exit_api_error(
            'create-deployment',
            exc,
            'a new PYTHON deployment response',
            {
                'region': args.region,
                'workspace': args.workspace,
                'namespace': args.namespace,
                'name': args.name,
                'artifact_uri': args.artifact_uri,
                'resource_queue': args.resource_queue,
                'flink_version': args.flink_version,
                'execution_mode': args.execution_mode,
                'jm_memory': args.jm_memory,
                'tm_memory': args.tm_memory,
                'flink_conf_keys': sorted(flink_conf or {}),
            },
            'Verify the artifact URI exists in the selected workspace storage, '
            'the confirmed resource queue exists, the engine version and '
            'resource settings are supported, and the caller has '
            'stream:CreateDeployment permission. A response parsing error or '
            'timeout does not prove creation failed. Inspect the response and '
            'check for an existing deployment in the confirmed workspace and '
            'namespace before retrying; do not create a duplicate.',
        )


def cmd_get_deployment(args):
    """Read back a newly created deployment for configuration verification."""
    pathname = (
        f'/api/v2/namespaces/{args.namespace}'
        f'/deployments/{args.deployment_id}'
    )

    try:
        client = create_client(args.region)
        response = call_api(
            client,
            action='GetDeployment',
            method='GET',
            pathname=pathname,
            workspace=args.workspace,
        )
        _deployment_data(response, 'GetDeployment')
        _print_response(_redact_sensitive(response))
    except Exception as exc:
        _exit_api_error(
            'get-deployment',
            exc,
            'the requested deployment details',
            {
                'region': args.region,
                'workspace': args.workspace,
                'namespace': args.namespace,
                'deployment_id': args.deployment_id,
            },
            'Verify the workspace, namespace, and deployment ID, and confirm '
            'the caller has stream:GetDeployment permission.',
        )


def build_parser():
    """Build the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description='Create Flink Python deployments and verify their configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available subcommands')

    # -- Common arguments -----------------------------------------------------
    def add_workspace_args(sub):
        sub.add_argument('--workspace', required=True,
                         help='VVP workspace/cluster or sales instance ID')
        sub.add_argument('--region', required=True,
                         help='Alibaba Cloud region (e.g. cn-shanghai)')

    def add_common_args(sub):
        add_workspace_args(sub)
        sub.add_argument('--namespace', required=True,
                         help='Ververica namespace')

    def add_flink_conf_arg(sub):
        sub.add_argument(
            '--flink-conf',
            action=_StoreOnceAction,
            type=_flink_conf_arg,
            default=None,
            metavar='JSON_OR_@FILE',
            help=(
                'Complete Flink configuration JSON object or @JSON-file; '
                'may be specified once'
            ),
        )

    # -- get-storage-mode ----------------------------------------------------
    sp = subparsers.add_parser(
        'get-storage-mode',
        help='Get storage mode and exact VVP console URL',
    )
    add_common_args(sp)
    sp.set_defaults(func=cmd_get_storage_mode)

    # -- list-engine-versions -----------------------------------------------
    sp = subparsers.add_parser(
        'list-engine-versions',
        help=(
            'List workspace-supported engine versions and return '
            'defaultEngineVersion'
        ),
    )
    add_workspace_args(sp)
    sp.set_defaults(func=cmd_list_engine_versions)

    # -- create-deployment ----------------------------------------------------
    sp = subparsers.add_parser('create-deployment',
                               help='Create a Flink Python deployment')
    add_common_args(sp)
    sp.add_argument('--name', required=True,
                    help='Deployment name')
    sp.add_argument('--artifact-uri', required=True,
                    help='Verified canonical Python artifact URI')
    sp.add_argument('--entry-module', default='',
                    help='Entry module (default: "")')
    sp.add_argument('--main-args', default='',
                    help='Main arguments string (default: "")')
    sp.add_argument('--flink-version', required=True, type=_non_empty_arg,
                    help='Resolved Flink engine version')
    sp.add_argument('--execution-mode', default='STREAMING',
                    choices=['STREAMING', 'BATCH'],
                    help='Execution mode (default: STREAMING)')
    sp.add_argument(
        '--resource-queue',
        required=True,
        type=_non_empty_arg,
        help='User-confirmed deployment resource queue '
             '(suggested value: default-queue)',
    )
    sp.add_argument('--libraries', default=None,
                    help='Comma-separated artifact URIs for Python libraries')
    sp.add_argument('--archives', default=None,
                    help='Comma-separated artifact URIs for Python archives')
    sp.add_argument('--additional-deps', default=None,
                    help='Comma-separated artifact URIs for dependencies')
    add_flink_conf_arg(sp)
    sp.add_argument('--jm-cpu', default='1',
                    help='JobManager CPU cores (default: 1)')
    sp.add_argument('--jm-memory', default='4g',
                    help='JobManager memory in API format (default: 4g)')
    sp.add_argument('--tm-cpu', default='1',
                    help='TaskManager CPU cores (default: 1)')
    sp.add_argument('--tm-memory', default='4g',
                    help='TaskManager memory in API format (default: 4g)')
    sp.add_argument('--parallelism', default='1',
                    help='Job parallelism (default: 1)')
    sp.set_defaults(func=cmd_create_deployment)

    # -- get-deployment -------------------------------------------------------
    sp = subparsers.add_parser('get-deployment',
                               help='Read back the newly created deployment for verification')
    add_common_args(sp)
    sp.add_argument('--deployment-id', required=True,
                    help='Deployment ID')
    sp.set_defaults(func=cmd_get_deployment)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
