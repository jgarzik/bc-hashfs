from django.conf.urls import patterns, include, url
from django.contrib import admin
from . import views

urlpatterns = patterns('',

url(r'^$', 'hashfs.views.home', name='home'),
url(r'^payments/', include('two1.lib.bitserv.django.urls')),

)
