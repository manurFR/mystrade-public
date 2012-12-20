from django.conf.global_settings import SHORT_DATETIME_FORMAT
from django.contrib.auth.models import User
from django.db import models
from django.utils import dateformat
from django.utils.timezone import now
from scoring.models import Ruleset, RuleCard, Commodity

class Game(models.Model):
    ruleset = models.ForeignKey(Ruleset)
    master = models.ForeignKey(User, related_name = 'mastering_games_set')

    rules = models.ManyToManyField(RuleCard)
    players = models.ManyToManyField(User, related_name = 'playing_games_set')

    # it's important to use django.utils.timezone.now() which is an aware date
    creation_date = models.DateTimeField(default = now())
    start_date = models.DateTimeField(default = now())
    end_date = models.DateTimeField(null = True)

    def __unicode__(self):
        return "{} ({} players, {} - {})".format(self.id, len(self.players.all()),
                                                 dateformat.format(self.start_date, SHORT_DATETIME_FORMAT),
                                                 dateformat.format(self.end_date, SHORT_DATETIME_FORMAT))

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