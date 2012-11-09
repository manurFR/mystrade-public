from django import forms

class RuleCardFormParse(forms.Form):
    card_id = forms.CharField(widget = forms.HiddenInput)
    selected_rule = forms.BooleanField(required = False, label = "Keep")

class RuleCardFormDisplay(RuleCardFormParse):
    public_name = forms.CharField()
    description = forms.CharField()
    mandatory = forms.BooleanField()

class HandsForm(forms.Form):
    yellow = forms.IntegerField(min_value = 0, max_value = 999, required = False)
    blue = forms.IntegerField(min_value = 0, max_value = 999, required = False)
    red = forms.IntegerField(min_value = 0, max_value = 999, required = False)
    orange = forms.IntegerField(min_value = 0, max_value = 999, required = False)
    white = forms.IntegerField(min_value = 0, max_value = 999, required = False)