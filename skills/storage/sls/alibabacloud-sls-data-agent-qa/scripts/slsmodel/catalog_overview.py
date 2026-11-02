"""Overview discovery with the less restrictive read mode."""

from .catalog_projection import project_overview
from .query import ModelQuery, ReadMode

OVERVIEW_SPL = (".umodel | where kind in ('log_set', 'runbook_set', 'metric_set')"
                " | project kind, metadata, spec")


def overview(query_model: ModelQuery, *, include_example_queries=True):
    return project_overview(query_model(OVERVIEW_SPL, ReadMode.OVERVIEW), include_example_queries=include_example_queries)
