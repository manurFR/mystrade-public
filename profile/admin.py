from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from profile.forms import MystradeUserForm
from profile.models import MystradeUser
from django.utils.translation import ugettext_lazy as _

class MystradeUserAdminForm(forms.ModelForm):
    class Meta:
        model = MystradeUser

class MystradeUserAdmin(UserAdmin):
    form = MystradeUserAdminForm
    add_form = MystradeUserForm

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        ('Mystrade', {'fields': ('send_notifications', 'bio', 'contact')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

admin.site.register(MystradeUser, MystradeUserAdmin)

