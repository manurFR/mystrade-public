from django.conf.urls import patterns, url

urlpatterns = patterns('trade.views',
    url(r'^(\d+)/list/$',          'trade_list',    name = 'trade_list'),
    url(r'^(\d+)/create/$',        'create_trade',  name = 'create_trade'),
    url(r'^(\d+)/(\d+)/$',         'show_trade',    name = 'show_trade'),
    url(r'^(\d+)/(\d+)/cancel/$',  'cancel_trade',  name = 'cancel_trade'),
    url(r'^(\d+)/(\d+)/reply/$',   'reply_trade',   name = 'reply_trade'),
    url(r'^(\d+)/(\d+)/accept/$',  'accept_trade',  name = 'accept_trade'),
    url(r'^(\d+)/(\d+)/decline/$', 'decline_trade', name = 'decline_trade'),
)