from django import forms
from django.contrib.auth.models import User
from scoring.models import Ruleset, RuleCard
from utils.utils import roundTimeToMinute

class CreateGameForm(forms.Form):
    ruleset = forms.ModelChoiceField(queryset = Ruleset.objects.all(), empty_label = None)

    start_date = forms.DateTimeField(initial = roundTimeToMinute(roundToMinutes = 15).strftime("%m/%d/%Y %H:%M"))
    end_date = forms.DateTimeField()

    players = forms.ModelMultipleChoiceField(queryset = User.objects.none())

    def __init__(self, game_master, *args, **kwargs):
        super(CreateGameForm, self).__init__(*args, **kwargs)
        self.fields['players'].queryset = User.objects.exclude(id = game_master.id)

    def clean(self):
        """ Accept only a minimum of as many players as there are mandatory rule cards. """
        cleaned_data = super(CreateGameForm, self).clean()
        nb_mandatory_cards = RuleCard.objects.filter(ruleset = cleaned_data['ruleset'], mandatory = True).count()
        if 'players' in cleaned_data and len(cleaned_data['players']) < nb_mandatory_cards:
            raise forms.ValidationError("Please select at least {} players (as many as there are mandatory rule cards in this ruleset).".format(nb_mandatory_cards))
        return cleaned_data