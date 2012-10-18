from django import forms

class RuleCardFormParse(forms.Form):
    card_id = forms.CharField(widget = forms.HiddenInput())
    selected_rule = forms.BooleanField(required = False, label = "Keep")

class RuleCardFormDisplay(RuleCardFormParse):
    public_name = forms.CharField()
    description = forms.CharField()
    mandatory = forms.BooleanField()
