from django.db import models
from django.utils.timezone import now
from game.models import Game, RuleInHand, CommodityInHand
from mystrade import settings


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

    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="initiator_trades_set")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="responder_trades_set")

    initiator_offer = models.OneToOneField('Offer', related_name = 'trade_initiated')
    responder_offer = models.OneToOneField('Offer', related_name = 'trade_responded', null = True)

    status = models.CharField(max_length = 15, choices = STATUS_CHOICES, default = "INITIATED") # see above

    decline_reason = models.TextField(blank = True, null = True)
    finalizer = models.ForeignKey(settings.AUTH_USER_MODEL, null = True,
        verbose_name = "Player that caused the trade to reach the current final status, null if not in a final status")

    creation_date = models.DateTimeField(default = now)
    closing_date = models.DateTimeField(null = True)

    def abort(self, whodunit, closing_date):
        if whodunit == self.initiator:
            if self.status == 'INITIATED':
                self.status = 'CANCELLED'
            elif self.status == 'REPLIED':
                self.status = 'DECLINED'
        elif whodunit == self.responder:
            if self.status == 'INITIATED':
                self.status = 'DECLINED'
            elif self.status == 'REPLIED':
                self.status = 'CANCELLED'
        else:
            self.status = 'CANCELLED' # when the game is closed by the game master or an admin
        self.finalizer = whodunit
        self.closing_date = closing_date
        self.save()

class Offer(models.Model):
    rules = models.ManyToManyField(RuleInHand)
    commodities = models.ManyToManyField(CommodityInHand, through='TradedCommodities')

    comment = models.TextField(blank = True, null = True)
    free_information = models.TextField("Free information that won't be revealed until both players accept the trade", blank = True, null = True)

    creation_date = models.DateTimeField(default = now)

    @property
    def summary(self):
        content = []
        nb_rules = len(self.rules.all())
        nb_traded_commodities = sum([t.nb_traded_cards for t in self.tradedcommodities_set.all()])
        if nb_rules > 0:
            content.append("{0} rule{1}".format(nb_rules, "s" if nb_rules > 1 else ""))
        if nb_traded_commodities > 0:
            content.append("{0} commodit{1}".format(nb_traded_commodities, "ies" if nb_traded_commodities > 1 else "y"))
        if self.free_information:
            content.append("some information")

        if not content:
            return
        elif len(content) == 1:
            return content[0]
        else:
            return ", ".join(content[:-1]) + " and " + content[-1]

    @property
    def total_traded_cards(self):
        return len(self.rules.all()) + sum([t.nb_traded_cards for t in self.tradedcommodities_set.all()])

class TradedCommodities(models.Model):
    offer = models.ForeignKey(Offer)
    commodityinhand = models.ForeignKey(CommodityInHand)

    nb_traded_cards = models.PositiveSmallIntegerField(default = 0)