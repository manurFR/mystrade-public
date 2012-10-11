from django.shortcuts import render
from scoring.models import RuleCard

def choose_rulecards(request):
    list_rulecards = RuleCard.objects.filter(ruleset = 1)
    return render(request, 'scoring/choose_rulecards.html', {'list_rulecards': list_rulecards})
