from django import forms
from django.contrib.auth.models import User
from userprofile.models import UserProfile

class UserForm(forms.ModelForm):
    new_password1 = forms.CharField(label="New password", required = False,
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="New password confirmation", required = False,
                                    widget=forms.PasswordInput)
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
        elif (not password1 and password2) or (password1 and not password2):
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'contact']