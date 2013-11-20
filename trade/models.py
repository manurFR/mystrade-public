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
    TRADE_STATUS = ['INITIATED', 'REPLIED', 'ACCEPTED', 'CANCELLED', 'DECLINED']

    game = models.ForeignKey(Game)

    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="initiator_trades_set")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="responder_trades_set")

    initiator_offer = models.OneToOneField('Offer', related_name = 'trade_initiated')
    responder_offer = models.OneToOneField('Offer', related_name = 'trade_responded', null = True)

    status = models.CharField(max_length = 15, choices =[(status, status) for status in TRADE_STATUS], default = "INITIATED") # see above

    finalize_reason = models.TextField(blank = True, null = True)
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

    def is_pending(self):
        return self.status == 'INITIATED' or self.status == 'REPLIED'

class Offer(models.Model):
    rules = models.ManyToManyField(RuleInHand)
    commodities = models.ManyToManyField(CommodityInHand, through = 'TradedCommodities')

    comment = models.TextField(blank = True, null = True)
    free_information = models.TextField("Free information that won't be revealed until both players accept the trade", blank = True, null = True)

    creation_date = models.DateTimeField(default = now)

    @property
    def total_traded_cards(self):
        return len(self.rules.all()) + sum([t.nb_traded_cards for t in self.tradedcommodities_set.all()])

    @property
    def tradedcommodities(self):
        """ return the traded commodities in the canonical order ; essential in templates, avoids duplication anywhere else """
        return self.tradedcommodities_set.all().order_by('commodityinhand__commodity__name')

    @property
    def rulecards(self):
        """ return the traded rulecards in the canonical order ; essential in templates, avoids duplication anywhere else """
        return self.rules.all().order_by('rulecard__ref_name')

class TradedCommodities(models.Model):
    offer = models.ForeignKey(Offer)
    commodityinhand = models.ForeignKey(CommodityInHand)

    nb_traded_cards = models.PositiveSmallIntegerField(default = 0)