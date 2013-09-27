import numpy

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from game.models import Game
from models import StatsScore

@login_required
@never_cache
def stats(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    x = []
    y = {}
    last_date = None
    for stats in StatsScore.objects.filter(game = game).order_by('date_score', 'player'):
        if stats.date_score <> last_date:
            last_date = stats.date_score
            x.append(stats.date_score)
        if stats.player.name not in y:
            y[stats.player.name] = []
        y[stats.player.name].append(stats.score)

    colormap = plt.cm.gist_ncar
    plt.gca().set_color_cycle([colormap(i) for i in numpy.linspace(0, 0.9, len(y))])

    plt.title('Evolution of scores from game #{0}'.format(game_id))
    plt.xlabel('Time')
    plt.ylabel('Scores')

    players = []
    for player_name, stats in y.iteritems():
        plt.plot(x, stats)
        players.append(player_name)
    legend = plt.legend(players, loc='best', fancybox=True)
    legend.get_frame().set_alpha(0.5)

    figure = plt.figure(1)
    figure.patch.set_facecolor('#FFB600')
    figure.autofmt_xdate()

    plt.subplots_adjust(bottom=0.13)

    canvas = FigureCanvasAgg(figure)

    response = HttpResponse(content_type='image/png')
    canvas.print_png(response)
    return response