from django.conf.urls import patterns, include, url
from django.contrib import admin

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$',         'django.contrib.auth.views.login', {'template_name': 'userprofile/login.html'}, name='login'),
    url(r'^welcome/$', 'django.views.generic.simple.redirect_to', {'url': '/game/'}),
    url(r'^logout$',   'django.contrib.auth.views.logout_then_login', name='logout'),
    url(r'^profile/',  include('userprofile.urls')),
    url(r'^scoring/',  include('scoring.urls')),
    url(r'^game/',     include('game.urls')),
    url(r'^trade/',    include('trade.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^caramba/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^caramba/', include(admin.site.urls)),
)
