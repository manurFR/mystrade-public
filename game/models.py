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

class Trade(models.Model):
    """
                                             (I)
                       ------------------------> CANCELLED (final)
                      /                         (R) ^
            (I)      /                     (R)     /           (I)
    * --------> INITIATED -----------+-------> REPLIED -----+----> ACCEPTED (final)
                                     `                      |
                                      `              (R)    v (I)
                                       `---------------> DECLINED (final)

     (I) status reached by action of the Initiator   (R) status reached by action of the Responder
    """
    STATUS_CHOICES = [(status, status) for status in ['INITIATED', 'CANCELLED', 'REPLIED', 'ACCEPTED', 'DECLINED']]

    game = models.ForeignKey(Game)

    initiator = models.ForeignKey(User, related_name="initiator_trades_set")
    responder = models.ForeignKey(User, related_name="responder_trades_set")

    initiator_offer = models.OneToOneField('Offer', related_name = 'trade_initiated')
    responder_offer = models.OneToOneField('Offer', related_name = 'trade_responded', null = True)

    status = models.CharField(max_length = 15, choices = STATUS_CHOICES, default = "INITIATED") # see above
    finalizer = models.ForeignKey(User, null = True,
        verbose_name = "Player that caused the trade to reach the current final status, null if not in a final status")

    creation_date = models.DateTimeField(default = now)
    closing_date = models.DateTimeField(null = True)

    @property
    def summary(self):
        return self.initiator_offer.summary

class Offer(models.Model):
    rules = models.ManyToManyField(RuleInHand)
    commodities = models.ManyToManyField(CommodityInHand, through='TradedCommodities')

    comment = models.TextField(blank = True, null = True)
    free_information = models.TextField("Free information that won't be revealed until both players accept the trade", blank = True, null = True)

    @property
    def summary(self):
        content = []
        nb_rules = len(self.rules.all())
        nb_traded_commodities = sum([t.nb_traded_cards for t in self.tradedcommodities_set.all()])
        if nb_rules > 0:
            content.append("{} rule card{}".format(nb_rules, "s" if nb_rules > 1 else ""))
        if nb_traded_commodities > 0:
            content.append("{} commodit{}".format(nb_traded_commodities, "ies" if nb_traded_commodities > 1 else "y"))
        if self.free_information:
            content.append("some information")

        if not content:
            return
        elif len(content) == 1:
            return content[0]
        else:
            return ", ".join(content[:-1]) + " and " + content[-1]

class TradedCommodities(models.Model):
    offer = models.ForeignKey(Offer)
    commodity = models.ForeignKey(CommodityInHand)

    nb_traded_cards = models.PositiveSmallIntegerField(default = 0)