from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from game.forms import CreateGameForm, validate_number_of_players

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            request.session['ruleset'] = form.cleaned_data['ruleset']
            request.session['start_date'] = form.cleaned_data['start_date']
            request.session['end_date'] = form.cleaned_data['end_date']
            request.session['players'] = list(form.cleaned_data['players'].all()) # convert from Queryset to list
            #game = Game.objects.create(ruleset    = form.cleaned_data['ruleset'],
            #                           master     = request.user,
            #                           start_date = form.cleaned_data['start_date'],
            #                           end_date   = form.cleaned_data['end_date'])
            #for user in form.cleaned_data['players']:
            #    game.players.add(user)
            return HttpResponseRedirect(reverse('game.views.select_rules'))
    else:
        form = CreateGameForm(request.user)
    return render(request, 'game/create.html', {'form': form})

@permission_required('game.add_game')
def select_rules(request):
    if 'ruleset' not in request.session or 'start_date' not in request.session \
        or 'end_date' not in request.session or 'players' not in request.session:
        return HttpResponseRedirect(reverse('game.views.create_game'))
    try:
        validate_number_of_players(request.session['players'], request.session['ruleset'])
    except ValidationError:
        return HttpResponseRedirect(reverse('game.views.create'))

    return HttpResponse("Page 2")