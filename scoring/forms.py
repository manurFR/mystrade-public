from django import forms
from scoring.models import RuleCard

class RuleCardFormDisplay(forms.ModelForm):
    cardId = forms.CharField(widget = forms.HiddenInput())
    selectedRule = forms.BooleanField(required = False)

    class Meta:
        model = RuleCard
        fields = ('public_name', 'description')

class RuleCardFormParse(forms.Form):
    cardId = forms.CharField(max_length = 20, widget = forms.HiddenInput())
    selectedRule = forms.BooleanField(required = False)