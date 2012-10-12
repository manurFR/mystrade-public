from django.conf.urls import patterns, url

urlpatterns = patterns('scoring.views',
    url(r'^$', 'choose_rulecards', name = 'scoring'),
)
