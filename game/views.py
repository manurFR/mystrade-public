from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from game.forms import CreateGameForm, validate_number_of_players, \
    validate_dates
from game.models import Game
from scoring.forms import RuleCardFormParse, RuleCardFormDisplay
from scoring.models import RuleCard

@login_required
def welcome(request):
    return render(request, 'game/welcome.html')

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            request.session['ruleset'] = form.cleaned_data['ruleset']
            request.session['start_date'] = form.cleaned_data['start_date']
            request.session['end_date'] = form.cleaned_data['end_date']
            request.session['players'] = list(form.cleaned_data['players'].all()) # convert from Queryset to list
            request.session['profiles'] = [user.get_profile() for user in request.session['players']]
            return HttpResponseRedirect(reverse('select_rules'))
    else:
        form = CreateGameForm(request.user)
    return render(request, 'game/create.html', {'form': form})

@permission_required('game.add_game')
def select_rules(request):
    if 'ruleset' not in request.session or 'start_date' not in request.session \
        or 'end_date' not in request.session or 'players' not in request.session:
        return HttpResponseRedirect(reverse('create_game'))

    ruleset = request.session['ruleset']
    start_date = request.session['start_date']
    end_date = request.session['end_date']
    players = request.session['players']

    try:
        validate_dates(start_date, end_date)
        validate_number_of_players(players, ruleset)
    except ValidationError:
        return HttpResponseRedirect(reverse('create_game'))

    rulecards_queryset = RuleCard.objects.filter(ruleset = ruleset)

    error = None
    if request.method == 'POST':
        RuleCardsFormSet = formset_factory(RuleCardFormParse)
        formset = RuleCardsFormSet(request.POST)
        if formset.is_valid():
            selected_rules = []
            for card in rulecards_queryset:
                if card.mandatory:
                    selected_rules.append(card)
                    continue
                for form in formset:
                    if int(form.cleaned_data['card_id']) == card.id and form.cleaned_data['selected_rule']:
                        selected_rules.append(card)
                        break
            if len(selected_rules) > len(players):
                error = "Please select at most {} rule cards (including the mandatory ones)".format(len(players))
                RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
                formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                                       'public_name':   card.public_name,
                                                       'description':   card.description,
                                                       'mandatory':     bool(card.mandatory),
                                                       'selected_rule': bool(card in selected_rules)}
                                                            for card in rulecards_queryset])
                return render(request, 'game/rules.html', {'formset': formset, 'session': request.session, 'error': error})
            else:
                game = Game.objects.create(ruleset    = ruleset,
                                           master     = request.user,
                                           start_date = start_date,
                                           end_date   = end_date)
                for user in players: game.players.add(user)
                for rule in selected_rules: game.rules.add(rule)
                del request.session['ruleset']
                del request.session['start_date']
                del request.session['end_date']
                del request.session['players']
                del request.session['profiles']
                return HttpResponseRedirect(reverse('welcome'))
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                               'public_name':   card.public_name,
                                               'description':   card.description,
                                               'mandatory':     bool(card.mandatory)}
                                                       for card in rulecards_queryset])
        return render(request, 'game/rules.html', {'formset': formset, 'session': request.session})