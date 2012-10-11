from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView

urlpatterns = patterns('scoring.views',
    url(r'^$', 'choose_rulecards', name = 'scoring'),
)
