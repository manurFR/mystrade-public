from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^$',                           'welcome',       name = 'welcome'),
    url(r'^create/$',                    'create_game',   name = 'create_game'),
    url(r'^rules/$',                     'select_rules',  name = 'select_rules'),
    url(r'^(\d+)/hand/$',                'hand',          name = 'hand'),
    url(r'^(\d+)/hand/submit/$',         'submit_hand',   name = 'submit_hand'),
    url(r'^(\d+)/score/$',               'player_score',  name = 'player_score'),
    url(r'^(\d+)/control/$',             'control_board', name = 'control'),
    url(r'^(\d+)/close/$',               'close_game',    name = 'close_game'),
)

