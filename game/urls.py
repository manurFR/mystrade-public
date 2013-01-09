from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^$',              'welcome',      name = 'welcome'),
    url(r'^create/$',       'create_game',  name = 'create_game'),
    url(r'^rules/$',        'select_rules', name = 'select_rules'),
    url(r'^hand/(\d+)/$',   'hand',         name = 'hand'),
    url(r'^trades/(\d+)/$', 'trades',       name = 'trades'),
    url(r'^trades/(\d+)/create/$', 'create_trade', name = 'create_trade')
)
