from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from scoring.models import RuleCard
from scoring.forms import RuleCardsForm

@login_required
def choose_rulecards(request):
    list_rulecards = RuleCard.objects.filter(ruleset = 1)
    #if request.method == 'POST':
    #    form = RuleCardsForm(request.POST)
    #    if (form.is_valid()):
    #        resp = ""
    #        for val in form.cleaned_data.get('rulecard'):
    #            resp += val + "<br/>\n"
    #        return HttpResponse(resp)
    return render(request, 'scoring/choose_rulecards.html', {'list_rulecards': list_rulecards})
