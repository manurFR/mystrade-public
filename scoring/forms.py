from django import forms

class RuleCardsForm(forms.Form):
    rulecard = forms.MultipleChoiceField(widget = forms.CheckboxSelectMultiple())