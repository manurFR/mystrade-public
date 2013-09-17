from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^$',                           'welcome',             name = 'welcome'),
    url(r'^(\d+)/$',                     'game_board',          name = 'game'),
    url(r'^(\d+)/trade/(\d+)/$',         'game_board',          name = 'game_with_trade'),
    url(r'^(\d+)/events/$',              'events',              name = 'events'),
    url(r'^(\d+)/postmessage/$',         'post_message',        name = 'post_message'),
    url(r'^(\d+)/deletemessage/$',       'delete_message',      name = 'delete_message'),
    url(r'^(\d+)/submithand/$',          'submit_hand',         name = 'submit_hand'),
    url(r'^(\d+)/close/$',               'close_game',          name = 'close_game'),
    url(r'^create/$',                    'create_game',         name = 'create_game'),
    url(r'^selectrules/$',               'select_rules',        name = 'select_rules'),
)

