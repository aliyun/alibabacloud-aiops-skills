"""Overview discovery with the less restrictive read mode."""

from .catalog_projection import project_overview
from .query import QueryFunc, ReadMode

OVERVIEW_SPL = (".umodel | where kind in ('log_set', 'runbook_set', 'metric_set')"
                " | project kind, metadata, spec")


def overview(query: QueryFunc):
    return project_overview(query(OVERVIEW_SPL, ReadMode.OVERVIEW))
