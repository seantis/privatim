from __future__ import annotations

from weasyprint.urls import (  # type: ignore[import-untyped]
    URLFetcher,
    URLFetcherResponse,
)


from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Iterable


class AllowlistURLFetcher(URLFetcher):
    """WeasyPrint URL fetcher that only fetches the given URLs.

    WeasyPrint's default fetcher follows any URL in the rendered HTML,
    including ``file://`` (embedding local files as PDF attachments) and
    internal hosts (SSRF). Pass this to every ``HTML(...)`` and ``CSS(...)``
    that renders data we don't fully control.

    ``data:`` URLs are always allowed: they carry their content inline and
    can neither read files nor reach other hosts (the report's logo is one).

    """

    def __init__(
        self, allowed_urls: Iterable[str] = (), **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.allowed_urls = frozenset(allowed_urls)

    def fetch(
        self, url: str, headers: dict[str, str] | None = None
    ) -> URLFetcherResponse:
        if url not in self.allowed_urls and not url.startswith('data:'):
            raise ValueError(f'URL not allowed in PDF: {url}')
        return super().fetch(url, headers)
