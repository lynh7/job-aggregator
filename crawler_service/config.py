from functools import lru_cache

from app.config import Settings


class CrawlerSettings(Settings):
    crawler_enabled_providers: str = "topcv,itviec"
    crawler_push_exports: bool = False
    topcv_search_url_template: str = "https://www.topcv.vn/tim-viec-lam-{keyword_slug}"
    itviec_search_url_template: str = "https://itviec.com/it-jobs/{keyword_slug}"
    crawl_browser_type: str = "chromium"
    crawl_headless: bool = True
    crawl_verbose: bool = False
    crawl_text_mode: bool = False
    crawl_page_timeout_ms: int = 45000
    crawl_wait_for_timeout_ms: int = 20000
    crawl_delay_before_return_html: float = 1.0

    @property
    def crawler_providers(self) -> list[str]:
        return [item.strip() for item in self.crawler_enabled_providers.split(",") if item.strip()]


@lru_cache
def get_settings() -> CrawlerSettings:
    return CrawlerSettings()
