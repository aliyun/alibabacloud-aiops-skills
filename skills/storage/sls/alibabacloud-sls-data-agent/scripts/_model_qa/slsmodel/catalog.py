"""Bind model identity to the shared semantic core and output budgets."""

from .definitions import DefinitionCatalog
from .errors import CatalogError
from .output import DEFAULT_MAX_BYTES, get_output, overview_output


class ModelCatalog:
    def __init__(self, query_model, identity_fields, *, supports_example_queries=True):
        self.definitions = DefinitionCatalog(query_model)
        self.identity_fields = identity_fields
        self.supports_example_queries = supports_example_queries

    def overview(self, source_tags=None, max_bytes=DEFAULT_MAX_BYTES):
        definitions = self.definitions.overview(include_example_queries=self.supports_example_queries)
        return overview_output(self.identity_fields, definitions, source_tags, max_bytes)

    def get(self, element_type, element_name, member_names=None, max_bytes=DEFAULT_MAX_BYTES):
        if element_type == "exampleQuery" and not self.supports_example_queries:
            raise CatalogError("InvalidParameter", "This catalog does not provide example queries")
        return get_output(self.identity_fields, self.definitions.get(element_type, element_name, member_names), max_bytes)
