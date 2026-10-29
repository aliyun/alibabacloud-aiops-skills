"""Check selected CLI capabilities; optional official runtime repair, no cloud APIs."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time

from skill_ua import user_agent
from eiam_transport import supported_version

SCOPES = ('setup', 'verification', 'planning', 'inspect-system', 'diagnose', 'resolve-account')
OFFICIAL_PLUGIN_SOURCE = 'https://aliyuncli.alicdn.com/plugins'


def inspect(vendor, finder=shutil.which, runner=subprocess.run, scope='setup', deadline=None):
    if vendor not in ('alibaba_cloud', 'aws', 'tencent_cloud') or scope not in SCOPES:
        raise ValueError('Unsupported vendor or environment scope')
    deadline = deadline if deadline is not None else time.monotonic() + 90
    provider = {'alibaba_cloud':'aliyun', 'aws':'aws', 'tencent_cloud':'tccli'}[vendor]
    required = list(dict.fromkeys(('aliyun', provider)))
    resolved = {name: finder(name) for name in required}
    missing = [name for name, path in resolved.items() if not path]
    result = {'status':'environment_required', 'vendor':vendor, 'environment_scope':scope,
              'selected_provider_cli':provider, 'missing_clis':missing,
              'missing_capabilities':[], 'cloud_calls_performed':False,
              'configuration_performed':False, 'eiam_commands':{}}
    if missing:
        return result
    env = dict(os.environ, ALIBABA_CLOUD_USER_AGENT=user_agent())
    def local(argv, timeout):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, 0)
        return runner(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding='utf-8', errors='replace', shell=False, timeout=min(timeout, remaining), env=env)
    try:
        version = local([resolved['aliyun'], 'version'], 15)
        force_available = version.returncode == 0 and supported_version(version.stdout)
        result['aliyun_version'] = version.stdout.strip() if version.returncode == 0 else None
    except (subprocess.TimeoutExpired, OSError):
        force_available = False
    result['auxiliary_transport'] = 'official_force_rpc' if force_available else None
    if scope == 'resolve-account':
        actions = ('ListCloudAccounts',)
    elif scope == 'inspect-system':
        actions = ('ListCloudAccountRoles', 'GetCloudAccountRole')
    elif scope == 'diagnose':
        actions = ('GetInstance', 'GetCloudAccount')
    else:
        actions = ('GetInstance', 'ListCloudAccounts', 'GetCloudAccount',
                   'ListCloudAccountRoles', 'GetCloudAccountRole')
        if scope == 'setup':
            actions += ('CreateCloudAccountRole',)
        if scope in ('setup', 'verification'):
            actions += ('GetCloudAccountRoleConfig', 'CheckCloudAccountRoleConfig')
    probes = []
    for action in actions:
        if action in ('GetCloudAccountRoleConfig', 'CheckCloudAccountRoleConfig'):
            if force_available:
                result['eiam_commands'][action] = action
            else:
                result['missing_capabilities'].append(action)
        else:
            probes.append(('eiam', re.sub(r'(?<!^)(?=[A-Z])', '-', action).lower(), action))
    probes.append(('sts', 'get-caller-identity', 'sts:get-caller-identity'))
    if vendor == 'alibaba_cloud' and scope not in ('inspect-system', 'diagnose', 'resolve-account'):
        probes += [('ram', op, 'ram:'+op) for op in
                   ('get-role','get-policy','get-policy-version','list-policies-for-role')]
        probes.append(('ims', 'get-oidc-provider', 'ims:get-oidc-provider'))
        if scope == 'setup':
            probes += [('ram', op, 'ram:'+op) for op in ('create-role','attach-policy-to-role','update-role')]
    for product, command, label in probes:
        try:
            completed = local([resolved['aliyun'], product, command, '--help'], 30)
            output = (completed.stdout + completed.stderr).lower()
            available = completed.returncode == 0 and not any(marker in output for marker in
                ('not a valid api', 'not a valid built-in command', 'not installed', 'unknown command'))
        except (subprocess.TimeoutExpired, OSError):
            available = False
        if not available:
            result['missing_capabilities'].append(label)
        elif product == 'eiam':
            result['eiam_commands'][label] = command
    result['status'] = 'cli_capabilities_available' if not result['missing_capabilities'] else 'environment_required'
    result['identity_verified'] = False
    return result


def repair(vendor, scope='setup', finder=shutil.which, runner=subprocess.run):
    """Repair missing official CLI packages before API calls; never touch credentials."""
    deadline = time.monotonic() + 300
    result = inspect(vendor, finder, runner, scope, deadline)
    commands = []
    if result['status'] == 'cli_capabilities_available' or result['missing_clis']:
        return result
    cli = finder('aliyun')
    env = dict(os.environ, ALIBABA_CLOUD_USER_AGENT=user_agent())
    def command(argv, maximum):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, 0)
        return runner(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            encoding='utf-8', errors='replace', shell=False, timeout=min(maximum, remaining), env=env)
    try:
        if not supported_version(result.get('aliyun_version') or ''):
            argv = [cli, 'upgrade', '--yes']
            commands.append(argv)
            if command(argv, 120).returncode:
                raise ValueError('Official CLI upgrade failed')
            result = inspect(vendor, finder, runner, scope, deadline)
        products = sorted({value.split(':')[0] if ':' in value else 'eiam'
                           for value in result['missing_capabilities']})
        for product in products:
            if product not in ('eiam', 'sts', 'ram', 'ims'):
                raise ValueError('Unsupported runtime dependency')
            name = 'aliyun-cli-' + product
            installed = command([cli, 'plugin', 'show', '--name', name], 15)
            argv = [cli, 'plugin', 'update' if installed.returncode == 0 else 'install',
                    '--name', name, '--source-base', OFFICIAL_PLUGIN_SOURCE]
            commands.append(argv)
            if command(argv, 90).returncode:
                raise ValueError('Official plugin repair failed')
        result = inspect(vendor, finder, runner, scope, deadline)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result['runtime_repair_error'] = type(exc).__name__
        result['status'] = 'environment_required'
    result.update(configuration_performed=bool(commands), runtime_repair_commands=commands,
                  cloud_calls_performed=False, credential_configuration_performed=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor', required=True, choices=('alibaba_cloud', 'aws', 'tencent_cloud'))
    parser.add_argument('--scope', choices=SCOPES, default='setup')
    parser.add_argument('--repair', action='store_true', help='Repair only missing official runtime packages; no credential setup')
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        result = repair(args.vendor, args.scope) if args.repair else inspect(args.vendor, scope=args.scope)
        if args.output:
            with Path(args.output).open('x', encoding='utf-8') as handle:
                json.dump(result, handle, indent=2)
        print(json.dumps(result))
        return 0 if result['status'] == 'cli_capabilities_available' else 2
    except (OSError, ValueError, KeyError):
        print(json.dumps({'status':'environment_check_failed', 'cloud_calls_performed':False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
