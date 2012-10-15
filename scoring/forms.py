from django import forms
from django.forms.formsets import BaseFormSet

class RuleCardsForm(forms.Form):
    public_name = forms.CharField(max_length = 50)
    description = forms.CharField(max_length = 1000)
    selectedRule = forms.BooleanField()
