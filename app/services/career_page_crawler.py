"""Career site crawler with HTTP and Playwright support."""

import asyncio
import logging
from typing import Optional, AsyncIterator
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CrawlerConfig:
    """Crawler configuration."""
    def __init__(
        self,
        max_pages: int = 200,
        max_depth: int = 3,
        request_timeout: int = 10,
        request_delay: float = 0.5,
        max_concurrent: int = 3,
        retry_attempts: int = 2,
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.request_timeout = request_timeout
        self.request_delay = request_delay
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts


class CareerPageCrawler:
    """Crawl career sites using HTTP and optional Playwright rendering."""

    def __init__(self, domain: str, config: CrawlerConfig = None):
        self.domain = domain
        self.config = config or CrawlerConfig()
        self.session = None
        self.browser = None
        self.context = None

    async def initialize(self):
        """Initialize HTTP session (and optional Playwright browser)."""
        import aiohttp
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()

    async def fetch_page(self, url: str, use_playwright: bool = False) -> tuple[str, str]:
        """Fetch page HTML.

        Args:
            url: Page URL
            use_playwright: If True, render JS using Playwright

        Returns:
            (html, title) tuple

        Raises:
            On network error, timeout, 404, 403, etc.
        """
        if use_playwright:
            return await self._fetch_with_playwright(url)
        else:
            return await self._fetch_http(url)

    async def _fetch_http(self, url: str) -> tuple[str, str]:
        """Fetch using simple HTTP GET."""
        import aiohttp

        for attempt in range(self.config.retry_attempts):
            try:
                async with self.session.get(
                    url, timeout=self.config.request_timeout
                ) as resp:
                    if resp.status == 404:
                        raise HTTPError(404, f"Page not found: {url}")
                    if resp.status == 403:
                        raise HTTPError(403, f"Access forbidden: {url}")
                    if resp.status >= 500:
                        if attempt < self.config.retry_attempts - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise HTTPError(resp.status, f"Server error: {url}")

                    resp.raise_for_status()
                    html = await resp.text()

                    # Extract title
                    soup = BeautifulSoup(html, "html.parser")
                    title_tag = soup.find("title")
                    title = title_tag.get_text() if title_tag else ""

                    return html, title

            except asyncio.TimeoutError:
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise TimeoutError(f"Timeout fetching {url}")

    async def _fetch_with_playwright(self, url: str) -> tuple[str, str]:
        """Fetch using Playwright (for JS-rendered content)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed, falling back to HTTP")
            return await self._fetch_http(url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, timeout=self.config.request_timeout * 1000)
                await page.wait_for_load_state("networkidle", timeout=5000)

                html = await page.content()
                title = await page.title()

                return html, title
            finally:
                await page.close()
                await browser.close()

    async def crawl(self) -> AsyncIterator[tuple[str, str, str]]:
        """Crawl career site.

        Yields:
            (url, html, title) tuples

        Respects:
            - max_pages limit
            - max_depth limit
            - request_delay rate limiting
            - max_concurrent concurrent requests
        """
        await self.initialize()

        try:
            queue = asyncio.Queue()
            seen = set()
            semaphore = asyncio.Semaphore(self.config.max_concurrent)
            pages_crawled = 0

            await queue.put((self.domain, 0))

            while not queue.empty() and pages_crawled < self.config.max_pages:
                url, depth = queue.get_nowait()

                if url in seen or depth >= self.config.max_depth:
                    continue

                seen.add(url)

                async with semaphore:
                    await asyncio.sleep(self.config.request_delay)

                    try:
                        # Try HTTP first, fallback to Playwright if needed
                        html, title = await self.fetch_page(url, use_playwright=False)

                        yield (url, html, title)
                        pages_crawled += 1

                        # Extract links for next crawl
                        links = self._extract_links(html, url)
                        for link in links:
                            if link not in seen and pages_crawled < self.config.max_pages:
                                await queue.put((link, depth + 1))

                    except HTTPError as e:
                        if e.status == 403:
                            logger.warning(f"Access forbidden: {url}")
                            break  # Stop crawling this domain
                        else:
                            logger.warning(f"HTTP error {e.status}: {url}")

                    except TimeoutError:
                        logger.warning(f"Timeout: {url}")

                    except Exception as e:
                        logger.error(f"Crawl error {url}: {e}")

        finally:
            await self.close()

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract links from HTML."""
        links = []
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)

            # Only follow same-domain links
            if urlparse(full_url).hostname == urlparse(self.domain).hostname:
                # Remove fragments
                full_url = full_url.split("#")[0]
                links.append(full_url)

        return links


class HTTPError(Exception):
    """HTTP error with status code."""
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)
