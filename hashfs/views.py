import json
from django.http import HttpResponse
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

@api_view(['GET'])
@payment.required(1)
def hashfs_get(request, hexstr):
    body="Data requested for hash " + hexstr
    return HttpResponse(body, content_type='text/plain')

@api_view(['GET'])
@payment.required(1)
def hashfs_put(request):
    body="Put data..."
    return HttpResponse(body, content_type='text/plain')

