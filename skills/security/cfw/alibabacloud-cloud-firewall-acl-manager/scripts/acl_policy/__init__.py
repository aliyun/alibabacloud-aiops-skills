"""ACL policy plugin auto-discovery & registry"""
import importlib
import pkgutil
from .base import AclPolicyPlugin

_registry = {}


def _auto_discover():
    """Scan all modules under the acl_policy/ directory and automatically register AclPolicyPlugin subclasses"""
    plugins_list = []
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f".{module_name}", package=__name__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, AclPolicyPlugin)
                    and attr is not AclPolicyPlugin):
                instance = attr()
                plugins_list.append(instance)
    plugins_list.sort(key=lambda p: p.order)
    for p in plugins_list:
        _registry[p.name] = p


_auto_discover()


def list_plugins():
    return list(_registry.values())


def get_plugins(names):
    return [_registry[n] for n in names if n in _registry]


def get_all_plugin_names():
    return list(_registry.keys())
