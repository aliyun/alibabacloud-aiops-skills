"""Context Model catalog, including semantic-to-physical storage resolution."""

from slsmodel import ModelCatalog, CatalogError
from .client import ContextModelClient
from .storage import resolve_by_schema, resolve_by_source_tag


class ContextModelCatalog(ModelCatalog):
    def __init__(self, client: ContextModelClient, model_name: str):
        super().__init__(lambda spl, mode: client.query_model(model_name, spl, mode), {"model": model_name})

    def resolve_storage(self, schema_name=None, *, source_tag=None):
        """Resolve Context Model locations by Schema name or metadata.tags.source."""
        if bool(schema_name) == bool(source_tag):
            raise CatalogError("InvalidParameter", "Provide exactly one of schema or source")
        query_model = self.definitions.query_model
        result = (resolve_by_source_tag(query_model, source_tag) if source_tag else
                  resolve_by_schema(query_model, schema_name))
        return {**self.identity_fields, **result}
