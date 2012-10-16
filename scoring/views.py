from django.contrib.auth.decorators import login_required
from django.forms.formsets import formset_factory
from django.http import HttpResponse
from django.shortcuts import render
from scoring.forms import RuleCardFormDisplay, RuleCardFormParse
from scoring.models import RuleCard

@login_required
def choose_rulecards(request):
    if request.method == 'POST':
        RuleCardFormSet = formset_factory(RuleCardFormParse)
        formset = RuleCardFormSet(request.POST)
        if formset.is_valid():
            # TODO: validate cardIds are from the expected ruleset ?
            strg = ''
            for form in formset:
                strg += form.cleaned_data['cardId'] + ' : '
                strg += repr(form.cleaned_data['selectedRule']) + '  | '
            return HttpResponse(strg)
    else:
        # TODO : is the ModelForm needed, if we can declare the fields without a max_length ?
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        formset = RuleCardsFormSet(initial = [{'cardId':       card.id,
                                               'public_name':  card.public_name,
                                               'description':  card.description,
                                               'selectedRule': bool(card.mandatory)}
                                              for card in RuleCard.objects.filter(ruleset=1)])
    return render(request, 'scoring/choose_rulecards.html', {'formset': formset})
