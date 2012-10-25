from django.contrib.auth.decorators import login_required
from django.forms.formsets import formset_factory
from django.http import HttpResponse
from django.shortcuts import render
from scoring.forms import RuleCardFormDisplay, RuleCardFormParse, HandsForm
from scoring.models import RuleCard, Commodity

@login_required
def choose_rulecards(request):
    rulecards_queryset = RuleCard.objects.filter(ruleset = 1)
    commodities_queryset = Commodity.objects.filter(ruleset = 1)
    if request.method == 'POST':
        RuleCardFormSet = formset_factory(RuleCardFormParse)
        rulecards_formset = RuleCardFormSet(request.POST, prefix = 'rulecards')
        HandsFormSet = formset_factory(HandsForm)
        hands_formset = HandsFormSet(request.POST, prefix = 'hands')
        if rulecards_formset.is_valid() and hands_formset.is_valid():
            selected_rules = []
            for card in rulecards_queryset:
                if card.mandatory:
                    selected_rules.append(card)
                    continue
                for form in rulecards_formset:
                    if int(form.cleaned_data['card_id']) == card.id and form.cleaned_data['selected_rule']:
                        selected_rules.append(card)
                        break
            players = []
            for form in hands_formset:
                hand = {}
                for commodity in commodities_queryset:
                    if not form.cleaned_data: # none of the fields are valued
                        hand[commodity] = 0
                    else:
                        hand[commodity] = form.cleaned_data[commodity.name.lower()]
                        if hand[commodity] is None:
                            hand[commodity] = 0
                players.append(hand)
            return render(request, 'scoring/result.html', {'rules': selected_rules, 'players': players})
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        rulecards_formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                               'public_name':   card.public_name,
                                               'description':   card.description,
                                               'mandatory':     bool(card.mandatory)}
                                                for card in rulecards_queryset],
                                             prefix = 'rulecards')
        HandsFormSet = formset_factory(HandsForm, extra = 1)
        hands_formset = HandsFormSet(prefix = 'hands')
    return render(request, 'scoring/choose_rulecards.html', 
                  {'rulecards_formset': rulecards_formset, 'hands_formset': hands_formset})