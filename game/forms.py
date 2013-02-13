from django import forms
from django.contrib.auth.models import User
from django.forms.formsets import BaseFormSet
from game.models import Game, RuleInHand, CommodityInHand
from scoring.models import Ruleset, RuleCard
from utils.utils import roundTimeToMinute

#############################################################################
##                              Games                                      ##
#############################################################################

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
            "Please select at least {} players (as many as there are mandatory rule cards in this ruleset).".format(nb_mandatory_cards))

#############################################################################
##                              Trades                                     ##
#############################################################################

class TradeForm(forms.Form):
    responder = forms.ModelChoiceField(queryset = User.objects.none(), empty_label = u'- Choose a player -')

    def __init__(self, me, game, *args, **kwargs):
        super(TradeForm, self).__init__(*args, **kwargs)
        self.fields['responder'].queryset = Game.objects.get(id = game.id).players.exclude(id = me.id).order_by('id')

class OfferForm(forms.Form):
    free_information = forms.CharField(required = False, widget = forms.Textarea(attrs={'cols': '145', 'rows': '3'}))
    comment = forms.CharField(required = False, widget = forms.Textarea(attrs={'cols': '145', 'rows': '3'}))

    nb_selected_rules = 0
    nb_selected_commodities = 0

    def __init__(self, *args, **kwargs):
        if kwargs.has_key('nb_selected_rules'):
            self.nb_selected_rules = kwargs.pop('nb_selected_rules')
        if kwargs.has_key('nb_selected_commodities'):
            self.nb_selected_commodities = kwargs.pop('nb_selected_commodities')
        super(OfferForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(OfferForm, self).clean()
        if self.nb_selected_rules == 0 and self.nb_selected_commodities == 0:
            raise forms.ValidationError("At least one card should be offered.")
        return cleaned_data

class RuleCardFormParse(forms.Form):
    card_id = forms.IntegerField(widget = forms.HiddenInput)
    selected_rule = forms.BooleanField(required = False, label = "Offer")

class RuleCardFormDisplay(RuleCardFormParse):
    public_name = forms.CharField()
    description = forms.CharField()
    mandatory = forms.BooleanField()
    reserved = forms.BooleanField()

class BaseRuleCardsFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if form.cleaned_data['selected_rule']:
                if RuleInHand.objects.get(id=form.cleaned_data['card_id']).is_in_a_pending_trade():
                    raise forms.ValidationError("A rule card in a pending trade can not be offered in another trade.")

class CommodityCardFormParse(forms.Form):
    commodity_id = forms.CharField(widget = forms.HiddenInput)
    nb_traded_cards = forms.IntegerField(widget = forms.HiddenInput)

class CommodityCardFormDisplay(CommodityCardFormParse):
    name = forms.CharField()
    nb_cards = forms.IntegerField()
    nb_tradable_cards = forms.IntegerField()
    color = forms.CharField()

class BaseCommodityCardFormSet(BaseFormSet):
    def set_game(self, game):
        self.game = game

    def set_player(self, player):
        self.player = player

    def clean(self):
        if any(self.errors):
            return
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            try:
                commodity_in_hand = CommodityInHand.objects.get(game = self.game, player = self.player, commodity__id = form.cleaned_data['commodity_id'])
            except CommodityInHand.DoesNotExist: # shouldn't happen in real life, but it simplifies testing greatly
                continue
            if form.cleaned_data['nb_traded_cards'] > commodity_in_hand.nb_tradable_cards():
                raise forms.ValidationError("A commodity card in a pending trade can not be offered in another trade.")