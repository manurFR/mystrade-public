from django.conf.urls import patterns, url
from django.contrib.auth.views import password_reset, password_reset_done, password_reset_confirm, password_reset_complete
from mystrade import settings

urlpatterns = patterns('profile.views',
    url(r'^$',                          'profile',                  name = 'profile'),
    url(r'^(\d+)/$',                    'profile',                  name = 'otherprofile'),
    url(r'^edit/$',                     'editprofile',              name = 'editprofile'),
    url(r'^signup/$',                   'sign_up',                  name = 'signup'),
    url(r'^activation/(\d+)/(.+)/$',    'activation',               name = 'activation'),
    url(r'^password_reset/$',           password_reset, {
                                                        'template_name':         'profile/password_reset.html',
                                                        'subject_template_name': 'notification/password_reset_subject.txt',
                                                        'email_template_name':   'notification/password_reset_body.txt',
                                                        'from_email':            settings.EMAIL_MYSTRADE
                                                        },
                                                                    name = 'password_reset'),
    url(r'^password_reset_done/$',      password_reset_done,        name = 'password_reset_done'),
    url(r'^password_reset_confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                                        password_reset_confirm,     name = 'password_reset_confirm'),
    url(r'^password_reset_complete/$',  password_reset_complete,    name = 'password_reset_complete'),
)
