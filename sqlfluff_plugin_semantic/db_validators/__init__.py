"""Database validators and the shared, per-process validator registry.

Rules must obtain validators through :func:`get_validator` instead of
instantiating them directly. This keeps a single persistent connection (and
its metadata cache) per dialect for the whole lint run, instead of opening
and closing a connection for every evaluated AST node.
"""

import atexit
from typing import Callable, Dict, Optional

from sqlfluff_plugin_semantic.db_validators.base_validator import BaseDBValidator


# Maps a SQLFluff dialect name to a factory of its validator. Each engine
# registers its own entry, importing the validator lazily inside the factory
# so that each engine's driver is only required when used, e.g.:
#
#     def _create_mysql() -> BaseDBValidator:
#         from sqlfluff_plugin_semantic.db_validators.mysql_validator import MySQLValidator
#         return MySQLValidator()
#
#     _FACTORIES = {"mysql": _create_mysql}
_FACTORIES: Dict[str, Callable[[], BaseDBValidator]] = {}

# One validator per dialect. ``None`` records a failed connection attempt so
# that we do not retry (and print the same error) for every statement.
_instances: Dict[str, Optional[BaseDBValidator]] = {}


def _load_env_file() -> None:
    """Load a local ``.env`` file if python-dotenv is available."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    # usecwd=True searches from the directory where sqlfluff is executed.
    load_dotenv(find_dotenv(usecwd=True))


def get_validator(dialect_name: str) -> Optional[BaseDBValidator]:
    """Return the connected, shared validator for a dialect.

    Returns:
        The validator, or None if the dialect is unsupported or the
        connection could not be established.
    """
    if dialect_name in _instances:
        return _instances[dialect_name]

    factory = _FACTORIES.get(dialect_name)
    if factory is None:
        return None

    _load_env_file()
    validator = factory()
    _instances[dialect_name] = validator if validator.ensure_connected() else None
    return _instances[dialect_name]


@atexit.register
def close_all_validators() -> None:
    """Close every open connection when the process exits."""
    for validator in _instances.values():
        if validator is not None:
            validator.disconnect()
    _instances.clear()
