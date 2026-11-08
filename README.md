# sqlfluff-plugin-semantic

SQLFluff plugin for the static semantic analysis of SQL embedded in triggers, stored
procedures and views. Unlike SQLFluff's syntactic rules, it connects to a live database
and validates the code against the real metadata (tables, columns, types, routines).

Branches: `main` holds the SQLFluff integration and the database contract shared by every
engine; `mysql` and `postgresql` hold each engine's validator and semantic rules.

```
sqlfluff-plugin-semantic/
├── sqlfluff_plugin_semantic/
|   ├── db_validators/
|   |   ├── __init__.py              # get_validator(): shared connection + cache per dialect
|   |   └── base_validator.py        # Abstract contract (BaseDBValidator, StoredObject)
|   └── __init__.py                  # SQLFluff plugin hook (get_rules)
├── .env.example                     # Template for local credentials (copy to .env)
├── generate_tree.py                 # Renders the SQLFluff AST of test.sql with Graphviz
├── pyproject.toml
└── test.sql
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in your local credentials
```

`.env` is looked up from the directory where `sqlfluff` is executed (and its parents).

## Inspecting the AST

`generate_tree.py` parses `test.sql` with the MySQL dialect and writes `ast_output.png`, to
see the real node hierarchy before writing a rule (requires `pip install graphviz` and the
Graphviz binaries).

## Implementing a new engine

Subclass `BaseDBValidator` and implement only `connect`, `disconnect`, `is_connected`,
`_fetch_table_columns(table) -> {column: DATA_TYPE}` and the stored object hooks
`_fetch_views`, `_fetch_routines`, `_fetch_triggers` (each returns a list of
`StoredObject(kind, name, definition)` with the full `CREATE ...` statement). Caching,
`table_exists`, `get_column_type`, `get_table_columns` and `get_stored_objects` are
inherited. Then register the factory in `db_validators/__init__.py` (`_FACTORIES`) and the
engine's rules in `get_rules()` (`sqlfluff_plugin_semantic/__init__.py`).
