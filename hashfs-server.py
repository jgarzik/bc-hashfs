
import re
import os
import json
import binascii
import hashlib
import time
import base58
from datetime import datetime
import logging
import apsw
import pprint

pp = pprint.PrettyPrinter(indent=2)

# import flask web microframework
from flask import Flask
from flask import request
from flask import abort

# import from the 21 Developer Library
from two1.lib.wallet import Wallet
from two1.lib.bitserv.flask import Payment

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)

HASHFS_ROOT_DIR = "hashroot/"
HASHFS_MAX_GB = 2
HASHFS_DB = apsw.Connection("hashfs.sqlite3")

blank_re = re.compile('^\s*$')

SQLS_HASH_QUERY = "SELECT size,time_create,time_expire,content_type FROM metadata WHERE hash = ?"
SQLS_HASH_INSERT = "INSERT INTO metadata(hash,size,time_create,time_expire,content_type,pubkey_addr) VALUES(?, ?, ?, ?, ?, ?)"
SQLS_TOTAL_SIZE = "SELECT SUM(size) FROM metadata"
SQLS_EXPIRED = "SELECT hash,size FROM metadata WHERE time_expire < ? ORDER BY time_expire"
SQLS_EXPIRE_LIST = "DELETE FROM metadata WHERE "
SQLS_HASH_SIZE = "SELECT size FROM metadata WHERE hash = ?"



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


def make_hashfs_fn(hexstr, make_dirs=False):
    dir1 = hexstr[:3]
    dir2 = hexstr[3:6]

    dir1_pn = "%s%s" % (HASHFS_ROOT_DIR, dir1)
    dir2_pn = "%s%s/%s" % (HASHFS_ROOT_DIR, dir1, dir2)
    fn = "%s%s/%s/%s" % (HASHFS_ROOT_DIR, dir1, dir2, hexstr)

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


def hashfs_total_size(cursor):
    row = cursor.execute(SQLS_TOTAL_SIZE).fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])

def hashfs_free_space(cursor):
    max_size = HASHFS_MAX_GB * 1000 * 1000 * 1000
    return max_size - hashfs_total_size(cursor)

def hashfs_expired(cursor):
    curtime = int(time.time())

    rows = []
    for md_hash,md_size in cursor.execute(SQLS_EXPIRED, (curtime,)):
        row = (md_hash, int(md_size))
        rows.append(row)

    return rows

def hashfs_expired_size(rows):
    total = 0
    for row in rows:
        total = total + row[1]
    return total

def hashfs_expire_data(cursor, goal):
    # list all expired records
    rows = hashfs_expired(cursor)
    exp_size = hashfs_expired_size(rows)

    # is it possible to meet the goal?  if not, exit now.
    if goal > exp_size:
        return

    # build list of data to expire
    exp_total = 0
    exp_rows = []
    for row in rows:
        exp_total = exp_total + row[1]
        exp_rows.append(row)

        if exp_toal >= goal:
            break

    # pass 1: remove metadata

    # dynamically build SQL statement listing all hashes to be removed
    sqls = SQLS_EXPIRE_LIST
    in_first = True
    for row in exp_rows:

        if not in_first:
            sqls += " OR "

        sqls += "hash='%s'" % (row[0],)

        in_first = False

    # execute large sql stmt
    cursor.execute(sqls)

    # pass 2: remove data from OS filesystem
    for row in exp_rows:
        fn = make_hashfs_fn(row[0])

        try:
            os.remove(fn)
        except OSError:
            app.logger.error("Failed to remove " + fn)

def hashfs_hash_size(cursor, hash):
    row = cursor.execute(SQLS_HASH_SIZE, (hash,)).fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0])


