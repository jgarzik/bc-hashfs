
This is an API service that provides a hash-based REST GET/PUT, providing
content-addressible data storage services.

The interface is very REST-ful, and intended to behave similarly
to Amazon S3 storage API, which remembers metadata such as content-type.

In addition, PUT may specify a public key hash (bitcoin address)
for authenticating certain requests such as delete (when implemented).


API Overview
============

* GET /
* GET /hashfs/1/$hash
* PUT /hashfs/1/$hash

$hash is the hex-encoded SHA256 hash of the data.

API Pricing
===========

* GET requests: 1 satoshi
* PUT requests: 1 satoshi

Installation
============

Install packages
----------------

	sudo apt-get install sqlite3 python3-django nginx \
		python3-djangorestframework \
		uwsgi-plugin-python3 uwsgi python3-uwsgidecorators

nginx setup & restart
---------------------

	etc/apiservice.conf to /etc/nginx/sites-enabled

create metadata database for storing file information
-----------------------------------------------------

	./mkdb.sh

run uwsgi
---------

	uwsgi_python3 --ini uwsgi.ini

test your endpoint!
-------------------

stop the server
---------------

	uwsgi --stop /tmp/hashfs-uwsgi.pid

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

