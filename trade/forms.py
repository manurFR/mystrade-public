from django import forms
from django.contrib.auth import get_user_model
from django.forms.formsets import BaseFormSet
from game.models import RuleInHand, CommodityInHand

class TradeForm(forms.Form):
    responder = forms.ModelChoiceField(queryset = get_user_model().objects.none(), empty_label = u'- Choose a player -',
                                       error_messages = {'invalid_choice': "This player doesn't participate to this game or has already submitted his hand to the game master"})

    def __init__(self, me, game, *args, **kwargs):
        super(TradeForm, self).__init__(*args, **kwargs)
        self.fields['responder'].queryset = get_user_model().objects.filter(gameplayer__game = game,
                                            gameplayer__submit_date__isnull = True).exclude(id = me.id).order_by_full_name()

class DeclineReasonForm(forms.Form):
    decline_reason = forms.CharField(required = False, widget = forms.Textarea(attrs={'cols': '145', 'rows': '3'}))

class OfferForm(forms.Form):
    free_information = forms.CharField(required = False, widget = forms.Textarea(attrs={'cols': '145', 'rows': '3'}))
    comment = forms.CharField(required = False, widget = forms.Textarea(attrs={'cols': '145', 'rows': '3'}))

    def __init__(self, *args, **kwargs):
        commodities = kwargs.pop('commodities')
        rulecards = kwargs.pop('rulecards')
        super(OfferForm, self).__init__(*args, **kwargs)

        for cih in commodities:
            self.fields['commodity_{0}'.format(cih.commodity_id)] = forms.IntegerField(widget = forms.HiddenInput, min_value = 0, max_value = cih.nb_cards)
        for rih in rulecards:
            self.fields['rulecard_{0}'.format(rih.id)] = forms.BooleanField(widget = forms.HiddenInput, required = False)

    def commodities(self):
        for name in self.fields:
            if name.startswith('commodity_'):
                yield(self[name])

    def rulecards(self):
        for name in self.fields:
            if name.startswith('rulecard_'):
                yield(self[name])

    # def clean(self):
    #     cleaned_data = super(OfferForm, self).clean()
    #     # if not self.selected_rulecards() and not self.selected_commodities() and not cleaned_data['free_information']:
    #     #     raise forms.ValidationError("At least one card or one free information should be offered.")
    #     return cleaned_data

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

class TradeCommodityCardFormParse(forms.Form):
    commodity_id = forms.CharField(widget = forms.HiddenInput)
    nb_traded_cards = forms.IntegerField(widget = forms.HiddenInput)

class TradeCommodityCardFormDisplay(TradeCommodityCardFormParse):
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