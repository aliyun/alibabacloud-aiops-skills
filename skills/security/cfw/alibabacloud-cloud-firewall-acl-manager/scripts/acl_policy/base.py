"""Base class for ACL policy backup plugins"""
from abc import ABC, abstractmethod


class AclPolicyPlugin(ABC):
    """Base class for ACL policy backup plugins"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name (in Chinese, used for display and interactive selection)"""
        pass

    @property
    @abstractmethod
    def sheet_name(self) -> str:
        """Excel sheet name"""
        pass

    @property
    @abstractmethod
    def columns(self) -> list:
        """Excel column definitions: [(column_name, value_getter), ...]"""
        pass

    @property
    def order(self) -> int:
        """Sort order (smaller values come first, default 0)"""
        return 0

    @property
    def col_widths(self) -> list:
        """Column widths (optional), aligned one-to-one with columns"""
        return None

    @property
    def api_action(self) -> str:
        """API Action name"""
        return ""

    @property
    def page_no_key(self) -> str:
        """Pagination page number parameter name, defaults to CurrentPage"""
        return "CurrentPage"

    @property
    def result_key(self) -> str:
        """Key name of the returned data array"""
        return "Acls"

    def extra_params(self) -> dict:
        """Extra API request parameters (must be overridden, must contain at least Direction)"""
        return {}

    def post_process(self, items: list) -> list:
        """Post-processing of data (optional override)"""
        return items

    def custom_fetch(self, ak, sk, endpoint, call_api_fn, page_size=50, security_token=None):
        """Custom data fetching logic (optional override)"""
        return None
