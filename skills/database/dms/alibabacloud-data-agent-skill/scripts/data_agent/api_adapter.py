"""API adapter for consistent casing in requests and responses.

Author: Tinker
Created: 2026-03-19
"""

import json
from typing import Any, Dict, Union


def camel_to_pascal_case(s: str) -> str:
    """Convert camelCase string to PascalCase."""
    if not s:
        return s
    return s[0].upper() + s[1:] if len(s) > 1 else s.upper()


def pascal_to_camel_case(s: str) -> str:
    """Convert PascalCase string to camelCase."""
    if not s:
        return s
    return s[0].lower() + s[1:] if len(s) > 1 else s.lower()


def convert_keys_to_pascal(obj: Any, exclude_paths: list = None) -> Any:
    """Recursively convert all dictionary keys to PascalCase.

    Args:
        obj: Input object (dict, list, or primitive)
        exclude_paths: List of key names to exclude from conversion

    Returns:
        Object with keys converted to PascalCase
    """
    if exclude_paths is None:
        exclude_paths = []

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(key, str) and key in exclude_paths:
                # Skip conversion for excluded keys
                pascal_key = key
            else:
                pascal_key = camel_to_pascal_case(key) if isinstance(key, str) else key
            result[pascal_key] = convert_keys_to_pascal(value, exclude_paths)
        return result
    elif isinstance(obj, list):
        return [convert_keys_to_pascal(item, exclude_paths) for item in obj]
    else:
        return obj


def convert_keys_to_camel(obj: Any, api_action: str = None) -> Any:
    """Recursively convert all dictionary keys to camelCase.

    Args:
        obj: Input object (dict, list, or primitive)
        api_action: API action name to customize transformation logic

    Returns:
        Object with keys converted to camelCase
    """
    # Special handling for file upload signature response which needs to preserve specific formats
    if api_action and 'DescribeFileUploadSignature' in api_action:
        # Don't transform the response for file upload signature as it needs specific format
        return obj

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            camel_key = pascal_to_camel_case(key) if isinstance(key, str) else key
            result[camel_key] = convert_keys_to_camel(value, api_action)
        return result
    elif isinstance(obj, list):
        return [convert_keys_to_camel(item, api_action) for item in obj]
    else:
        return obj


class APIAdapter:
    """Adapter to ensure consistent casing for API requests and responses."""

    @staticmethod
    def prepare_request_params(params: Dict[str, Any], api_action: str = None) -> Dict[str, Any]:
        """Prepare request parameters with PascalCase keys.

        Args:
            params: Original request parameters
            api_action: API action name to customize transformation logic

        Returns:
            Parameters with PascalCase keys
        """
        # Special handling for file upload signatures which may require specific param formats
        exclude_paths = []
        if api_action and 'FileUpload' in api_action:
            # Some file upload APIs might expect specific parameter casing
            exclude_paths = ['FileName', 'FileSize', 'FileId', 'Filename']

        return convert_keys_to_pascal(params, exclude_paths)

    @staticmethod
    def prepare_request_body(body: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request body with PascalCase keys.

        Args:
            body: Original request body

        Returns:
            Body with PascalCase keys
        """
        return convert_keys_to_pascal(body)

    @staticmethod
    def process_response(response: Dict[str, Any], api_action: str = None) -> Dict[str, Any]:
        """Process API response to convert keys to camelCase.

        Args:
            response: Original API response
            api_action: API action name to customize transformation logic

        Returns:
            Response with camelCase keys
        """
        return convert_keys_to_camel(response, api_action)


# Singleton instance
adapter = APIAdapter()