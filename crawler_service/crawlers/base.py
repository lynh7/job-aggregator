from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from hashlib import sha1
from typing import Any, AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx

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

    @asynccontextmanager
    async def open_session(self) -> AsyncIterator[Any]:
        if self.settings.crawl_backend == "crawl4ai":
            try:
                from crawl4ai import AsyncWebCrawler  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "crawl4ai backend selected but crawl4ai is not installed; "
                    "use the browser crawler image or switch CRAWL_BACKEND=http"
                ) from exc
            async with AsyncWebCrawler(config=self.build_browser_config()) as crawler:
                yield crawler
            return

        headers = {
            "User-Agent": self.settings.crawl_user_agent,
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            headers=headers,
            follow_redirects=True,
        ) as client:
            yield client

    def build_browser_config(self) -> Any:
        if self.settings.crawl_backend != "crawl4ai":
            return None
        try:
            from crawl4ai import BrowserConfig  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "crawl4ai backend selected but crawl4ai is not installed"
            ) from exc
        return BrowserConfig(
            browser_type=self.settings.crawl_browser_type,
            headless=self.settings.crawl_headless,
            verbose=self.settings.crawl_verbose,
            text_mode=self.settings.crawl_text_mode,
        )

    def build_run_config(self, *, wait_for: str | None = None) -> Any:
        if self.settings.crawl_backend != "crawl4ai":
            return None
        try:
            from crawl4ai import CacheMode, CrawlerRunConfig  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "crawl4ai backend selected but crawl4ai is not installed"
            ) from exc
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for=wait_for,
            wait_for_timeout=self.settings.crawl_wait_for_timeout_ms,
            page_timeout=self.settings.crawl_page_timeout_ms,
            delay_before_return_html=self.settings.crawl_delay_before_return_html,
        )

    async def fetch_html(
        self,
        session: Any,
        url: str,
        *,
        wait_for: str | None = None,
    ) -> str:
        if self.settings.crawl_backend == "crawl4ai":
            result = await session.arun(url=url, config=self.build_run_config(wait_for=wait_for))
            if not result.success:
                message = result.error_message or f"crawl failed for {url}"
                raise ValueError(message)
            return result.cleaned_html or result.html or ""

        response = await session.get(url)
        response.raise_for_status()
        return response.text

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
