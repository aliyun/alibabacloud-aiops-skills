"""Context Model wire API; no argument parsing or presentation logic."""

from typing import Protocol
from urllib.parse import quote

from slsmodel import CatalogError, ReadMode
from slsmodel.query import decode_rows


class Transport(Protocol):
    def request(self, action, method, path, query=None, body=None, project=None): ...


def decode_model_rows(body, mode=ReadMode.COMPLETE):
    status = body.get("responseStatus") or {}
    if mode == ReadMode.COMPLETE and (not isinstance(status, dict) or
            status.get("result") != "Success" or status.get("level") != "Info"):
        raise CatalogError("IncompleteCatalogRead", "Model response does not certify a complete successful read")
    return decode_rows(body.get("header"), body.get("data"), mode)


class ContextModelClient:
    def __init__(self, transport: Transport):
        self.transport = transport

    def list_models(self, page=1, size=20, keyword=None, name=None, project=None):
        query = {"page": str(page), "size": str(size)}
        query.update({k: v for k, v in {"keyword": keyword, "name": name, "projectName": project}.items() if v is not None})
        return self.transport.request("ListContextModel", "GET", "/context-models", query=query)

    def query(self, name, spl, mode=ReadMode.COMPLETE):
        body = self.transport.request("QueryContextModel", "POST", "/context-models/" + quote(name, safe="") + "/query",
                                      body={"query": spl})
        return decode_model_rows(body, mode)
