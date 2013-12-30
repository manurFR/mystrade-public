from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import ugettext_lazy as _

from profile.models import MystradeUser

class MystradeUserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ("username",)

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            get_user_model()._default_manager.get(username=username)
        except get_user_model().DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages[u'duplicate_username'])

class MystradeUserAdminForm(forms.ModelForm):
    pass

class MystradeUserAdmin(UserAdmin):
    form = MystradeUserAdminForm
    add_form = MystradeUserCreationForm

    fieldsets = (
        (None,                 {'fields': ('username', 'password')}),
        (_('Personal info'),   {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'),     {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Mystrade',           {'fields': ('send_notifications', 'timezone', 'bio', 'contact', 'palette')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

admin.site.register(MystradeUser, MystradeUserAdmin)

