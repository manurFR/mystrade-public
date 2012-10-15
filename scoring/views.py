from django.contrib.auth.decorators import login_required
from django.forms.formsets import formset_factory
from django.http import HttpResponse
from django.shortcuts import render
from scoring.forms import RuleCardsForm
from scoring.models import RuleCard

@login_required
def choose_rulecards(request):
    if request.method == 'POST':
        return HttpResponse(request.POST)
    else:
        list_rulecards = RuleCard.objects.filter(ruleset = 1)
  
        RuleCardsFormSet = formset_factory(RuleCardsForm, extra = 0)
        formset = RuleCardsFormSet(initial = [{'public_name': card.public_name,
                                               'description': card.description,
                                               'selectedRule': bool(card.mandatory)} for card in list_rulecards]) 
    return render(request, 'scoring/choose_rulecards.html', {'formset': formset})
