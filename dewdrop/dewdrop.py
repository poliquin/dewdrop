
"""
Interact with Dewey Data API.
"""

import logging
import os
import requests
import time

from pathlib import Path
from typing import Generator


class ExtendedSession(requests.Session):
    """A requests session that retries and delays requests as needed."""

    def __init__(self, max_tries: int = 5, delay: float = 1.0, headers: dict|None = None):
        super().__init__()
        self.headers.update(headers or {})

        self.max_tries: int = int(max_tries)
        self.retry_delay: float = 180
        self.request_delay: float = float(delay)
        self._last_request_time: float = 0

    def _delay(self) -> None:
        """Delay between requests."""
        time_since_last_request = time.time() - self._last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        self._last_request_time = time.time()

    def request(self, method: str|bytes, url: str|bytes, **kwargs) -> requests.Response:  # pyright: ignore
        """Make a request with retries and delays as necessary."""

        if self.request_delay > 0:
            self._delay()

        tries = 0
        while tries < self.max_tries:
            tries += 1

            try:
                resp = super().request(method, url, **kwargs)

                # don't bother retrying if not found or access denied
                if resp.status_code in (403, 404):
                    logging.critical("Request to %s failed with status %d", url, resp.status_code)
                    break

                resp.raise_for_status()
                return resp

            except requests.RequestException as e:
                logging.error("Request failed: %s", e)
                if tries < self.max_tries:
                    time.sleep(self.retry_delay * (2 ** (tries - 1)))
                    logging.debug("Retrying request to %s", url)

        raise requests.RequestException(
            f"Request to {url} failed after {tries} {'try' if tries == 1 else 'tries'}"
        )


class DeweyData(ExtendedSession):
    """Interact with Dewey Data API."""

    def __init__(self, key: str|None = None, sleep: float = 1.0):

        super().__init__(delay = float(sleep))
        self._base_url = "https://app.deweydata.io/external-api/v3/products"
        self.key = os.getenv("DEWEY_API_KEY") if key is None else key

    @property
    def key(self) -> str|None:
        return self._key

    @key.setter
    def key(self, key: str|None) -> None:
        self._key = key
        self._set_api_header()

    def _set_api_header(self) -> None:
        """Set the API key header."""
        headers = {"X-API-KEY": self._key, "accept": "application/json"}
        self.headers.update(headers)

    def _get(self, url: str, params: dict|None = None) -> dict:
        """Make an API request."""
        return self.request("GET", url, params=params).json()

    def get_meta(self, product: str, **kwargs) -> dict:
        """Download metadata for product."""

        logging.debug("Fetching metadata for %s", product)
        return self._get(f"{self._base_url}/{product}/files/metadata", kwargs)

    def get_files(self, product: str, **kwargs) -> Generator[dict, None, None]:
        """Download metadata for product."""

        # use metadata to determine default partitioning
        meta = self.get_meta(product)

        if meta["partition_type"] == "DATE":
            params: dict = {
                "partition_key_after": "1900-01-01", "partition_key_before": "2099-12-31"
            }
        else:
            params = {}

        params |= kwargs

        i = 1
        while True:
            params["page"] = i
            response = self._get(f"{self._base_url}/{product}/files", params)
            logging.debug(
                "Fetched page %d of %d for %s file list", i, response["total_pages"], product
            )
            logging.debug(
                f"""
                ===== {product} =====
                Page: {response["page"]}
                Number of Files for Page: {response["number_of_files_for_page"]}
                Average File Size for Page: {response["avg_file_size_for_page"]}
                Total Files: {response["total_files"]}
                Total Pages: {response["total_pages"]}
                Total Size: {response["total_size"]}
                Expires At: {response["expires_at"]}
                """
            )

            links = response.pop("download_links")
            yield from (d | response for d in links)

            if i >= response["total_pages"]:
                break
            i += 1

    def download_files(
            self, dirpath: str, product: str, partition: bool=True, clobber: bool=False, **kwargs
        ) -> Generator[dict, None, None]:
        """Download files for product."""

        dp = Path(dirpath)
        dp.mkdir(parents=True, exist_ok=True)

        for file in self.get_files(product, **kwargs):

            if partition and file['partition_key'] is not None:
                fpath = dp / file["partition_key"] / file["file_name"]
            else:
                # file names can repeat across pages of the same product,
                # include page number in the path for multi-page products
                if file["total_pages"] == 1:
                    fpath = dp / file["file_name"]
                else:
                    fpath = dp / f"page-{file['page']}" / file["file_name"]

            if not clobber and fpath.exists():
                logging.debug("Skipping existing file %s", fpath)
                continue

            logging.debug("Downloading %s", file["file_name"])
            req = self.request("GET", file["link"])

            fpath.parent.mkdir(parents=True, exist_ok=True)
            with open(fpath, "wb") as f:
                f.write(req.content)

            yield file

    def list_files(self, product: str, **kwargs) -> Generator[dict, None, None]:
        """List files for product."""
        logging.debug("Listing files for %s", product)
        yield from self.get_files(product, **kwargs)
