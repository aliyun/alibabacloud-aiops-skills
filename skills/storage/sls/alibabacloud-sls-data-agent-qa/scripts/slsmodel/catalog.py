"""Public model core: inject a query function, independent of any service."""

from .catalog_get import get
from .catalog_overview import overview
from .catalog_resolve import resolve
from .query import QueryFunc


class Catalog:
    def __init__(self, query: QueryFunc):
        self.query = query

    def overview(self):
        return overview(self.query)

    def get(self, element_type, element, requested=None):
        return get(self.query, element_type, element, requested)

    def resolve(self, schema):
        return resolve(self.query, schema)
