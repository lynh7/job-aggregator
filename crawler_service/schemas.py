from app.schemas import IngestResponse, SearchRequest


class CrawlRequest(SearchRequest):
    export: bool = False


class CrawlResponse(IngestResponse):
    pass
