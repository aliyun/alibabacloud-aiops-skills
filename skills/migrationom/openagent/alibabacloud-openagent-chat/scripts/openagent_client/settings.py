"""Local connection choices; cloud controls belong to the service."""
from .common import require, ClientError
from .credentials import validate_source

SERVICE_REGIONS = {'cn-hangzhou': 'Hangzhou', 'ap-southeast-1': 'Singapore'}
PRODUCTION_ENDPOINTS = {region: f'openagent.{region}.aliyuncs.com' for region in SERVICE_REGIONS}


def region_choices():
    return ' or '.join(f'{label} ({region})' for region, label in SERVICE_REGIONS.items())


def connection(spec, *, saved_region=None):
    require(isinstance(spec, dict) and not (set(spec) - {'region', 'endpoint', 'credentials'}),
            'InvalidConnection', 'Provide only the OpenAgent service region and credential source; never store secret values.')
    region = spec.get('region', saved_region)
    require(region is not None, 'RegionSelectionRequired',
            'Ask the user to choose the OpenAgent service region: ' + region_choices() + '.')
    require(isinstance(region, str) and region in PRODUCTION_ENDPOINTS,
            'UnsupportedRegion', 'Choose a service region listed by capabilities.')
    validate_source(spec.get('credentials'))
    endpoint = PRODUCTION_ENDPOINTS[region]
    require('endpoint' not in spec or spec['endpoint'] == endpoint, 'InvalidEndpoint',
            'The endpoint must match the selected region and installed distribution.')
    return {'region': region, 'endpoint': endpoint, 'credentials': dict(spec['credentials'])}


def supported_connection(value):
    try:
        return isinstance(value, dict) and set(value) == {'region', 'endpoint', 'credentials'} and connection(value) == value
    except ClientError:
        return False


def load(store):
    saved = store.get('connection')
    if saved is not None:
        return {'connection': saved}
    return None


def configure(store, proposed):
    require(isinstance(proposed, dict) and set(proposed) == {'connection'}, 'InvalidSetup',
            'Provide connection only. Cloud controls, model settings and update policies are not part of this Skill.')
    current = load(store) or {}
    selected = connection(proposed['connection'], saved_region=current.get('connection', {}).get('region'))
    # Saving connection choices is entirely local: no credential resolution, cloud
    # inspection or account-wide setting changes are needed to start a conversation.
    store.save_connection(selected)
    return {'ok': True, 'configuration_target': 'OpenAgent Skill', 'configured': True,
            'connection': selected, 'cloud_requests': False,
            'message': 'Saved the OpenAgent Skill local connection. The service region and credential source will be reused.'}


def guard(store, transport=None):
    """Validate only the local connection before a new conversation submission."""
    config = load(store)
    require(config and supported_connection(config.get('connection')), 'SetupRequired',
            'Choose an OpenAgent service region and credential source with setup configure.')
    return config['connection']
