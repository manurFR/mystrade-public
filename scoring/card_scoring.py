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
    def __init__(self, gameplayer):
        self.gameplayer = gameplayer
        self._scores_from_commodity = []
        for cih in CommodityInHand.objects.filter(game = gameplayer.game, player = gameplayer.player, nb_submitted_cards__gt = 0):
            sfc = ScoreFromCommodity(game = gameplayer.game, player = gameplayer.player, commodity = cih.commodity,
                                     nb_scored_cards = cih.nb_submitted_cards, actual_value = cih.commodity.value, score = 0)
            sfc.name = cih.commodity.name.lower()
            sfc.nb_submitted_cards = cih.nb_submitted_cards # non persisted property added for ease of scoring
            self._scores_from_commodity.append(sfc)
        self._scores_from_rule = []

        self.neutral_commodity = ScoreFromCommodity(game = gameplayer.game, player = gameplayer.player, commodity = Commodity(),
                                                    nb_scored_cards = 0, actual_value = 0, score = 0)

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

    def register_score_from_rule(self, rulecard, detail = '', score = None):
        self._scores_from_rule.append(ScoreFromRule(game = self.gameplayer.game, player = self.gameplayer.player,
                                                    rulecard = rulecard, detail = detail, score = score))

    def _calculate_commodity_scores(self):
        for sfc in self.scores_from_commodity:
            sfc.score = sfc.nb_scored_cards * sfc.actual_value
        return sum(sfc.score for sfc in self.scores_from_commodity)

    @property
    def total_score(self):
        return self._calculate_commodity_scores() + sum(sfr.score for sfr in self.scores_from_rule if sfr.score is not None)

    @property
    def scores_from_commodity(self):
        return self._scores_from_commodity

    @property
    def scores_from_rule(self):
        return self._scores_from_rule

