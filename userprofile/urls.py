from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView

urlpatterns = patterns('userprofile.views',
    url(r'^$', login_required(TemplateView.as_view(template_name = 'userprofile/profile.html')), name = 'profile'),
    url(r'^(\d+)/$', 'editprofile'),
)
