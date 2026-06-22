from crawler_service.config import CrawlerSettings
from crawler_service.crawlers.base import JobCrawler
from crawler_service.crawlers.itviec import ITViecCrawler
from crawler_service.crawlers.mock import MockCrawler
from crawler_service.crawlers.topcv import TopCVCrawler



def build_crawlers(settings: CrawlerSettings) -> dict[str, JobCrawler]:
    return {
        "mock": MockCrawler(settings),
        "topcv": TopCVCrawler(settings),
        "itviec": ITViecCrawler(settings),
    }
