from bs4 import Tag

from app.schemas import RawJobRecord
from crawler_service.crawlers.base import JobCrawler
from crawler_service.crawlers.common import join_texts, html_soup, normalize_job_url, safe_attr, safe_text, slugify_keyword


class ITViecCrawler(JobCrawler):
    name = "itviec"

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        del location
        urls = [
            self.settings.itviec_search_url_template.format(keyword_slug=slugify_keyword(keyword))
            for keyword in keywords
            if slugify_keyword(keyword)
        ]
        records: list[RawJobRecord] = []
        seen_urls: set[str] = set()

        async with self.open_session() as session:
            for listing_url in urls:
                html = await self.fetch_html(session, listing_url, wait_for="div.ipy-2")
                for card in html_soup(html).find_all("div", class_="ipy-2"):
                    payload = self._extract_listing(card)
                    job_url = normalize_job_url(payload.get("url"))
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    detail_html = await self.fetch_html(session, job_url, wait_for="body")
                    payload.update(self._extract_detail(detail_html))
                    payload["url"] = job_url
                    payload.setdefault("id", job_url.rsplit("/", 1)[-1])
                    records.append(self.build_record(payload, job_url))
                    if len(records) >= limit:
                        return records
        return records

    def _extract_listing(self, card: Tag) -> dict[str, str | None]:
        url_holder = card.find("h3", class_="imt-3 text-break")
        raw_url = safe_attr(url_holder, "data-url")
        job_url = normalize_job_url(raw_url)

        company_wrapper = card.find("div", class_="imy-3 d-flex align-items-center")
        location_node = card.find(
            "div",
            class_="text-rich-grey text-truncate text-nowrap stretched-link position-relative",
        )
        mode_node = card.find("div", class_="text-rich-grey flex-shrink-0")
        tag_container = card.find("div", class_="imt-4 imb-3 d-flex igap-1")
        tags = None
        if tag_container is not None:
            tags = ", ".join(
                text for text in (safe_text(tag) for tag in tag_container.find_all("a")) if text
            ) or None

        return {
            "id": job_url.rsplit("/", 1)[-1] if job_url else None,
            "title": safe_text(card.find("h3")),
            "company": safe_text(company_wrapper.find("span") if company_wrapper else None),
            "logo_url": safe_attr(company_wrapper.find("img") if company_wrapper else None, "data-src"),
            "url": job_url,
            "location": safe_attr(location_node, "title"),
            "mode": safe_text(mode_node),
            "employment_type": safe_text(mode_node),
            "tags": tags,
        }

    def _extract_detail(self, html: str) -> dict[str, str | None]:
        soup = html_soup(html)
        job_category = None
        category_label = soup.find("div", string="Job Expertise:")
        if category_label is not None:
            links = category_label.find_next("div")
            if links is not None:
                job_category = ", ".join(
                    text for text in (safe_text(link) for link in links.find_all("a")) if text
                ) or None

        sections = soup.find_all("div", class_="imy-5 paragraph")
        description = join_texts(sections[0].find_all(["p", "li"], recursive=True)) if len(sections) > 0 else None
        requirements = join_texts(sections[1].find_all(["p", "li"], recursive=True)) if len(sections) > 1 else None
        return {
            "description": description,
            "descriptions": description,
            "requirements": requirements,
            "job_category": job_category,
        }
