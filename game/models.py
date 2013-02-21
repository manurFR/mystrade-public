from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Sum
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

    def is_in_a_pending_trade(self):
        """ A rule card may be in a trade in the initator offer or the responder offer.
            A pending trade is a trade not in a final status, ie. without a defined finalizer.
        """
        return self.offer_set.filter(Q(trade_initiated__isnull=False, trade_initiated__finalizer__isnull=True) |
                                     Q(trade_responded__isnull=False, trade_responded__finalizer__isnull=True)).count() > 0

class CommodityInHand(models.Model):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(User)
    commodity = models.ForeignKey(Commodity)

    nb_cards = models.PositiveSmallIntegerField(default = 0)

    def __unicode__(self):
        return "{} {} card{} owned by {} in game {}".format(self.nb_cards, self.commodity.name.lower(),
                's' if self.nb_cards > 1 else '', self.player.get_profile().name, self.game.id)

    def nb_tradable_cards(self):
        """ Commodity cards may be in a trade in the initator offer or the responder offer.
            The number of cards not tradable is the sum of the cards offered in other trades currently not finalized.
        """
        return self.nb_cards - (self.tradedcommodities_set.filter(
            Q(offer__trade_initiated__isnull=False, offer__trade_initiated__finalizer__isnull=True) |
            Q(offer__trade_responded__isnull=False, offer__trade_responded__finalizer__isnull=True))
                                .aggregate(Sum('nb_traded_cards'))['nb_traded_cards__sum']
                                or 0) # if there are no records to aggregate