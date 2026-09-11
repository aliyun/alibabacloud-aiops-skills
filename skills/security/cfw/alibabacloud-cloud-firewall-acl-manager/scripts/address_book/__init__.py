"""Auto-discovery and registry of address book plugins"""
import importlib
import pkgutil
from .base import AddressBookPlugin

_registry = {}


def _auto_discover():
    """Scan all modules under the address_book/ directory and auto-register AddressBookPlugin subclasses"""
    plugins_list = []
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f".{module_name}", package=__name__)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, AddressBookPlugin)
                    and attr is not AddressBookPlugin):
                instance = attr()
                plugins_list.append(instance)
    # Sort by order
    plugins_list.sort(key=lambda p: p.order)
    for p in plugins_list:
        _registry[p.name] = p


_auto_discover()


def list_plugins():
    """Return the list of all registered plugins"""
    return list(_registry.values())


def get_plugins(names):
    """Get plugins by a list of names"""
    return [_registry[n] for n in names if n in _registry]


def get_all_plugin_names():
    """Return the names of all registered plugins"""
    return list(_registry.keys())
