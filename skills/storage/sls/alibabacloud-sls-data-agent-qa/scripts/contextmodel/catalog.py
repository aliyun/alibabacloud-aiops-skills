"""Model-bound catalog orchestration and presentation, reusable without CLI."""

from slsmodel import Catalog
from .adaptive_output import DEFAULT_MAX_BYTES, get_output, overview_output
from .client import ContextModelClient


class ContextModelCatalog:
    def __init__(self, client: ContextModelClient, name: str):
        self.name = name
        self.catalog = Catalog(lambda spl, mode: client.query(name, spl, mode))

    def overview(self, sources=None, max_bytes=DEFAULT_MAX_BYTES):
        return overview_output(self.name, self.catalog.overview(), sources, max_bytes)

    def get(self, element_type, element, members=None, max_bytes=DEFAULT_MAX_BYTES):
        return get_output(self.name, self.catalog.get(element_type, element, members), max_bytes)

    def resolve(self, schema):
        return {"model": self.name, **self.catalog.resolve(schema)}
