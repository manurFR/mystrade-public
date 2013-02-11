from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^$',                           'welcome',      name = 'welcome'),
    url(r'^create/$',                    'create_game',  name = 'create_game'),
    url(r'^rules/$',                     'select_rules', name = 'select_rules'),
    url(r'^(\d+)/hand/$',                'hand',         name = 'hand'),
    url(r'^(\d+)/trades/$',              'trades',       name = 'trades'),
    url(r'^(\d+)/trades/create/$',       'create_trade', name = 'create_trade'),
    url(r'^(\d+)/trades/(\d+)/$',        'show_trade',   name = 'show_trade'),
    url(r'^(\d+)/trades/(\d+)/cancel/$', 'cancel_trade', name = 'cancel_trade'),
    url(r'^(\d+)/trades/(\d+)/reply/$',  'reply_trade',  name = 'reply_trade'),
)

