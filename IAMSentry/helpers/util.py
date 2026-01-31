"""General utility functions for IAMSentry.

This module provides common utility functions used across the IAMSentry package.
"""

from typing import Any, Dict, List, Optional, TypeVar

T = TypeVar("T")


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries with override taking precedence.

    Creates a new dictionary containing all keys from both input
    dictionaries. When a key exists in both, the value from override
    is used. This is a shallow merge - nested dictionaries are not
    merged recursively.

    Arguments:
        base: Base dictionary.
        override: Override dictionary (values take precedence).

    Returns:
        New dictionary with merged contents.

    Example:
        >>> base = {'a': 1, 'b': 2}
        >>> override = {'b': 3, 'c': 4}
        >>> merge_dicts(base, override)
        {'a': 1, 'b': 3, 'c': 4}
    """
    result = base.copy()
    result.update(override)
    return result


def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries with override taking precedence.

    Similar to merge_dicts but recursively merges nested dictionaries.

    Arguments:
        base: Base dictionary.
        override: Override dictionary (values take precedence).

    Returns:
        New dictionary with deep merged contents.

    Example:
        >>> base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        >>> override = {'a': {'y': 4, 'z': 5}}
        >>> deep_merge_dicts(base, override)
        {'a': {'x': 1, 'y': 4, 'z': 5}, 'b': 3}
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value.

    Arguments:
        data: Dictionary to get value from.
        *keys: Sequence of keys for nested access.
        default: Default value if any key not found.

    Returns:
        Value at nested key path or default.

    Example:
        >>> data = {'a': {'b': {'c': 1}}}
        >>> safe_get(data, 'a', 'b', 'c')
        1
        >>> safe_get(data, 'a', 'x', 'y', default='not found')
        'not found'
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def flatten_dict(data: Dict[str, Any], separator: str = ".", prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dictionary to single level.

    Arguments:
        data: Dictionary to flatten.
        separator: Separator for nested keys.
        prefix: Prefix for keys (used in recursion).

    Returns:
        Flattened dictionary with dot-separated keys.

    Example:
        >>> data = {'a': {'b': 1, 'c': {'d': 2}}}
        >>> flatten_dict(data)
        {'a.b': 1, 'a.c.d': 2}
    """
    result = {}

    for key, value in data.items():
        full_key = f"{prefix}{separator}{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_dict(value, separator, full_key))
        else:
            result[full_key] = value

    return result


def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split list into chunks of specified size.

    Arguments:
        items: List to split.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.

    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def filter_none(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from dictionary.

    Arguments:
        data: Dictionary to filter.

    Returns:
        New dictionary without None values.

    Example:
        >>> filter_none({'a': 1, 'b': None, 'c': 3})
        {'a': 1, 'c': 3}
    """
    return {k: v for k, v in data.items() if v is not None}
