"""
Interact with Dewey Data API.
"""

import logging
import os
import requests
import time

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Generator

try:
    __version__ = version("dewdrop")
except PackageNotFoundError:
    __version__ = "dev"

BASE_URL = "https://api.deweydata.io/api/v1/external/data"

# Only these statuses can plausibly succeed on retry.
RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class DeweyRequestError(requests.RequestException):
    """A request that failed and should not be retried further."""


class DewdropError(Exception):
    """Base class for errors raised by dewdrop itself."""


class IncompleteDownload(DewdropError):
    """A downloaded file does not have the size reported by the API."""


class DuplicateFileName(DewdropError):
    """Two different files in a listing would be written to the same path."""


def _error_detail(resp: requests.Response) -> str:
    """Extract the error message the API puts in the response body."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200].strip()
    if isinstance(body, dict):
        for k in ("detail", "error", "error_message", "message"):
            if k in body:
                return str(body[k])
    return str(body)[:200]


class ExtendedSession(requests.Session):
    """A requests session that retries and delays requests as needed."""

    def __init__(self, max_tries: int = 5, delay: float = 1.0, headers: dict|None = None):
        super().__init__()
        self.headers.update(headers or {})

        self.max_tries: int = int(max_tries)
        self.retry_delay: float = 30
        self.max_retry_delay: float = 600
        self.request_delay: float = float(delay)
        # (connect, read) seconds; requests has no timeout by default and a
        # stalled connection would otherwise hang forever
        self.timeout: tuple[float, float] = (30, 120)
        self._last_request_time: float = 0

    def _delay(self) -> None:
        """Delay between requests."""
        time_since_last_request = time.time() - self._last_request_time
        if time_since_last_request < self.request_delay:
            time.sleep(self.request_delay - time_since_last_request)
        self._last_request_time = time.time()

    def _retry_wait(self, attempt: int, resp: requests.Response|None = None) -> float:
        """Seconds to wait before the next attempt, honoring Retry-After if sent."""
        if resp is not None:
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                return float(retry_after)
        return min(self.retry_delay * (2 ** (attempt - 1)), self.max_retry_delay)

    def request(self, method: str|bytes, url: str|bytes, **kwargs) -> requests.Response:  # pyright: ignore
        """Make a request with retries and delays as necessary."""

        if self.request_delay > 0:
            self._delay()
        kwargs.setdefault("timeout", self.timeout)

        err = ""
        for attempt in range(1, self.max_tries + 1):
            resp = None
            try:
                resp = super().request(method, url, **kwargs)
            except requests.RequestException as e:
                err = str(e)
            else:
                if resp.ok:
                    return resp
                err = f"HTTP {resp.status_code} {_error_detail(resp)}"
                if resp.status_code not in RETRY_STATUS:
                    raise DeweyRequestError(f"Request to {url} failed: {err}", response=resp)

            logging.error("Request to %s failed (try %d of %d): %s", url, attempt, self.max_tries, err)
            if attempt < self.max_tries:
                wait = self._retry_wait(attempt, resp)
                logging.debug("Retrying request to %s in %.0f seconds", url, wait)
                time.sleep(wait)

        raise DeweyRequestError(f"Request to {url} failed after {self.max_tries} tries: {err}")


class DeweyData(ExtendedSession):
    """Interact with Dewey Data API."""

    def __init__(self, key: str|None = None, sleep: float = 1.0):

        headers = {"User-Agent": f"dewdrop/{__version__}", "accept": "application/json"}
        super().__init__(delay = float(sleep), headers=headers)
        self._base_url = BASE_URL
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
        if self._key:
            self.headers["X-API-KEY"] = self._key
        else:
            self.headers.pop("X-API-KEY", None)

    def _url(self, product: str, endpoint: str) -> str:
        """Build an endpoint URL for a product.

        The product can be an identifier (e.g. prj_xxx__fldr_yyy) or the full
        API URL shown in the Dewey web app, which ends in that identifier.
        """
        if product.startswith(("http://", "https://")):
            base = product.rstrip("/")
        else:
            base = f"{self._base_url}/{product}"
        return f"{base}/{endpoint}"

    def _get(self, url: str, params: dict|None = None) -> dict:
        """Make an API request."""
        return self.request("GET", url, params=params).json()

    def get_meta(self, product: str, **kwargs) -> dict:
        """Download metadata for product."""

        logging.debug("Fetching metadata for %s", product)
        return self._get(self._url(product, "metadata"), kwargs)

    def describe(self, product: str, **kwargs) -> dict:
        """Download description (name, partner, version, DOI) for product."""

        logging.debug("Fetching description for %s", product)
        return self._get(self._url(product, "describe"), kwargs)

    def get_files(self, product: str, **kwargs) -> Generator[dict, None, None]:
        """Get list of files for product."""

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
            response = self._get(self._url(product, "files"), params)
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

    def _download(self, link: str, fpath: Path, expected_size: int|None) -> None:
        """Stream a file to disk, verify its size, and move it into place."""

        # write to a temporary name so an interrupted download is never
        # mistaken for a complete file when the command is re-run
        tmp = fpath.with_name(fpath.name + ".part")
        fpath.parent.mkdir(parents=True, exist_ok=True)

        # download links carry their own secret, so the API key is not needed
        with self.request("GET", link, stream=True, headers={"X-API-KEY": None}) as resp:
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    f.write(chunk)

        size = tmp.stat().st_size
        if expected_size is not None and size != expected_size:
            tmp.unlink()
            raise IncompleteDownload(
                f"Downloaded {size} bytes for {fpath.name}, expected {expected_size}"
            )
        tmp.replace(fpath)

    def download_files(
            self,
            dirpath: str,
            product: str,
            partition: bool = True,
            clobber: bool = False,
            **kwargs
        ) -> Generator[dict, None, None]:
        """Download files for product."""

        dp = Path(dirpath)
        dp.mkdir(parents=True, exist_ok=True)

        # paths seen in this run, so that a repeated file name is caught
        # rather than silently skipped or overwritten
        seen: dict[Path, str] = {}

        for file in self.get_files(product, **kwargs):

            if partition and file["partition_key"] is not None:
                fpath = dp / file["partition_key"] / file["file_name"]
            else:
                fpath = dp / file["file_name"]

            if fpath in seen:
                if seen[fpath] == file["external_id"]:
                    logging.debug("Skipping repeated listing of %s", fpath)
                    continue
                raise DuplicateFileName(
                    f"{file['file_name']} appears more than once in the listing "
                    f"({seen[fpath]} and {file['external_id']}); refusing to overwrite {fpath}"
                )
            seen[fpath] = file["external_id"]

            if not clobber and fpath.exists():
                if fpath.stat().st_size == file["file_size_bytes"]:
                    logging.debug("Skipping existing file %s", fpath)
                    continue
                logging.warning("Existing file %s has wrong size, downloading again", fpath)

            logging.debug("Downloading %s (%d bytes)", file["file_name"], file["file_size_bytes"])
            for attempt in range(1, self.max_tries + 1):
                try:
                    self._download(file["link"], fpath, file["file_size_bytes"])
                    break
                except DeweyRequestError:
                    # request() has already retried what it could
                    raise
                except (requests.RequestException, IncompleteDownload) as e:
                    # failures partway through the stream are not seen by request()
                    logging.error(
                        "Download of %s failed (try %d of %d): %s",
                        file["file_name"], attempt, self.max_tries, e
                    )
                    if attempt == self.max_tries:
                        raise
                    time.sleep(self._retry_wait(attempt))

            yield file

    def list_files(self, product: str, **kwargs) -> Generator[dict, None, None]:
        """List files for product."""
        logging.debug("Listing files for %s", product)
        yield from self.get_files(product, **kwargs)
