from django import forms
from django.contrib.auth import get_user_model
from django.utils.timezone import now, localtime
from game.models import Message
from ruleset.models import Ruleset, RuleCard
from utils.utils import roundTimeToMinute

#############################################################################
##                              Games                                      ##
#############################################################################

class CreateGameForm(forms.Form):
    ruleset = forms.ModelChoiceField(queryset = Ruleset.objects.all(), empty_label = None)

    start_date = forms.DateTimeField()
    end_date = forms.DateTimeField()

    players = forms.ModelMultipleChoiceField(queryset = get_user_model().objects.none())

    def __init__(self, game_master, *args, **kwargs):
        super(CreateGameForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].initial = roundTimeToMinute(localtime(now()), roundToMinutes = 15).strftime("%m/%d/%Y %H:%M")
        self.fields['players'].queryset = get_user_model().objects.exclude(id = game_master.id).order_by_full_name()

    def clean(self):
        cleaned_data = super(CreateGameForm, self).clean()
        if 'start_date' in cleaned_data and 'end_date' in cleaned_data:
            validate_dates(cleaned_data['start_date'], cleaned_data['end_date'])
        if 'players' in cleaned_data and 'ruleset' in cleaned_data:
            validate_number_of_players(cleaned_data['players'], cleaned_data['ruleset'])
        return cleaned_data

def validate_dates(start_date, end_date):
    """
    End date must be strictly after start date.
    """
    if end_date <= start_date:
        raise forms.ValidationError("End date must be strictly posterior to start date.")

def validate_number_of_players(list_of_players, chosen_ruleset):
    """
    There must be at least as many players as there are mandatory rule cards.
    Raises a ValidationError ifthat condition is not fulfilled.
    """
    nb_mandatory_cards = RuleCard.objects.filter(ruleset = chosen_ruleset, mandatory = True).count()
    if len(list_of_players) < nb_mandatory_cards:
        raise forms.ValidationError(
            "Please select at least {0} players (as many as there are mandatory rule cards in this ruleset).".format(nb_mandatory_cards))

class GameCommodityCardFormParse(forms.Form):
    commodity_id = forms.CharField(widget = forms.HiddenInput)
    nb_submitted_cards = forms.IntegerField(widget = forms.HiddenInput)

class GameCommodityCardFormDisplay(GameCommodityCardFormParse):
    name = forms.CharField()
    nb_cards = forms.IntegerField()
    color = forms.CharField()

class MessageForm(forms.Form):
    message = forms.CharField(max_length = Message.MAX_LENGTH, widget=forms.Textarea, required = False, label = "Add message")