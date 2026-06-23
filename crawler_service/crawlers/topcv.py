from bs4 import Tag

from app.schemas import RawJobRecord
from crawler_service.crawlers.base import JobCrawler
from crawler_service.crawlers.common import html_soup, normalize_job_url, safe_attr, safe_text, slugify_keyword


class TopCVCrawler(JobCrawler):
    name = "topcv"

    async def search(
        self, keywords: list[str], location: str | None, limit: int
    ) -> list[RawJobRecord]:
        del location
        urls = [
            self.settings.topcv_search_url_template.format(keyword_slug=slugify_keyword(keyword))
            for keyword in keywords
            if slugify_keyword(keyword)
        ]
        records: list[RawJobRecord] = []
        seen_urls: set[str] = set()

        async with self.open_session() as session:
            for listing_url in urls:
                html = await self.fetch_html(session, listing_url, wait_for="div.job-item-search-result")
                for card in html_soup(html).select("div.job-item-search-result"):
                    payload = self._extract_listing(card)
                    job_url = normalize_job_url(payload.get("job_url"))
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    detail_html = await self.fetch_html(session, job_url, wait_for="body")
                    payload.update(self._extract_detail(detail_html, job_url))
                    payload["job_url"] = job_url
                    payload["apply_url"] = job_url
                    payload.setdefault("id", job_url.rsplit("/", 1)[-1])
                    records.append(self.build_record(payload, job_url))
                    if len(records) >= limit:
                        return records
        return records

    def _extract_listing(self, card: Tag) -> dict[str, str | None]:
        title = safe_text(card.find("h3"))
        company = safe_text(card.find("a", class_="company"))
        image = card.find("img")
        raw_url = safe_attr(card.find("a"), "href")
        job_url = normalize_job_url(raw_url)

        address_label = card.find("label", class_="address")
        salary_label = card.find("label", class_="title-salary") or card.find("label", class_="salary")
        experience_label = card.find("label", class_="exp")

        return {
            "id": job_url.rsplit("/", 1)[-1] if job_url else None,
            "job_id": job_url.rsplit("/", 1)[-1] if job_url else None,
            "job_title": title,
            "company_name": company,
            "company_logo": safe_attr(image, "src") or safe_attr(image, "data-src"),
            "job_url": job_url,
            "city": safe_text(address_label.find("span") if address_label else None),
            "salary_range": safe_text(salary_label.find("span") if salary_label else None),
            "experience": safe_text(experience_label.find("span") if experience_label else None),
        }

    def _extract_detail(self, html: str, job_url: str) -> dict[str, str | None]:
        soup = html_soup(html)
        if "/brand/" in job_url:
            description, requirements, education, work_model = self._parse_brand_detail(soup)
        else:
            description, requirements, education, work_model = self._parse_standard_detail(soup)

        category = None
        category_label = soup.find("div", string=lambda value: isinstance(value, str) and "Chuyên môn" in value)
        if category_label is not None:
            links = category_label.find_next("div")
            if links is not None:
                category = ", ".join(
                    text for text in (safe_text(link) for link in links.find_all("a")) if text
                ) or None

        return {
            "job_description": description,
            "description": description,
            "requirements": requirements,
            "level_of_education": education,
            "job_type": work_model,
            "work_model": work_model,
            "job_category": category,
        }

    def _parse_brand_detail(self, soup: Tag) -> tuple[str | None, str | None, str | None, str | None]:
        description = None
        requirements = None
        education = None
        work_model = None

        for box in soup.select("div.premium-job-description__box, div.box-info"):
            title_node = box.select_one("h2.premium-job-description__box--title") or box.select_one("h2.title")
            content_node = box.select_one("div.premium-job-description__box--content") or box.select_one("div.content-tab")
            title = safe_text(title_node)
            content = safe_text(content_node)
            if title == "Mô tả công việc":
                description = content
            elif title == "Yêu cầu ứng viên":
                requirements = content

        for box in soup.select("div.general-information-data, div.box-item"):
            label = safe_text(box.select_one(".general-information-data__label") or box.find("strong"))
            value = safe_text(box.select_one(".general-information-data__value") or box.find("span"))
            if label == "Hình thức làm việc":
                work_model = value
            elif label == "Học vấn":
                education = value

        return description, requirements, education, work_model

    def _parse_standard_detail(self, soup: Tag) -> tuple[str | None, str | None, str | None, str | None]:
        description = None
        requirements = None
        education = None
        work_model = None

        for box in soup.select("div.job-description__item"):
            title = safe_text(box.find("h3"))
            content = safe_text(box.find("div", class_="job-description__item--content"))
            if title == "Mô tả công việc":
                description = content
            elif title == "Yêu cầu ứng viên":
                requirements = content

        for box in soup.find_all("div", class_="box-general-group-info"):
            label = safe_text(box.find("div", class_="box-general-group-info-title"))
            value = safe_text(box.find("div", class_="box-general-group-info-value"))
            if label == "Hình thức làm việc":
                work_model = value
            elif label == "Học vấn":
                education = value

        return description, requirements, education, work_model
