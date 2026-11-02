"""Project binding for the shared model catalog."""

from slsmodel import ModelCatalog
from .client import SourceModelClient


class SourceModelCatalog(ModelCatalog):
    def __init__(self, client: SourceModelClient, project: str):
        super().__init__(lambda spl, mode: client.query_model(project, spl, mode),
                         {"project": project}, supports_example_queries=False)
