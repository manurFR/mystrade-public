from django.contrib.auth.models import User
from django.db import models
from game.models import Game
from ruleset.models import RuleCard, Commodity

class ScoreFromRule(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(User)
    rulecard = models.ForeignKey(RuleCard)

    detail = models.CharField(max_length = 255)
    score = models.PositiveIntegerField(null = True)

class ScoreFromCommodity(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(User)
    commodity = models.ForeignKey(Commodity)

    nb_scored_cards = models.PositiveSmallIntegerField()
    actual_value = models.IntegerField()
    score = models.PositiveIntegerField()