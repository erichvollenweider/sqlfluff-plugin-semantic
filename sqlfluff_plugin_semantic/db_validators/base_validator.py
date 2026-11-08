"""Base Validator interface for database connections."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

# Kinds of stored objects returned by ``get_stored_objects``.
VIEW = "VIEW"
PROCEDURE = "PROCEDURE"
FUNCTION = "FUNCTION"
TRIGGER = "TRIGGER"
STORED_OBJECT_KINDS = (VIEW, PROCEDURE, FUNCTION, TRIGGER)


@dataclass(frozen=True)
class StoredObject:
    """A view, routine or trigger stored in the database.

    Attributes:
        kind: One of VIEW / PROCEDURE / FUNCTION / TRIGGER.
        name: Object name (without schema).
        definition: The complete ``CREATE ...`` statement, in the engine's
            own SQL dialect and without a trailing delimiter.
    """

    kind: str
    name: str
    definition: str


class BaseDBValidator(ABC):
    """Abstract base class for database metadata validators.

    Any specific database engine (MySQL, PostgreSQL) must inherit from this
    class and implement the abstract hooks below. The public lookup methods
    (``get_table_columns``, ``table_exists``, ``get_column_type``,
    ``get_stored_objects``) are already implemented here on top of the hooks
    (Template Method), so each engine only needs to know how to talk to its
    own data dictionary.
    """

    def __init__(self) -> None:
        """Initialize the in-memory metadata caches."""
        # {table_name: {column_name: DATA_TYPE}} with the original column names.
        self._columns_cache: Dict[str, Dict[str, str]] = {}
        # Same data keyed by lower-cased column name, for case-insensitive lookups.
        self._columns_ci_cache: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------
    # Engine-specific hooks (must be implemented by each subclass)
    # ------------------------------------------------------------------

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the database.

        Returns:
            bool: True if connection is successful, False otherwise.
        """

    @abstractmethod
    def disconnect(self) -> None:
        """Safely close the database connection and cursors."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if there is an open, usable connection."""

    @abstractmethod
    def _fetch_table_columns(self, table_name: str) -> Dict[str, str]:
        """Query the engine's data dictionary for the columns of a table.

        This method is only called on cache misses and always runs with an
        open connection.

        Args:
            table_name (str): The name of the table (or view) to inspect.

        Returns:
            Dict[str, str]: Mapping ``{column_name: DATA_TYPE}`` with the data
            type in UPPERCASE (e.g. ``'INT'``, ``'VARCHAR'``). An empty dict
            means the table does not exist in the current schema.
        """

    @abstractmethod
    def _fetch_views(self) -> List[StoredObject]:
        """Return every view of the current schema as ``CREATE VIEW`` statements.

        Like the other ``_fetch_*`` hooks, it always runs with an open connection.
        """

    @abstractmethod
    def _fetch_routines(self) -> List[StoredObject]:
        """Return every procedure and function of the current schema.

        Each definition must be the full ``CREATE PROCEDURE`` / ``CREATE
        FUNCTION`` statement, including the parameter list (bodies alone, as
        in ``information_schema.ROUTINES``, lose the parameters).
        """

    @abstractmethod
    def _fetch_triggers(self) -> List[StoredObject]:
        """Return every trigger of the current schema as ``CREATE TRIGGER`` statements."""

    def describe_target(self) -> str:
        """Human-readable description of the inspected database (for reports)."""
        return type(self).__name__

    # ------------------------------------------------------------------
    # Public API (shared by every engine)
    # ------------------------------------------------------------------

    def ensure_connected(self) -> bool:
        """Connect lazily if needed and report whether the connection is usable."""
        return self.is_connected() or self.connect()

    def get_table_columns(self, table_name: str) -> Dict[str, str]:
        """Return a dict mapping ``{column_name: DATA_TYPE}`` for a given table.

        Results are cached in memory, so the data dictionary is queried at
        most once per table during a lint run.
        """
        if table_name not in self._columns_cache:
            if not self.ensure_connected():
                return {}
            columns = self._fetch_table_columns(table_name)
            self._columns_cache[table_name] = columns
            self._columns_ci_cache[table_name] = {
                name.lower(): data_type for name, data_type in columns.items()
            }
        return self._columns_cache[table_name]

    def table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists in the current schema.

        Args:
            table_name (str): The name of the table to look for.

        Returns:
            bool: True if the table exists.
        """
        return bool(self.get_table_columns(table_name))

    def get_column_type(self, table_name: str, column_name: str) -> Optional[str]:
        """Retrieve the SQL data type of a specific column.

        Column names are matched case-insensitively.

        Returns:
            str: The data type (e.g., 'INT', 'VARCHAR'), or None if not found.
        """
        self.get_table_columns(table_name)
        return self._columns_ci_cache.get(table_name, {}).get(column_name.lower())

    def clear_cache(self) -> None:
        """Drop all cached metadata (e.g. after a schema change)."""
        self._columns_cache.clear()
        self._columns_ci_cache.clear()

    def get_stored_objects(self, kinds: Optional[Iterable[str]] = None) -> List[StoredObject]:
        """Return the views, routines and triggers of the current schema.

        Args:
            kinds: Optional subset of STORED_OBJECT_KINDS to return.

        Returns:
            Objects ordered by kind (views, routines, triggers). Empty if the
            connection cannot be established. Not cached: definitions are
            always read fresh from the data dictionary.
        """
        if not self.ensure_connected():
            return []
        wanted = {kind.upper() for kind in kinds} if kinds else set(STORED_OBJECT_KINDS)
        objects: List[StoredObject] = []
        if VIEW in wanted:
            objects += self._fetch_views()
        if wanted & {PROCEDURE, FUNCTION}:
            objects += [obj for obj in self._fetch_routines() if obj.kind in wanted]
        if TRIGGER in wanted:
            objects += self._fetch_triggers()
        return objects
