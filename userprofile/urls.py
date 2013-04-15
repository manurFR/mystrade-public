from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView

urlpatterns = patterns('userprofile.views',
    url(r'^$',       'profile',     name = 'profile'),
    url(r'^(\d+)/$', 'profile',     name = 'otherprofile'),
    url(r'^edit/$',  'editprofile', name = 'editprofile'),
)
