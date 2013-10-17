from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView
from game import views as game_views

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$',              game_views.game_list, name = 'nopath'),
    url(r'^login$',         'django.contrib.auth.views.login', {'template_name': 'profile/login.html'}, name='login'),
    url(r'^logout$',        'django.contrib.auth.views.logout_then_login', name='logout'),
    url(r'^rules/(\w+)/$',  game_views.rules, name='rules_lang'),
    url(r'^rules/$',        game_views.rules, {'lang': 'en'}, name='rules'),
    url(r'^profile/',       include('profile.urls')),
    url(r'^game/',          include('game.urls')),
    url(r'^trade/',         include('trade.urls')),
    url(r'^utils/',         include('utils.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^caramba/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^caramba/', include(admin.site.urls)),
)
