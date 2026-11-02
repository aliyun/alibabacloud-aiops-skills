"""Context Model wire API; no argument parsing or presentation logic."""

from urllib.parse import quote

from slsmodel.query import ModelTransport, ReadMode, decode_model_rows


class ContextModelClient:
    def __init__(self, transport: ModelTransport):
        self.transport = transport

    def list_models(self, page=1, size=20, keyword=None, model_name=None, project=None):
        query = {"page": str(page), "size": str(size)}
        query.update({k: v for k, v in {"keyword": keyword, "name": model_name, "projectName": project}.items() if v is not None})
        return self.transport.request("ListContextModel", "GET", "/context-models", query=query)

    def query_model(self, model_name, spl, mode=ReadMode.COMPLETE):
        body = self.transport.request("QueryContextModel", "POST", "/context-models/" + quote(model_name, safe="") + "/query",
                                      body={"query": spl})
        return decode_model_rows(body, mode)
