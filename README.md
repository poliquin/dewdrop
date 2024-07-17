Interact with Dewey Data API
============================

A simple Python 3 client for the Dewey Data API.

    > python dewey.py --help

    usage: dewey.py [-h] [-k KEY] [-v] [--params PARAMS] [--debug]
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

## Commands

### `meta`

Get metadata for a product. For example, if the product identifier is
something like `978cz-306w`, then the command would be:

    python dewey.py 978cz-306w meta

By default, the API key is read from the `DEWEY_API_KEY` environment variable.
To set it manually, use the `key` option:

    python dewey.py 978cz-306w -k YOUR_API_KEY meta

### `list`

List all file info for a product.

    python dewey.py 978cz-306w list

The file information will be written to standard output.

### `download`

Download all files for a product.

    python dewey.py 978cz-306w download destination-folder-path

Files will be placed in `destination-folder-path`, which will be created if
it does not exist. Additionally, the file information will be written to
standard output as with the `list` command.

By default, the downloaded files will be organized by the `partition_key`
value that the API returns which each file. To ignore this, specify the
option `--no-partition`.
