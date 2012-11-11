from django import forms
from django.contrib.auth.models import User
from scoring.models import Ruleset
from utils.utils import roundTimeToMinute

class CreateGameForm(forms.Form):
    ruleset = forms.ModelChoiceField(queryset = Ruleset.objects.all(), empty_label = None)

    start_date = forms.DateTimeField(initial = roundTimeToMinute(roundToMinutes = 15).strftime("%m/%d/%Y %H:%M"))
    end_date = forms.DateTimeField()

    players = forms.ModelMultipleChoiceField(queryset = User.objects.none())

    def __init__(self, game_master, *args, **kwargs):
        super(CreateGameForm, self).__init__(*args, **kwargs)
        self.fields['players'].queryset = User.objects.exclude(id = game_master.id)