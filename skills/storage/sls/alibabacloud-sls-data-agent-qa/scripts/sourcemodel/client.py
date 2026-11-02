"""Source Model wire API using the same injected SDK transport as Context Models."""

from slsmodel.query import ModelTransport, ReadMode, decode_model_rows


class SourceModelClient:
    def __init__(self, transport: ModelTransport):
        self.transport = transport

    def get_generation_status(self, project):
        return self.transport.request("GetSourceModelStatus", "GET", "/source-models/status", project=project)

    def query_model(self, project, spl, mode=ReadMode.COMPLETE):
        body = self.transport.request("QuerySourceModel", "POST", "/source-models/query",
                                      body={"query": spl}, project=project)
        return decode_model_rows(body, mode)
