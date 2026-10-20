"""Select one official SDK credential provider without a fallback chain."""
import os
from .common import require, ClientError

SOURCES = ('environment', 'cli-profile', 'sdk-profile', 'oidc', 'ecs-role', 'credentials-uri')
ENVIRONMENT = {
    'environment': ['ALIBABA_CLOUD_ACCESS_KEY_ID', 'ALIBABA_CLOUD_ACCESS_KEY_SECRET', 'ALIBABA_CLOUD_SECURITY_TOKEN'],
    'oidc': ['ALIBABA_CLOUD_ROLE_ARN', 'ALIBABA_CLOUD_OIDC_PROVIDER_ARN', 'ALIBABA_CLOUD_OIDC_TOKEN_FILE', 'ALIBABA_CLOUD_ROLE_SESSION_NAME'],
    'ecs-role': ['ALIBABA_CLOUD_ECS_METADATA', 'ALIBABA_CLOUD_IMDSV1_DISABLED'],
    'credentials-uri': ['ALIBABA_CLOUD_CREDENTIALS_URI'],
    'sdk-profile': ['ALIBABA_CLOUD_CREDENTIALS_FILE'],
    'cli-profile': [],
}


def validate_source(source):
    require(isinstance(source, dict) and source.get('kind') in SOURCES, 'InvalidCredentialSource', 'Choose a supported credential source.')
    require(not (set(source) - {'kind', 'profile', 'file'}), 'InvalidCredentialSource', 'Credential values must not be stored in skill settings.')
    if source['kind'].endswith('profile'):
        require(bool(source.get('profile')), 'ProfileRequired', 'Choose an explicit named profile.')
    else:
        require(set(source) == {'kind'}, 'InvalidCredentialSource', 'This source uses its standard environment or workload configuration.')


def create_credentials(source):
    validate_source(source)
    from alibabacloud_credentials.client import Client
    from alibabacloud_credentials.provider.env import EnvironmentVariableCredentialsProvider
    from alibabacloud_credentials.provider.cli_profile import CLIProfileCredentialsProvider
    from alibabacloud_credentials.provider.profile import ProfileCredentialsProvider
    from alibabacloud_credentials.provider.oidc import OIDCRoleArnCredentialsProvider
    from alibabacloud_credentials.provider.ecs_ram_role import EcsRamRoleCredentialsProvider
    from alibabacloud_credentials.provider.uri import URLCredentialsProvider
    kind = source['kind']
    try:
        if kind == 'environment':
            require(all(os.environ.get(k) for k in ENVIRONMENT[kind][:2]), 'CredentialsMissing', 'Set the complete access key pair in the local environment.')
            provider = EnvironmentVariableCredentialsProvider()
        elif kind == 'cli-profile':
            provider = CLIProfileCredentialsProvider(profile_name=source['profile'], profile_file=source.get('file'))
        elif kind == 'sdk-profile':
            provider = ProfileCredentialsProvider(profile_name=source['profile'], profile_file=source.get('file'))
        elif kind == 'oidc':
            provider = OIDCRoleArnCredentialsProvider()
        elif kind == 'ecs-role':
            provider = EcsRamRoleCredentialsProvider(disable_imds_v1=True)
        else:
            require(bool(os.environ.get('ALIBABA_CLOUD_CREDENTIALS_URI')), 'CredentialsMissing', 'Set the credentials URI in the local environment.')
            provider = URLCredentialsProvider(uri=os.environ['ALIBABA_CLOUD_CREDENTIALS_URI'])
        client = Client(provider=provider)
        client.get_credential()
        return client
    except ClientError:
        raise
    except Exception:
        raise ClientError('CredentialsUnavailable', 'The selected credential source could not be resolved. Repair it locally; no other source was tried.') from None


def inspect_presence():
    """Inspect known locations and variable presence only; do not resolve providers."""
    from pathlib import Path
    variables = {key: bool(os.environ.get(key)) for names in ENVIRONMENT.values() for key in names}
    profiles = {'cli': (Path.home() / '.aliyun/config.json').is_file(),
                'sdk': Path(os.environ.get('ALIBABA_CLOUD_CREDENTIALS_FILE') or Path.home() / '.alibabacloud/credentials').is_file()}
    pair = [variables[key] for key in ENVIRONMENT['environment'][:2]]
    return {'ok': True, 'identity_verification': 'not_performed',
            'message': 'This check reports local credential presence only. It does not contact the cloud or determine whether credentials are valid. No identity verification was attempted or failed.',
            'environment': variables,
            'profile_files': profiles,
            'source_summary': {'environment': 'present_not_verified' if all(pair) else 'incomplete' if any(variables[key] for key in ENVIRONMENT['environment']) else 'absent',
                               'cli-profile': 'file_present_not_verified' if profiles['cli'] else 'file_missing',
                               'sdk-profile': 'file_present_not_verified' if profiles['sdk'] else 'file_missing',
                               'credentials-uri': 'endpoint_set_not_verified' if variables['ALIBABA_CLOUD_CREDENTIALS_URI'] else 'endpoint_not_set',
                               'oidc': 'not_probed', 'ecs-role': 'not_probed'},
            'workload_providers': 'Not probed. Select a provider explicitly; absence of local keys does not rule out workload identity.',
            'next_step': 'Reuse the source selected for this setup, or ask the user to choose one. Profile names are local labels, not verified cloud account identities.'}
