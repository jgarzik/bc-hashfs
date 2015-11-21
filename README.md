
hashfs API service
==================

Summary
-------
This is an API service that provides a hash-based REST GET/PUT, providing
content-addressable data storage services.

The intention is to have many people/organizations run a hashfs service,
creating a decentralized storage mesh.

This project aims towards a robust, high performance API service
using flask, nginx and 21BC.


Theory of Operation
-------------------
The interface is very REST-ful, and intended to behave similarly
to Amazon S3 storage API, which remembers metadata such as content-type.

API users upload data using PUT.  Data is guaranteed to be stored
_at least_ until its expiration date (T + 24 hours), if not longer.

Data may live longer than the minimum guaranteed lifetime.  Data is
removed only when the system reaches total storage capacity, a new data
item is to be added, and sufficient expired data exists to be freed.
HASHFS_MAX_GB in settings.py controls system storage capacity.

In addition, API users may specify a public key hash (bitcoin address)
for authenticating certain requests such as delete (when implemented).


API Overview
============

* GET /
* GET /hashfs/1/$hash
* PUT /hashfs/1/$hash

$hash is the hex-encoded SHA256 hash of the data.

API Pricing
===========

* GET requests: 1 satoshi/request + 2 satoshis/MB transfer
* PUT requests: 1 satoshi/request

Installation
============

Install packages
----------------

	sudo apt-get install sqlite3

Create metadata database for storing file information
-----------------------------------------------------

	./mkdb.sh

Run the server
--------------

	python3 hashfs-server.py

Now test your endpoint!

API Reference
=============

GET /
-----
Returns: application/json list describing all services at this endpoint

Example output (excluding comments):

    [
        {
            "name": "hashfs/1",           # service 'hashfs', version '1'
            "pricing-type": "per-rpc",    # indicates layout of "pricing"
            "pricing" : [
                {
                    "rpc": "get",
                    "per-req": 1,         # 1 satoshi per request
                    "per-kb": 10,         # 10 satoshis per 1000 bytes
                },
                {
                    "rpc": "put",
                    "per-req": 1,         # 1 satoshi per request
                    "per-kb": 10,         # 10 satoshis per 1000 bytes
                    "per-hour": 2,        # 2 satoshis per hour to keep alive
                },

                # default pricing, if no specific match
                {
                    "rpc": True,          # True = indicates default
                    "per-req": 1,         # 1 satoshi per request
                },
            ]
        }
    ]

GET /hashfs/1/$hash
-------------------
Returns:  Document whose SHA256 checksum is $hash, or 404-not-found

Headers returned:
* Content-Length
* Content-Type
* ETag
* Last-Modified


PUT /hashfs/1/$hash
-------------------
Returns:  application/json value "true" if stored, or an HTTP error

$hash must match the input data's SHA256 checksum.

Headers evaluated:
* Content-Length: Must be present and accurate.
* Content-Type: Optional; If not specified, set to application/octet-stream
* X-HashFS-PKH: Optional; If specified, stored, and used for authenticating requests


Command Line Interface
======================

The ```hashcli.py``` tool provides command line access to any hashfs endpoint.

Command: help
-------------
The tool and all sub-commands support "--help" to provide command line help.

	$ hashcli.py --help

	$ hashcli.py get --help


Command: info
-------------

	$ hashcli.py info > endpoint.json


Command: get
------------

	$ hashcli.py get 45cf8aa8e740c3c0c48b5aaceaceae64f58d18379c35059cdf57a5802cd89f2c > myfile.dat


Command: put
------------

	$ hashcli.py put README.md
	45cf8aa8e740c3c0c48b5aaceaceae64f58d18379c35059cdf57a5802cd89f2c

