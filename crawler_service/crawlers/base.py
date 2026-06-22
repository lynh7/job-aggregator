from abc import ABC, abstractmethod
from hashlib import sha1
from urllib.parse import urlsplit, urlunsplit

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from app.schemas import RawJobRecord
from crawler_service.config import CrawlerSettings


class JobCrawler(ABC):
    name: str
    api_version: str = "v1"

    def __init__(self, settings: CrawlerSettings) -> None:
        self.settings = settings

    @abstractmethod
    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        """Return raw source records for this provider."""

    def build_browser_config(self) -> BrowserConfig:
        return BrowserConfig(
            browser_type=self.settings.crawl_browser_type,
            headless=self.settings.crawl_headless,
            verbose=self.settings.crawl_verbose,
            text_mode=self.settings.crawl_text_mode,
        )

    def build_run_config(self, *, wait_for: str | None = None) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for=wait_for,
            wait_for_timeout=self.settings.crawl_wait_for_timeout_ms,
            page_timeout=self.settings.crawl_page_timeout_ms,
            delay_before_return_html=self.settings.crawl_delay_before_return_html,
        )

    async def fetch_html(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        *,
        wait_for: str | None = None,
    ) -> str:
        result = await crawler.arun(url=url, config=self.build_run_config(wait_for=wait_for))
        if not result.success:
            message = result.error_message or f"crawl failed for {url}"
            raise ValueError(message)
        return result.cleaned_html or result.html or ""

    def build_record(self, payload: dict[str, str | None], url: str) -> RawJobRecord:
        return RawJobRecord(
            provider=self.name,
            api_version=self.api_version,
            source_record_id=stable_source_id(self.name, url),
            payload=payload,
        )


def canonical_url(url: str) -> str:
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, "", ""))



def stable_source_id(provider: str, url: str) -> str:
    canonical = canonical_url(url)
    digest = sha1(f"{provider}:{canonical}".encode("utf-8")).hexdigest()
    return digest
