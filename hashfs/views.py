
import re
import os
import json
import binascii
import hashlib
import time
from datetime import datetime
import logging
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
from django.core.servers.basehttp import FileWrapper
from rest_framework.decorators import api_view
from two1.lib.bitserv.django import payment
import hashfs.settings as settings

logger = logging.getLogger(__name__)

blank_re = re.compile('^\s*$')

SQLS_HASH_QUERY = "SELECT val_size,time_create,time_expire,content_type FROM metadata WHERE hash = ?"
SQLS_HASH_INSERT = "INSERT INTO metadata(hash,val_size,time_create,time_expire,content_type,pubkey_addr) VALUES(?, ?, ?, ?, ?, NULL)"

def httpdate(dt):
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).

    The supplied date must be in UTC.

    """
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
        dt.year, dt.hour, dt.minute, dt.second)

@api_view(['GET'])
def home(request):
    # export API endpoint metadata
    home_obj = [
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
    body = json.dumps(home_obj)
    return HttpResponse(body, content_type='application/json')


def make_hashfs_fn(hexstr, make_dirs=False):
    dir1 = hexstr[:3]
    dir2 = hexstr[3:6]

    dir1_pn = "%s%s" % (settings.HASHFS_ROOT_DIR, dir1)
    dir2_pn = "%s%s/%s" % (settings.HASHFS_ROOT_DIR, dir1, dir2)
    fn = "%s%s/%s/%s" % (settings.HASHFS_ROOT_DIR, dir1, dir2, hexstr)

    if not make_dirs:
        return fn

    try:
        if not os.path.isdir(dir2_pn):
            if not os.path.isdir(dir1_pn):
                os.mkdir(dir1_pn)
            os.mkdir(dir2_pn)
    except OSError:
        return False

    return fn


@api_view(['GET'])
@payment.required(1)
def hashfs_get(request, hexstr):

    # decode hex string param
    hexstr = hexstr.lower()
    try:
        hash = binascii.unhexlify(hexstr)
    except TypeError:
        return HttpResponseBadRequest("invalid hash")

    if len(hash) != 32:
        return HttpResponseBadRequest("invalid hash length")

    # get sqlite handle
    connection = settings.HASHFS_DB
    cursor = connection.cursor()

    # query for metadata
    md = {}
    for md_size,md_created,md_expires,md_ctype in cursor.execute(SQLS_HASH_QUERY, (hexstr,)):
        md['size'] = int(md_size)
        md['created'] = int(md_created)
        md['expires'] = int(md_expires)
        md['content_type'] = md_ctype

    if len(md.keys()) != 4:
        return HttpResponseNotFound("hash metadata not found")

    # set up FileWrapper to return data
    filename = make_hashfs_fn(hexstr)

    try:
        wrapper = FileWrapper(open(filename))
    except:
        logger.error("failed read " + filename)
        return HttpResponseServerError("hash data read failure")

    dt = datetime.fromtimestamp(md['created'])
    last_mod = httpdate(dt)

    response = HttpResponse(wrapper, content_type='application/octet-stream')
    response['Content-Length'] = md['size']
    response['Content-Type'] = md['content_type']
    response['ETag'] = hexstr
    response['Last-Modified'] = last_mod
    return response


@api_view(['PUT'])
@payment.required(1)
def hashfs_put(request, hexstr):

    # decode hex string param
    hexstr = hexstr.lower()
    try:
        hash = binascii.unhexlify(hexstr)
    except TypeError:
        return HttpResponseBadRequest("invalid hash")

    if len(hash) != 32:
        return HttpResponseBadRequest("invalid hash length")

    # check file existence; if it exists, no need to proceed further
    # create dir1/dir2 hierarchy if need be
    filename = make_hashfs_fn(hexstr, True)
    if filename is None:
        return HttpResponseServerError("local storage failure")
    if os.path.isfile(filename):
        return HttpResponseBadRequest("hash already exists")

    # get data in memory, up to 100M (limit set in nginx config)
    body = request.body
    body_len = len(body)

    # hash data
    h = hashlib.new('sha256')
    h.update(body)

    # verify hash matches provided
    if h.hexdigest() != hexstr:
        return HttpResponseBadRequest("hash invalid - does not match data")

    # verify content-length matches provided
    if int(request.META['CONTENT_LENGTH']) != body_len:
        return HttpResponseBadRequest("content-length invalid - does not match data")

    # get content-type
    ctype = request.META['CONTENT_TYPE']
    if blank_re.match(ctype):
        ctype = 'application/octet-stream'

    # write to filesystem
    try:
        outf = open(filename, 'wb')
        outf.write(body)
        outf.close()
    except OSError:
        return HttpResponseServerError("local storage failure")
    body = None

    # get sqlite handle
    connection = settings.HASHFS_DB
    cursor = connection.cursor()

    # Create, expiration times
    tm_creat = int(time.time())
    tm_expire = tm_creat + (24 * 60 * 60)

    # Add hash metadata to db
    # TODO: test for errors, unlink file if so
    cursor.execute(SQLS_HASH_INSERT, (hexstr, body_len, tm_creat, tm_expire, ctype))

    return HttpResponse('true', content_type='application/json')

