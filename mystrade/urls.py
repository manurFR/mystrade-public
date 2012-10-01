from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.views.generic.base import TemplateView

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'django.contrib.auth.views.login', {'template_name': 'userprofile/login.html'}, 
        name='login'),
    url(r'^welcome/$', login_required(TemplateView.as_view(template_name = 'userprofile/welcome.html')), 
        name = 'welcome'),
    url(r'^logout$', 'django.contrib.auth.views.logout',
        name='logout'),
    url(r'^profile/', include('userprofile.urls')),
    
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^caramba/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^caramba/', include(admin.site.urls)),
)
