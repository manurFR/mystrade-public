from django.contrib.auth.decorators import login_required
from django.forms.formsets import formset_factory
from django.http import HttpResponse
from django.shortcuts import render
from scoring.forms import RuleCardFormDisplay, RuleCardFormParse
from scoring.models import RuleCard

@login_required
def choose_rulecards(request):
    queryset = RuleCard.objects.filter(ruleset=1)
    if request.method == 'POST':
        RuleCardFormSet = formset_factory(RuleCardFormParse)
        formset = RuleCardFormSet(request.POST)
        if formset.is_valid():
            selected_cards = []
            for card in queryset:
                if card.mandatory:
                    selected_cards.append(card)
                    continue
                for form in formset:
                    if int(form.cleaned_data['card_id']) == card.id and form.cleaned_data['selected_rule']:
                        selected_cards.append(card)
                        break
            strg = ''
            for card in selected_cards:
                strg += str(card.id) + ' : '
                strg += card.description + '<br/>\n'
            return HttpResponse(strg)
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                               'public_name':   card.public_name,
                                               'description':   card.description,
                                               'mandatory':     bool(card.mandatory),
                                               'selected_rule': bool(card.mandatory)}
                                                for card in queryset])
    return render(request, 'scoring/choose_rulecards.html', {'formset': formset})
