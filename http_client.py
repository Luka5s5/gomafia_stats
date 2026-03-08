import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientError, ClientTimeout

logger = logging.getLogger(__name__)
PROXIES = [
    "190.61.88.147:8080",
    "172.105.107.223:3128",
    "216.26.236.103:3129",
    "95.173.218.67:8081",
    "195.138.72.170:8080",
    "77.89.35.50:8080",
    "181.188.206.32:999",
    "72.195.34.42:4145",
    "185.18.250.83:80",
    "131.100.51.143:999",
    "47.239.241.230:1111",
]


class HttpClient:
    """
    Asynchronous HTTP client that routes requests through randomly selected proxies.

    Attributes:
        proxies (List[str]): List of proxy URLs (e.g., "http://user:pass@host:port").
        timeout (ClientTimeout): Timeout settings for requests.
        max_retries (int): Maximum number of retry attempts per request.
        connector (aiohttp.TCPConnector): Optional custom connector.
        session (aiohttp.ClientSession): Internal session, created lazily.
    """

    def __init__(
        self,
        proxies: List[str] = PROXIES,
        timeout: ClientTimeout = ClientTimeout(total=30),
        max_retries: int = 3,
        connector: Optional[aiohttp.TCPConnector] = None,
    ):
        """
        Initialize the HttpClient.

        Args:
            proxies: List of proxy URLs.
            timeout: aiohttp.ClientTimeout object.
            max_retries: Number of times to retry a request on failure.
            connector: Optional TCPConnector (e.g., for limiting connections).
        """
        self.proxies = proxies
        self.timeout = timeout
        self.max_retries = max_retries
        self.connector = connector or aiohttp.TCPConnector(
            ssl=False
        )  # disable SSL verification if needed
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazily create and return a ClientSession."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
            )
        return self.session

    def _get_random_proxy(self) -> str:
        """Return a random proxy from the list."""
        if not self.proxies:
            raise ValueError("Proxy list is empty")
        return random.choice(self.proxies)

    async def _request(
        self,
        method: str,
        url: str,
        retry_count: int = 0,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """
        Internal method to perform a request with proxy and retry logic.

        Args:
            method: HTTP method ('GET', 'POST', etc.).
            url: Request URL.
            retry_count: Current retry attempt number.
            **kwargs: Additional arguments passed to aiohttp.request().

        Returns:
            aiohttp.ClientResponse object.

        Raises:
            aiohttp.ClientError: If all retries fail.
        """
        proxy = self._get_random_proxy()
        logger.debug(
            f"Request {method} {url} via proxy {proxy} (attempt {retry_count + 1})"
        )

        session = await self._get_session()

        try:
            async with session.request(method, url, **kwargs) as response:
                # Trigger reading of response to ensure the request is fully processed
                await response.read()
                return response
        except (ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Request failed via proxy {proxy}: {e}")
            if retry_count < self.max_retries - 1:
                logger.info(
                    f"Retrying with a different proxy (attempt {retry_count + 2})"
                )
                return await self._request(method, url, retry_count + 1, **kwargs)
            else:
                logger.error(f"Max retries exceeded for {url}")
                raise

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """
        Perform a GET request through a random proxy.

        Args:
            url: Request URL.
            params: Query parameters.
            headers: HTTP headers.
            **kwargs: Additional arguments for aiohttp.

        Returns:
            aiohttp.ClientResponse.
        """
        return await self._request("GET", url, params=params, headers=headers, **kwargs)

    async def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """
        Perform a POST request through a random proxy.

        Args:
            url: Request URL.
            data: Form data.
            json: JSON data.
            headers: HTTP headers.
            **kwargs: Additional arguments for aiohttp.

        Returns:
            aiohttp.ClientResponse.
        """
        return await self._request(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    async def close(self):
        """Close the underlying aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def main():
    timeout = ClientTimeout(total=15)

    async with HttpClient(timeout=timeout, max_retries=3) as client:
        try:
            resp = await client.get("https://gomafia.pro/tournament/2428?tab=games")
            print(await resp.text())
        except Exception as e:
            print(f"Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
