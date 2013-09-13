from game.helpers import commodities_in_hand
from game.models import GamePlayer, CommodityInHand
from ruleset.models import Commodity
from scoring.models import ScoreFromRule, ScoreFromCommodity

def tally_scores(game):
    scoresheets = [Scoresheet(gameplayer) for gameplayer in GamePlayer.objects.filter(game = game)]

    for rule in game.rules.filter(step__isnull = False).order_by('step'):
        if rule.glob:
            rule.perform(scoresheets)
        else:
            for scoresheet in scoresheets:
                rule.perform(scoresheet)

    return scoresheets

class Scoresheet(object):
    def __init__(self, gameplayer, scores_from_commodity = None, scores_from_rule = None):
        self.gameplayer = gameplayer

        if scores_from_commodity:
            self._scores_from_commodity = scores_from_commodity
        else:
            self._prepare_scores_from_commodities(gameplayer)

        if scores_from_rule:
            self._scores_from_rule = scores_from_rule
        else:
            self._scores_from_rule = []

        # add non persisted properties for later ease of use
        for sfc in self._scores_from_commodity:
            sfc.name = sfc.commodity.name.lower()

        self.neutral_commodity = ScoreFromCommodity(game = gameplayer.game, player = gameplayer.player, commodity = Commodity(),
                                                    nb_submitted_cards = 0, nb_scored_cards = 0, actual_value = 0, score = 0)

    def score_for_commodity(self, name):
        for sfc in self.scores_from_commodity:
            if sfc.name == name.lower():
                return sfc
        return self.neutral_commodity

    def nb_scored_cards(self, name):
        return self.score_for_commodity(name).nb_scored_cards

    def actual_value(self, name):
        return self.score_for_commodity(name).actual_value

    def set_nb_scored_cards(self, name, nb_scored_cards):
        self.score_for_commodity(name).nb_scored_cards = nb_scored_cards

    def set_actual_value(self, name, actual_value):
        self.score_for_commodity(name).actual_value = actual_value

    def register_score_from_rule(self, rulecard, detail = '', score = None, is_random = None):
        sfr = ScoreFromRule(game=self.gameplayer.game, player=self.gameplayer.player, rulecard=rulecard, detail=detail, score=score)
        self._scores_from_rule.append(sfr)
        # This will not be persisted, and thus will only serve in warning the game master of the non-determinism
        # of the current scores' calculation on the his/her control board
        if is_random:
            sfr.is_random = True

    def persist(self):
        self._calculate_commodity_scores()
        for sfc in self.scores_from_commodity:
            sfc.save()
        for sfr in self.scores_from_rule:
            sfr.save()

    def _calculate_commodity_scores(self):
        for sfc in self.scores_from_commodity:
            sfc.score = sfc.nb_scored_cards * sfc.actual_value
        return sum(sfc.score for sfc in self.scores_from_commodity)

    def _prepare_scores_from_commodities(self, gameplayer):
        commodities = CommodityInHand.objects.filter(game = gameplayer.game, player = gameplayer.player, nb_cards__gt = 0).order_by('commodity__name')
        if gameplayer.submit_date:
            commodities = commodities.filter(nb_submitted_cards__gt = 0)

        self._scores_from_commodity = []
        for cih in commodities:
            nb_scored_cards = cih.nb_submitted_cards if gameplayer.submit_date else cih.nb_cards
            sfc = ScoreFromCommodity(game = gameplayer.game, player = gameplayer.player, commodity = cih.commodity,
                                     nb_submitted_cards = nb_scored_cards, nb_scored_cards = nb_scored_cards,
                                     actual_value = cih.commodity.value, score = 0)
            self._scores_from_commodity.append(sfc)

    @property
    def total_score(self):
        return self._calculate_commodity_scores() + sum(sfr.score for sfr in self.scores_from_rule if sfr.score is not None)

    @property
    def scores_from_commodity(self):
        return self._scores_from_commodity

    @property
    def scores_from_rule(self):
        return self._scores_from_rule

    @property
    def player_name(self):
        return self.gameplayer.player.name
