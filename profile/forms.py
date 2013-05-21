from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class MystradeUserForm(forms.ModelForm):
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
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'send_notifications', 'bio', 'contact']
