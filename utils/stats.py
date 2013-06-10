from django.utils.timezone import now
from scoring.card_scoring import tally_scores
from models import StatsScore

def record(game, trade = None, scoresheets = None):
    if not scoresheets:
        scoresheets = tally_scores(game)

    # save in db
    date_score = now()
    for scoresheet in scoresheets:
        StatsScore.objects.create(game = game, player = scoresheet.gameplayer.player, trade = trade,
                                  score = scoresheet.total_score, date_score = date_score,
                                  random = len([sfr for sfr in scoresheet.scores_from_rule
                                                        if getattr(sfr, 'is_random', False)]) > 0)