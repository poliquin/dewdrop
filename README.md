Dew Drop: A command line tool for the Dewey Data API
====================================================

A simple Python 3 client for the Dewey Data API that can be used to fetch
product information and download files.

    usage: dewdrop [-h] [-k KEY] [-v] [--params PARAMS] [--debug] [--sleep SLEEP]
                   {meta,describe,download,list} ...

    Fetch data from Dewey Data.

    positional arguments:
      {meta,describe,download,list}
        meta                Fetch metadata for product.
        describe            Fetch description of product.
        download            Download files for product.
        list                List files for product.

    options:
      -h, --help            show this help message and exit
      -k KEY, --key KEY     API key.
      -v, --verbose         Enable log.
      --params PARAMS       Additional parameters.
      --debug               Enable debug mode.
      --sleep SLEEP         Delay between requests

_NOTE: I have no affiliation with Dewey Data and this is not an official
Dewey Data client. If you're looking for an official Python client,
try [`deweypy`](https://github.com/Dewey-Data/deweypy)._


## Installation

The package requires Python 3.10 or later and can be installed from PyPI:

    pip install dewdrop


## Identifying products

Every command takes a product identifier. In the Dewey web app, each table
has an API URL that looks like this:

    https://api.deweydata.io/api/v1/external/data/prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy

Either the full URL or the identifier at the end of it (here,
`prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy`) can be used with `dewdrop`. Note
that the identifier includes the project (`prj_`) as well as the folder
(`fldr_`).


## Commands

### `meta`

Get metadata (file count, total size, partitioning) for a product:

    dewdrop meta prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy

By default, the API key is read from the `DEWEY_API_KEY` environment variable.
To set it manually, use the `key` option:

    dewdrop -k YOUR_API_KEY meta prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy

### `describe`

Get the description of a product, which includes the dataset name, the data
partner, the version timestamp, and DOI information when available:

    dewdrop describe prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy

### `list`

List all file info for a product.

    dewdrop list prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy

The file information will be written to standard output. You can, of course,
redirect this to a file if you want to save it:

    dewdrop list prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy > file_info.tsv

See `dewdrop list --help` for full options.

### `download`

Download all files for a product.

    dewdrop download prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy destination-folder-path

Files will be placed in `destination-folder-path`, which will be created if
it does not exist. Additionally, the file information will be written to
standard output as with the `list` command.

By default, the downloaded files will be organized by the `partition_key`
value that the API returns with each file. To ignore this, specify the
option `--no-partition`. See `dewdrop download --help` for full options.

Files that already exist in the destination with the size reported by the
API are skipped, so an interrupted download can be resumed by re-running the
same command. Use `--clobber` to download everything again.

#### Request parameters

Additional parameters can be passed to the API using the `--params` option.
This is useful when downloading partitioned products. The option expects a
JSON object, which can be difficult to enter as a string on the command line.
One option is to put the parameters in a JSON file and pass the file contents
to the argument like this:

    dewdrop --params "$(<params.json)" download prj_xxxxxxxx__fldr_yyyyyyyyyyyyyyyy destination-folder-path

Where a `params.json` file to download data for 2022 might look like this:

    {
    "partition_key_after":  "2022-01-01",
    "partition_key_before": "2022-12-31"
    }

Both bounds are inclusive.

### Checking output

Each file is downloaded to a temporary `.part` file, its size is compared to
the size reported by the API, and only then is it moved into place. A
mismatch is retried and, if it persists, reported as an error. To confirm
the file count after a download finishes, compare the `total_files` value
from `meta` with:

    find destination-folder-path -type f | wc -l
