from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from scoring.models import Ruleset, RuleCard, Commodity

class Game(models.Model):
    ruleset = models.ForeignKey(Ruleset)
    master = models.ForeignKey(User, related_name = 'mastering_games_set')

    rules = models.ManyToManyField(RuleCard)
    players = models.ManyToManyField(User, related_name = 'playing_games_set')

    # it's important to use django.utils.timezone.now() which is an aware date
    creation_date = models.DateTimeField(default = now)
    start_date = models.DateTimeField(default = now)
    end_date = models.DateTimeField(null = True)

    def __unicode__(self):
        return "{}".format(self.id)

class RuleInHand(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(User)
    rulecard = models.ForeignKey(RuleCard)

    ownership_date = models.DateTimeField("The date when this card was acquired")
    abandon_date = models.DateTimeField("The date when this card was exchanged", null = True)

    def __unicode__(self):
        return "Rule <{}> owned by {} in game {}".format(self.rulecard.ref_name, self.player.get_profile().name, self.game.id)

class CommodityInHand(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(User)
    commodity = models.ForeignKey(Commodity)

    nb_cards = models.PositiveSmallIntegerField(default = 0)

    def __unicode__(self):
        return "{} {} card{} owned by {} in game {}".format(self.nb_cards, self.commodity.name.lower(), 
                's' if self.nb_cards > 1 else '', self.player.get_profile().name, self.game.id)

class Trade(models.Model):
    game = models.ForeignKey(Game)

    initiator = models.ForeignKey(User, related_name="initiator_trades_set")
    responder = models.ForeignKey(User, related_name="responder_trades_set")

    rules = models.ManyToManyField(RuleInHand)
    commodities = models.ManyToManyField(CommodityInHand, through='TradedCommodities')

    comment = models.TextField(blank = True)

    status = models.CharField(max_length = 15, default = "INITIATED") # INITIATED, CANCELLED, ACCEPTED or DECLINED
    creation_date = models.DateTimeField(default = now)
    closing_date = models.DateTimeField(null = True)

class TradedCommodities(models.Model):
    trade = models.ForeignKey(Trade)
    commodity = models.ForeignKey(CommodityInHand)

    nb_traded_cards = models.PositiveSmallIntegerField(default = 0)