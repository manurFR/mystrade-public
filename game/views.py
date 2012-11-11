from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from game.forms import CreateGameForm
from game.models import Game
from django.http import HttpResponse

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            game = Game.objects.create(ruleset    = form.cleaned_data['ruleset'],
                                       master     = request.user,
                                       start_date = form.cleaned_data['start_date'],
                                       end_date   = form.cleaned_data['end_date'])
            for user in form.cleaned_data['players']:
                game.players.add(user)
            return HttpResponse("Game saved.")
    else:
        form = CreateGameForm(request.user)
    return render(request, 'game/create.html', {'form': form})