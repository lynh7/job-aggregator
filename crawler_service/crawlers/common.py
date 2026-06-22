import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from crawler_service.crawlers.base import canonical_url


def slugify_keyword(keyword: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", keyword.strip().lower())
    return slug.strip("-")


def safe_text(node: Tag | None) -> str | None:
    if node is None:
        return None
    text = " ".join(node.get_text(" ", strip=True).split())
    return text or None


def safe_attr(node: Tag | None, name: str) -> str | None:
    if node is None:
        return None
    value = node.get(name)
    if isinstance(value, str):
        value = value.strip()
    return value or None


def html_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def join_texts(nodes: Iterable[Tag]) -> str | None:
    parts = [safe_text(node) for node in nodes]
    cleaned = [part for part in parts if part]
    return " ".join(cleaned) or None


def normalize_job_url(url: str | None) -> str | None:
    if not url:
        return None
    return canonical_url(url)
