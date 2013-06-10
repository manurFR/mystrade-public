from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure
from game.models import Game
from models import StatsScore


@login_required
def stats(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if not game.has_super_access(request.user):
        raise PermissionDenied

    figure = Figure()
    ax = figure.add_subplot(111)

    x = []
    y = []
    last_date = None
    for stats in StatsScore.objects.filter(game = game).order_by('date_score', 'player'):
        if stats.date_score <> last_date:
            last_date = stats.date_score
            x.append(stats.date_score)
            y.append(stats.score)

    ax.plot_date(x, y, '-')
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    figure.autofmt_xdate()
    canvas = FigureCanvasAgg(figure)

    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response