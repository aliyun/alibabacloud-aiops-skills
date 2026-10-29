"""Official CLI RPC transport for two verified EIAM auxiliary APIs only."""
import re

AUXILIARY = {
    'get-cloud-account-role-config': 'GetCloudAccountRoleConfig',
    'check-cloud-account-role-config': 'CheckCloudAccountRoleConfig',
    'GetCloudAccountRoleConfig': 'GetCloudAccountRoleConfig',
    'CheckCloudAccountRoleConfig': 'CheckCloudAccountRoleConfig',
}
PARAMETERS = {'instance-id':'InstanceId', 'cloud-account-id':'CloudAccountId',
              'cloud-account-role-id':'CloudAccountRoleId', 'InstanceId':'InstanceId',
              'CloudAccountId':'CloudAccountId', 'CloudAccountRoleId':'CloudAccountRoleId'}


def supported_version(text):
    match = re.fullmatch(r'\s*(\d+)\.(\d+)\.(\d+)\s*', text)
    return bool(match and tuple(map(int, match.groups())) >= (3, 5, 2))


def auxiliary_command(cli, action, params, profile):
    if action not in AUXILIARY or set(params) - set(PARAMETERS):
        raise ValueError('Unsupported forced EIAM operation or parameter')
    converted = {PARAMETERS[k]: v for k, v in params.items()}
    if set(converted) != {'InstanceId','CloudAccountId','CloudAccountRoleId'} or len(params) != 3:
        raise ValueError('Exact EIAM role target required')
    if any(not isinstance(v, str) or not v.strip() for v in converted.values()):
        raise ValueError('Missing EIAM role target')
    argv = [cli, 'eiam', AUXILIARY[action]]
    for name in ('InstanceId','CloudAccountId','CloudAccountRoleId'):
        argv += ['--'+name, converted[name]]
    return argv + ['--profile', profile, '--endpoint','eiam.cn-hangzhou.aliyuncs.com',
        '--version','2021-12-01','--read-timeout','20','--connect-timeout','10','--retry-count','0','--force']
