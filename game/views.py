from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse

@permission_required('game.add_game')
def create_game(request):
    return HttpResponse("Let's create a new game...")