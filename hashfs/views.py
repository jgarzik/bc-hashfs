import json
import binascii
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.servers.basehttp import FileWrapper
from rest_framework.decorators import api_view
from two1.lib.bitserv.django import payment

@api_view(['GET'])
def home(request):
    # export API endpoint metadata
    home_obj = [
        {
            "name": "hashfs/1",
            "pricing-type": "per-rpc",
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
                    "per-kb": 10,         # 10 satoshis per 1000 bytes
                },
            ]
        }
    ]
    body = json.dumps(home_obj)
    return HttpResponse(body, content_type='application/json')


def make_hashfs_fn(hexstr):
    dir1 = hexstr[:3]
    dir2 = hexstr[3:6]
    fn = settings.HASHFS_ROOT_DIR + dir1 + "/" + dir2 + "/" + hexstr
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
    for md_size,md_created,md_expires in cursor.execute("SELECT val_size,strftime('%s',time_create),strftime('%s',time_expire) FROM metadata WHERE hash = ?", (hash,)):
        md['size'] = int(md_size)
        md['created'] = int(md_created)
        md['expires'] = int(md_expires)

    if len(md.keys()) != 3:
        return HttpResponseNotFound("hash metadata not found")

    # set up FileWrapper to return data
    filename = make_hashfs_fn(hexstr)
    wrapper = FileWrapper(file(filename))

    response = HttpResponse(wrapper, content_type='application/octet-stream')
    response['Content-Length'] = md['size']
    return response


@api_view(['GET'])
@payment.required(1)
def hashfs_put(request):
    body="Put data..."
    return HttpResponse(body, content_type='text/plain')

