
This is an API service that provides a hash-based REST GET/PUT, providing
content-addressible data storage services.


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

	# DANGER: deletes existing metadata db
	./mkdb.sh

run uwsgi
---------

	uwsgi_python3 --ini uwsgi.ini

test your endpoint!
-------------------

stop the server
---------------

	uwsgi --stop /tmp/hashfs-uwsgi.pid

