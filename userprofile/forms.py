from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User

class MysTradeUserChangeForm(SetPasswordForm):
    first_name = forms.CharField(max_length = User._meta.get_field('first_name').max_length)
    