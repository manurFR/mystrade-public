from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from game.forms import CreateGameForm

@permission_required('game.add_game')
def create_game(request):
    game_form = CreateGameForm()
    return render(request, 'game/create.html', {'form': game_form})