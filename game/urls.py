from django.conf.urls import patterns, url

urlpatterns = patterns('game.views',
    url(r'^create/$', 'create_game', name = 'create_game'),
    url(r'^rules/$', 'select_rules', name = 'select_rules'),
)
