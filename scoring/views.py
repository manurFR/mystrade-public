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
        #CommoditiesFormSet = formset_factory(CommoditiesFormParse)
        #commodities_formset = CommoditiesFormSet(request.POST, prefix = 'commodities')
        if rulecards_formset.is_valid(): # and commodities_formset.is_valid():
            selected_cards = []
            for card in rulecards_queryset:
                if card.mandatory:
                    selected_cards.append(card)
                    continue
                for form in rulecards_formset:
                    if int(form.cleaned_data['card_id']) == card.id and form.cleaned_data['selected_rule']:
                        selected_cards.append(card)
                        break
            commodities = {}
            #for commodity in commodities_queryset:
                #for form in commodities_formset:
                    #if int(form.cleaned_data['commodity_id']) == commodity.id:
                        #commodities[commodity] = form.cleaned_data['nb_cards']
                        #if commodities[commodity] is None:
                        #    commodities[commodity] = 0
                        #break
            strg = ''
            for card in selected_cards:
                strg += str(card.id) + ' : '
                strg += card.description + '<br/>\n'
            for commodity, nb in commodities.iteritems():
                strg += commodity.name + ' : ' + str(nb) + '<br/>\n'
            return HttpResponse(strg)
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
    return render(request, 'scoring/choose_rulecards.html', {'rulecards_formset': rulecards_formset, 'hands_formset': hands_formset})
