from django import forms
from django.contrib.auth import get_user_model

class MystradeUserForm(forms.ModelForm):
    # used only for sign up forms
    mystery = forms.CharField(label = "Type the name of this game", help_text = "Case-insensitive and required. We need to verify that you are a human being.",
                              required = False)

    def __init__(self, expected_mystery = None, *args, **kwargs):
        self.expected_mystery = expected_mystery
        super(MystradeUserForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        # we need required and unique email addresses, but since it comes from AbstractUser, one can't change the field definition. It's enforced here.
        if not self.cleaned_data['email']:
            raise forms.ValidationError("The email address is required.")

        queryset_email = get_user_model().objects.filter(email = self.cleaned_data['email'])
        if self.instance.id: # when we're editing an existing user, let's exclude the old email from our duplicate search
            queryset_email = queryset_email.exclude(id = self.instance.id)
        if queryset_email.exists():
            raise forms.ValidationError("User with this email address already exists.")

        return self.cleaned_data['email']

    def clean_mystery(self):
        if self.expected_mystery: # used only for sign up forms
            if self.cleaned_data['mystery'].replace('.', '').lower() != self.expected_mystery.lower():
                raise forms.ValidationError("Wrong answer.")
        return self.cleaned_data['mystery']

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'send_notifications', 'timezone', 'bio', 'contact', 'palette']
