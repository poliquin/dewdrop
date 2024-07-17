#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interact with Dewey Data API.
"""

import csv
import logging
import os
import requests
import sys
import time

from pathlib import Path
from pprint import pprint
from typing import Generator


class DeweyData:

    def __init__(self, key: str|None = None, sleep: float = 0.6):

        self._base_url = "https://app.deweydata.io/external-api/v3/products"
        self._key = os.getenv("DEWEY_API_KEY") if key is None else key
        self.sleep = float(sleep)

    def _get(self, url: str, params: dict|None = None) -> dict:
        """Make an API request."""

        headers = {"X-API-KEY": self._key, "accept": "application/json"}
        req = requests.get(url, params=params, headers=headers)
        req.raise_for_status()
        time.sleep(self.sleep)

        return req.json()

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
                 Total Files: {response["total_files"]}
                 Total Pages: {response["total_pages"]}
                  Total Size: {response["total_size"]}
                  Expires At: {response["expires_at"]}
                  Page Files: {response["number_of_files_for_page"]}
                """
            )

            yield from response["download_links"]
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
            if partition:
                fpath = dp / file["partition_key"] / file["file_name"]
                fpath.parent.mkdir(parents=True, exist_ok=True)
            else:
                fpath = dp / file["file_name"]

            if not clobber and fpath.exists():
                logging.debug("Skipping existing file %s", fpath)
                continue

            logging.debug("Downloading %s", file["file_name"])
            req = requests.get(file["link"])
            req.raise_for_status()

            with open(fpath, "wb") as f:
                f.write(req.content)

            yield file

    def list_files(self, product: str, **kwargs) -> Generator[dict, None, None]:
        """List files for product."""
        logging.debug("Listing files for %s", product)
        yield from self.get_files(product, **kwargs)


def info_writer(finfo: Generator, delimiter="\t") -> None:
    """Write file info to stdout."""
    row = next(finfo)
    wtr = csv.DictWriter(sys.stdout, delimiter=delimiter, fieldnames=row.keys())
    wtr.writeheader()
    wtr.writerow(row)
    wtr.writerows(finfo)


if __name__ == "__main__":
    import argparse
    import json

    dew = DeweyData()

    argp = argparse.ArgumentParser(description="Fetch data from Dewey Data.")
    argp.add_argument("product", type=str, help="Product to fetch data for.")
    argp.add_argument("-k", "--key", type=str, help="API key.")
    argp.add_argument("-v", "--verbose", action="store_true", help="Enable log.")
    argp.add_argument("--params", type=json.loads, help="Additional parameters.")
    argp.add_argument("--debug", action="store_true", help="Enable debug mode.")
    argp.add_argument("--sleep", type=float, default=0.6, help="Delay between requests")

    subp = argp.add_subparsers(dest="cmd", required=True)

    meta = subp.add_parser("meta", help="Fetch metadata for product.")
    meta.set_defaults(func=dew.get_meta)

    down = subp.add_parser("download", help="Download files for product.")
    down.add_argument("dirpath", type=str, help="Directory to save files to.")
    down.add_argument("-n", "--no-partition", action="store_false", help="Do not partition files.")
    down.add_argument("-s", "--sep", type=str, default="\t", help="Output delimiter.")
    down.add_argument("-c", "--clobber", action="store_true", help="Overwrite existing files.")
    down.set_defaults(func=dew.download_files)

    roll = subp.add_parser("list", help="List files for product.")
    roll.add_argument("-s", "--sep", type=str, default="\t", help="Output delimiter.")
    roll.set_defaults(func=dew.list_files)


    opts = argp.parse_args()
    dew.sleep = opts.sleep
    if opts.key:
        dew._key = opts.key
    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    params = opts.params or {}

    if opts.debug: sys.exit(0)

    if opts.cmd == "meta":
        pprint(opts.func(opts.product, **params))

    elif opts.cmd == "download":
        finfo = opts.func(
            opts.dirpath, opts.product, opts.no_partition, opts.clobber, **params
        )
        info_writer(finfo, delimiter=opts.sep)

    elif opts.cmd == "list":
        finfo = opts.func(opts.product, **params)
        info_writer(finfo, delimiter=opts.sep)
