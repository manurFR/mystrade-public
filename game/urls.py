from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^$',                           'welcome',        name = 'welcome'),
    url(r'^create/$',                    'create_game',    name = 'create_game'),
    url(r'^selectrules/$',               'select_rules',   name = 'select_rules'),
    url(r'^(\d+)/deletemessage/(\d+)/$', 'delete_message', name = 'delete_message'),
    url(r'^(\d+)/hand/$',                'hand',           name = 'hand'),
    url(r'^(\d+)/hand/submit/$',         'submit_hand',    name = 'submit_hand'),
    url(r'^(\d+)/score/$',               'player_score',   name = 'player_score'),
    url(r'^(\d+)/control/$',             'control_board',  name = 'control'),
    url(r'^(\d+)/close/$',               'close_game',     name = 'close_game'),
    url(r'^(\d+)/$',                     'game_board',     name = 'game_board'), # TODO rename to 'game' after redesign
    url(r'^(\d+)/events/$',              'events',         name = 'events'),
    url(r'^(\d+)/postmessage/$',         'post_message',   name = 'post_message'),
    url(r'^(\d+)/old/$',                 'game',           name = 'game'),
)

