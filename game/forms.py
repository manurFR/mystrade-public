from django import forms
from scoring.models import Ruleset

class CreateGameForm(forms.Form):
    ruleset = forms.ModelChoiceField(queryset = Ruleset.objects.all(), empty_label = None)

    start_date = forms.DateField()