@app.route('/')
def home():
    # export API endpoint metadata
    home_obj = [
        {
            "name": "hashfs/1",           # service 'hashfs', version '1'
            "pricing-type": "per-rpc",    # indicates layout of "pricing"
            "pricing" : [
                {
                    "rpc": "get",
                    "per-req": 1,         # 1 satoshi per request
                    "per-mb": 2,          # 2 satoshi per 1000000 bytes
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

    return (body, 200, {
        'Content-length': len(body),
        'Content-type': 'application/json',
    })


def hashfs_price_get(request):

    # re-parse path, as we are denied access to urls.py tokens
    path = request.path
    sl_pos = path.rfind('/')
    hexstr = path[sl_pos+1:]

    # lookup size of $hash's data (if present)
    connection = HASHFS_DB
    cursor = connection.cursor()
    val_size = hashfs_hash_size(cursor, hexstr)
    if val_size is None:
        app.logger.warning("returning 2 zero price for " + request.path)
        return 0

    # build pricing structure
    mb = int(val_size / 1000000)
    if mb == 0:
        mb = 1

    price = 1                    # 1 sat - base per-request price
    price = price + (mb * 2)     # 2 sat/MB bandwidth price

    app.logger.info("returning price " + str(price) + " for " + request.path)
    return price


@app.route('/hashfs/1/get/<hexstr>')
@payment.required(hashfs_price_get)
def hashfs_get(hexstr):

    # decode hex string param
    hexstr = hexstr.lower()
    try:
        hash = binascii.unhexlify(hexstr)
    except TypeError:
        abort(400)

    if len(hash) != 32:
        abort(400)

    # get sqlite handle
    connection = HASHFS_DB
    cursor = connection.cursor()

    # query for metadata
    md = {}
    row = cursor.execute(SQLS_HASH_QUERY, (hexstr,)).fetchone()
    if row is None:
        abort(404)

    md['size'] = int(row[0])
    md['created'] = int(row[1])
    md['expires'] = int(row[2])
    md['content_type'] = row[3]

    # set up FileWrapper to return data
    filename = make_hashfs_fn(hexstr)

    try:
        body = open(filename, 'rb').read()
    except:
        app.logger.error("failed read " + filename)
        abort(500)

    if len(body) != md['size']:
        abort(500)

    dt = datetime.fromtimestamp(md['created'])
    last_mod = httpdate(dt)

    return (body, 200, {
        'Content-Length': md['size'],
        'Content-Type': md['content_type'],
        'ETag': hexstr,
        'Last-Modified': last_mod,
    })


@app.route('/hashfs/1/put/<hexstr>', methods=['PUT'])
@payment.required(1)
def hashfs_put(hexstr):

    # decode hex string param
    hexstr = hexstr.lower()
    try:
        hash = binascii.unhexlify(hexstr)
    except TypeError:
        abort(400)

    if len(hash) != 32:
        abort(400)

    # get sqlite handle
    connection = HASHFS_DB
    cursor = connection.cursor()

    # get content-length
    clen_str = request.headers.get('content-length')
    if clen_str is None:
        abort(400)
    clen = int(request.headers.get('content-length'))
    if clen < 1 or clen > (100 * 1000 * 1000):
        abort(400)

    # do we have room for this new data?
    free_space = hashfs_free_space(cursor)
    if free_space < clen:

        # attempt to remove old, expired data (if any)
        hashfs_expire_data(cursor, clen)

        # do we have room for this new data, pass #2
        free_space = hashfs_free_space(cursor)

        # TODO: is there a better HTTP status?
        if free_space < clen:
            abort(500)

    # get content-type
    ctype = request.headers.get('content-type')
    if blank_re.match(ctype):
        ctype = 'application/octet-stream'

    # note public key hash, if provided
    pkh = request.headers.get('x-hashfs-pkh')
    if not pkh is None:
        if len(pkh) < 32 or len(pkh) > 35:
            abort(400)

        try:
            base58.b58decode_check(pkh)
        except:
            abort(400)

    # check file existence; if it exists, no need to proceed further
    # create dir1/dir2 hierarchy if need be
    filename = make_hashfs_fn(hexstr, True)
    if filename is None:
        abort(500)
    if os.path.isfile(filename):
        abort(400)

    # get data in memory, up to 100M (limit set in nginx config)
    body = request.data
    body_len = len(body)

    # verify content-length matches provided
    if clen != body_len:
        abort(400)

    # hash data
    h = hashlib.new('sha256')
    h.update(body)

    # verify hash matches provided
    if h.hexdigest() != hexstr:
        abort(400)

    # write to filesystem
    try:
        outf = open(filename, 'wb')
        outf.write(body)
        outf.close()
    except OSError:
        abort(500)
    body = None

    # Create, expiration times
    tm_creat = int(time.time())
    tm_expire = tm_creat + (24 * 60 * 60)

    # Add hash metadata to db
    # TODO: test for errors, unlink file if so
    cursor.execute(SQLS_HASH_INSERT, (hexstr, body_len, tm_creat, tm_expire, ctype, pkh))

    return ("true\n", 200, {
        'Content-length': body_len,
        'Content-type': 'application/json',
    })



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)

