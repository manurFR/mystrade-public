from django.conf.urls import patterns, url

urlpatterns = patterns('profile.views',
    url(r'^$',                  'profile',     name = 'profile'),
    url(r'^(\d+)/$',            'profile',     name = 'otherprofile'),
    url(r'^edit/$',             'editprofile', name = 'editprofile'),
    url(r'^signup/$',           'sign_up',     name = 'signup'),
    url(r'^activation/(\w+)/$', 'activation',  name = 'activation'),
)
