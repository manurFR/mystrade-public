from django.conf.urls import patterns, url

urlpatterns = patterns('utils.views',
    url(r'^stats/(\d+)/$', 'stats', name='stats'),
)
