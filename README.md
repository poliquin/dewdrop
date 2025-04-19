Dew Drop: A command line tool for the Dewey Data API
====================================================

A simple Python 3 client for the Dewey Data API that can be used to fetch
product information and download files.

    usage: dewdrop [-h] [-k KEY] [-v] [--params PARAMS] [--debug] [--sleep SLEEP]
                   {meta,tables,download,list} ...

    Fetch data from Dewey Data.

    positional arguments:
      {meta,tables,download,list}
        meta                Fetch metadata for product.
        tables              List tables for multi-table product.
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
Dewey Data client._


## Installation

The package can be installed from PyPI:

    pip install dewdrop


## Commands

### `meta`

Get metadata for a product. For example, if the product identifier is
something like `978cz-306w`, then the command would be:

    dewdrop meta 978cz-306w

By default, the API key is read from the `DEWEY_API_KEY` environment variable.
To set it manually, use the `key` option:

    dewdrop -k YOUR_API_KEY meta 978cz-306w

To list tables in multi-table products, use the `--multi-table` (`-m`) option:

    dewdrop meta 438cd-211x -m

To list metadata for a particular table, use the `--table-name` (`-t`) option:

    dewdrop meta 438cd-211x -t "Table Name"

See `dewdrop meta --help` for full options.

### `tables`

List all tables for a multi-table product with one table name per line and no
other metadata. This is useful for using table names in pipelines:

    dewdrop tables 438cd-211x | xargs -I {} echo "Processing {}"

### `list`

List all file info for a product.

    dewdrop list 978cz-306w

The file information will be written to standard output. You can, of course,
redirect this to a file if you want to save it:

    dewdrop list 978cz-306w > file_info.tsv

To list files for a particular table, use the `--table-name` (`-t`) option:

    dewdrop list 438cd-211x -t "Table Name"

See `dewdrop list --help` for full options.

### `download`

Download all files for a product.

    dewdrop download 978cz-306w destination-folder-path

Files will be placed in `destination-folder-path`, which will be created if
it does not exist. Additionally, the file information will be written to
standard output as with the `list` command.

By default, the downloaded files will be organized by the `partition_key`
value that the API returns which each file. To ignore this, specify the
option `--no-partition`. See `dewdrop download --help` for full options.

To download files for a particular table, use the `--table-name` (`-t`) option:

    dewdrop download 438cd-211x destination-folder-path -t "Table Name"

#### Request parameters

Additional parameters can be passed to the API using the `--params` option.
This is useful when downloading partitioned products. The option expects a
JSON object, which can be difficult to enter as a string on the command line.
One option is to put the parameters in a JSON file and pass the file contents
to the argument like this:

    dewdrop --params "$(<params.json)" download 978cz-306w destination-folder-path

Where a `params.json` file to download data for 2022 might look like this:

    {
    "partition_key_after":  "2022-01-01",
    "partition_key_before": "2022-12-31"
    }

### Checking output

Currently, there is no way to verify the downloaded files. One option is
to use the `-v` option to enable verbose logging, which will show the total
number of files. This can be compared to the downloaded files with:

    # confirm file count
    find destination-folder-path -type f | wc -l

The output file list will also contain file sizes, which can be compared to
the downloaded files, although currently there is no automatic way to make
this comparison using the script.
