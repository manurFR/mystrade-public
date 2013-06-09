from django.db import models
from django.utils.timezone import now
from game.models import Game
from mystrade import settings
from trade.models import Trade

class StatsScore(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(settings.AUTH_USER_MODEL)
    trade = models.ForeignKey(Trade, null = True) # after which completed trade this stat was taken, if not null

    dateScore = models.DateTimeField(default = now)

    score = models.IntegerField()

    random = models.BooleanField(default = False)
