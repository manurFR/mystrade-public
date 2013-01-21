from django import forms
from django.contrib.auth.models import User
from game.models import Game
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
        cleaned_data = super(CreateGameForm, self).clean()
        if 'start_date' in cleaned_data and 'end_date' in cleaned_data:
            validate_dates(cleaned_data['start_date'], cleaned_data['end_date'])
        if 'players' in cleaned_data and 'ruleset' in cleaned_data:
            validate_number_of_players(cleaned_data['players'], cleaned_data['ruleset'])
        return cleaned_data

class CreateTradeForm(forms.Form):
    responder = forms.ModelChoiceField(queryset = User.objects.none(), empty_label=u'- Choose a player -')
    comment = forms.CharField(widget=forms.Textarea(attrs = {'cols': '145', 'rows': '3'}))

    def __init__(self, me, game, *args, **kwargs):
        super(CreateTradeForm, self).__init__(*args, **kwargs)
        self.fields['responder'].queryset = Game.objects.get(id = game.id).players.exclude(id = me.id).order_by('id')

def validate_dates(start_date, end_date):
    """
    End date must be strictly after start date.
    """
    if end_date <= start_date:
        raise forms.ValidationError("End date must be strictly posterior to start date.")

def validate_number_of_players(list_of_players, chosen_ruleset):
    """
    There must be at least as many players as there are mandatory rule cards.
    Raises a ValidationError if that condition is not fulfilled.
    """
    nb_mandatory_cards = RuleCard.objects.filter(ruleset = chosen_ruleset, mandatory = True).count()
    if len(list_of_players) < nb_mandatory_cards:
        raise forms.ValidationError("Please select at least {} players (as many as there are mandatory rule cards in this ruleset).".format(nb_mandatory_cards))