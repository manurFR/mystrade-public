from django import forms
from scoring.models import Ruleset
from utils.utils import roundTimeToMinute

class CreateGameForm(forms.Form):
    ruleset = forms.ModelChoiceField(queryset = Ruleset.objects.all(), empty_label = None)

    start_date = forms.DateTimeField(initial = roundTimeToMinute(roundToMinutes = 15).strftime("%m/%d/%Y %H:%M"))
    end_date = forms.DateTimeField()