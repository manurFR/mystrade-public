from django.conf.urls import patterns, include, url
from django.contrib import admin

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'django.contrib.auth.views.login', {'template_name': 'userprofile/login.html'}),#'mystrade.views.home', name='home'),
    # url(r'^mystrade/', include('mystrade.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^caramba/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^caramba/', include(admin.site.urls)),
)
