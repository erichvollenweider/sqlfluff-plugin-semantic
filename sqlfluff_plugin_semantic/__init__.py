"""Hook implementation for the SQLFluff Semantic Analyzer plugin."""

from sqlfluff.core.plugin import hookimpl


@hookimpl
def get_rules():
    """Get plugin rules.

    This method must be implemented to return the list of rule classes
    that this plugin provides. Each database engine registers its semantic
    rules here, importing the rules module inside the function to avoid
    circular dependency issues during the plugin loading sequence.
    """
    return []
