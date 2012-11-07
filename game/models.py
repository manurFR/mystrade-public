from django.contrib.auth.models import User
from django.db import models
from scoring.models import Ruleset, RuleCard
import datetime

class Game(models.Model):
    ruleset = models.ForeignKey(Ruleset)
    master = models.ForeignKey(User, related_name = 'mastering_games_set')

    rules = models.ManyToManyField(RuleCard)
    players = models.ManyToManyField(User, related_name = 'playing_games_set')

    creation_date = models.DateTimeField(default = datetime.datetime.now)
    start_date = models.DateTimeField(default = datetime.datetime.now)
    end_date = models.DateTimeField()