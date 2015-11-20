from django.conf.urls import patterns, include, url
from django.contrib import admin
from . import views

urlpatterns = patterns('',

url(r'^$', 'hashfs.views.home', name='home'),

url(r'^hashfs/1/data$', 'hashfs.views.hashfs_put', name='hashfs_put'),
url(r'^hashfs/1/d/([a-fA-F0-9]+)$', 'hashfs.views.hashfs_get', name='hashfs_get'),

url(r'^payments/', include('two1.lib.bitserv.django.urls')),

)
