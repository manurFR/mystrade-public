from game.views import _fetch_scoresheets
from scoring.card_scoring import tally_scores
from models import StatsScore


def record(game, trade = None):
    if game.is_closed():
        scoresheets = _fetch_scoresheets(game) # from game.views
    else:
        scoresheets = tally_scores(game)

    # save in db
    for scoresheet in scoresheets:
        StatsScore.objects.create(game = game, player = scoresheet.gameplayer.player, trade = trade,
                                  score = scoresheet.total_score,
                                  random = len([sfr for sfr in scoresheet.scores_from_rule
                                                        if getattr(sfr, 'is_random', False)]) > 0)