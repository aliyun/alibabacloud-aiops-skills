"""Raw shared definition reads, without identity envelopes, storage resolution or output budgets."""

from .catalog_get import get
from .catalog_overview import overview
from .catalog_search import search
from .query import ModelQuery


class DefinitionCatalog:
    def __init__(self, query_model: ModelQuery):
        self.query_model = query_model

    def overview(self, *, include_example_queries=True):
        return overview(self.query_model, include_example_queries=include_example_queries)

    def get(self, element_type, element_name, member_names=None):
        return get(self.query_model, element_type, element_name, member_names)

    def search(self, search_text, source_tags=None, limit=20, *, include_example_queries=True):
        return search(self.query_model, search_text, source_tags, limit, include_example_queries=include_example_queries)
