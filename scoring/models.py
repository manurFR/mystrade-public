from django.db import models
from game.models import Game
from mystrade import settings
from ruleset.models import RuleCard, Commodity

class ScoreFromRule(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(settings.AUTH_USER_MODEL)
    rulecard = models.ForeignKey(RuleCard)

    detail = models.CharField(max_length = 255)
    score = models.IntegerField(null = True)

class ScoreFromCommodity(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(settings.AUTH_USER_MODEL)
    commodity = models.ForeignKey(Commodity)

    nb_submitted_cards = models.PositiveSmallIntegerField()
    nb_scored_cards = models.PositiveSmallIntegerField()
    actual_value = models.IntegerField()
    score = models.IntegerField()