from django.http import HttpResponse
from rest_framework.decorators import api_view
from two1.lib.bitserv.django import payment

@api_view(['GET'])
@payment.required(1)
def home(request):
    body='Hello, World!'
    return HttpResponse(body, content_type='text/plain')

