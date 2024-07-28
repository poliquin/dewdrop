Dew Drop: A command line tool for interacting with Dewey Data API
=================================================================

A simple Python 3 client for the Dewey Data API.

    > python -m dewdrop --help

    usage: __main__.py [-h] [-k KEY] [-v] [--params PARAMS] [--debug]
                       [--sleep SLEEP]
                       product {meta,download,list} ...
    
    Fetch data from Dewey Data.
    
    positional arguments:
      product               Product to fetch data for.
      {meta,download,list}
        meta                Fetch metadata for product.
        download            Download files for product.
        list                List files for product.
    
    options:
      -h, --help            show this help message and exit
      -k KEY, --key KEY     API key.
      -v, --verbose         Enable log.
      --params PARAMS       Additional parameters.
      --debug               Enable debug mode.
      --sleep SLEEP         Delay between requests


## Commands

### `meta`

Get metadata for a product. For example, if the product identifier is
something like `978cz-306w`, then the command would be:

    python -m dewdrop 978cz-306w meta

By default, the API key is read from the `DEWEY_API_KEY` environment variable.
To set it manually, use the `key` option:

    python -m dewdrop 978cz-306w -k YOUR_API_KEY meta

### `list`

List all file info for a product.

    python -m dewdrop 978cz-306w list

The file information will be written to standard output.

### `download`

Download all files for a product.

    python -m dewdrop 978cz-306w download destination-folder-path

Files will be placed in `destination-folder-path`, which will be created if
it does not exist. Additionally, the file information will be written to
standard output as with the `list` command.

By default, the downloaded files will be organized by the `partition_key`
value that the API returns which each file. To ignore this, specify the
option `--no-partition`.

#### Request parameters

Additional parameters can be passed to the API using the `--params` option.
This is useful when downloading partitioned products. The option expects a
JSON object, which can be difficult to enter as a string on the command line.
One option is to put the parameters in a JSON file and pass the file contents
to the argument like this:

    python -m dewdrop --params "$(<params.json)" 978cz-306w download destination-folder-path

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
