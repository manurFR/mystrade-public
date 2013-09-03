from django import forms
from django.contrib.auth import get_user_model

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

    def clean(self):
        cleaned_data = super(OfferForm, self).clean()
        nb_selected_commodities = 0
        nb_selected_rulecards = 0
        for name in self.cleaned_data.keys():
            if name.startswith('commodity_'):
                nb_selected_commodities += self.cleaned_data[name]
            elif name.startswith('rulecard_') and self.cleaned_data[name]:
                nb_selected_rulecards += 1
        if nb_selected_commodities == 0 and nb_selected_rulecards == 0 and not cleaned_data['free_information']:
            raise forms.ValidationError("At least one card or one free information should be offered.")
        return cleaned_data

class RuleCardFormParse(forms.Form):
    card_id = forms.IntegerField(widget = forms.HiddenInput)
    selected_rule = forms.BooleanField(required = False, label = "Offer")

class RuleCardFormDisplay(RuleCardFormParse):
    public_name = forms.CharField()
    description = forms.CharField()
    mandatory = forms.BooleanField()
    reserved = forms.BooleanField()
