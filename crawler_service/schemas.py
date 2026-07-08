from shared.schemas import IngestResponse, SearchRequest


class CrawlRequest(SearchRequest):
    export: bool = False


class CrawlResponse(IngestResponse):
    pass
