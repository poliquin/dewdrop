#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command line interface to interact with the Dewey Data API.
"""

import argparse
import csv
import json
import logging
import sys

from typing import Generator

from .dewdrop import DeweyData


def info_writer(finfo: Generator, delimiter: str="\t") -> None:
    """Write file info to stdout."""
    row = next(finfo)
    wtr = csv.DictWriter(sys.stdout, delimiter=delimiter, fieldnames=row.keys())
    wtr.writeheader()
    wtr.writerow(row)
    wtr.writerows(finfo)


def main():
    dew = DeweyData()

    argp = argparse.ArgumentParser(description="Fetch data from Dewey Data.")
    subp = argp.add_subparsers(dest="cmd", required=True)

    comm = argparse.ArgumentParser(add_help=False)
    comm.add_argument("product", type=str, help="Product to fetch data for.")
    argp.add_argument("-k", "--key", type=str, help="API key.")
    argp.add_argument("-v", "--verbose", action="store_true", help="Enable log.")
    argp.add_argument("--params", type=json.loads, help="Additional parameters.")
    argp.add_argument("--debug", action="store_true", help="Enable debug mode.")
    argp.add_argument("--sleep", type=float, default=1.0, help="Delay between requests")

    meta = subp.add_parser("meta", help="Fetch metadata for product.", parents=[comm])
    meta.set_defaults(func=dew.get_meta)

    down = subp.add_parser("download", help="Download files for product.", parents=[comm])
    down.add_argument("dirpath", type=str, help="Directory to save files to.")
    down.add_argument("-n", "--no-partition", action="store_false", help="Do not partition files.")
    down.add_argument("-s", "--sep", type=str, default="\t", help="Output delimiter.")
    down.add_argument("-c", "--clobber", action="store_true", help="Overwrite existing files.")
    down.set_defaults(func=dew.download_files)

    roll = subp.add_parser("list", help="List files for product.", parents=[comm])
    roll.add_argument("-s", "--sep", type=str, default="\t", help="Output delimiter.")
    roll.set_defaults(func=dew.list_files)


    opts = argp.parse_args()
    dew.request_delay = opts.sleep
    if opts.key:
        dew._key = opts.key
    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    params = opts.params or {}

    if opts.debug: sys.exit(0)

    if opts.cmd == "meta":
        print(
            json.dumps(opts.func(opts.product, **params), indent=4)
        )

    elif opts.cmd == "download":
        finfo = opts.func(
            opts.dirpath, opts.product, opts.no_partition, opts.clobber, **params
        )
        info_writer(finfo, delimiter=opts.sep)

    elif opts.cmd == "list":
        finfo = opts.func(opts.product, **params)
        info_writer(finfo, delimiter=opts.sep)


if __name__ == "__main__":
    main()
