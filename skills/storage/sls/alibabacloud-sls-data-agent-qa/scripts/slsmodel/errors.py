"""Catalog failures independent of CLI and SDK exceptions."""

class CatalogError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message
