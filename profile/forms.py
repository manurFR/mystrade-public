from django import forms
from django.contrib.auth import get_user_model

class MystradeUserForm(forms.ModelForm):

    def clean_email(self):
        if not self.cleaned_data['email']:
            raise forms.ValidationError("The email address is required.")
        return self.cleaned_data['email']

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'send_notifications', 'timezone', 'bio', 'contact']
