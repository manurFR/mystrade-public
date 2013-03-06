from game.models import GamePlayer, CommodityInHand

def tally_scores(game):
    """ hands = [{commodity1: <nb_submitted_cards>, commodity2: <nb_submitted_cards>, ...}, # player 1
                 {commodity1: <nb_submitted_cards>, commodity2: <nb_submitted_cards>, ...}, # player 2 etc.
                 ...]
        selected_rules = [rulecard1, rulecard2, ...]
    """
    if not game:
        return [],[]
    selected_rules = list(game.rules.all())

    scoresheets = [Scoresheet(gameplayer) for gameplayer in GamePlayer.objects.filter(game = game)]
    rules = sorted(selected_rules, key = lambda rule : rule.step)
    for rule in rules:
        if rule.step is None:
            continue
        rule.perform(scoresheets)
    return [scoresheet.calculate_score() for scoresheet in scoresheets], scoresheets

class Scoresheet(object):
    NEUTRAL_COMMODITY = {'name'                : '',
                         'nb_submitted_cards'  : 0,
                         'nb_scored_cards'     : 0,
                         'actual_value'        : 0 }

    def __init__(self, gameplayer):
        self._commodities = []
        for cih in CommodityInHand.objects.filter(game = gameplayer.game, player = gameplayer.player, nb_submitted_cards__gt = 0):
            self._commodities.append({'name'                : cih.commodity.name,
                                      'nb_submitted_cards'  : cih.nb_submitted_cards,
                                      'nb_scored_cards'     : cih.nb_submitted_cards,
                                      'actual_value'        : cih.commodity.value })
        self._extra = []

    def commodity(self, name):
        for c in self.commodities:
            if c['name'] == name:
                return c
        return Scoresheet.NEUTRAL_COMMODITY # this way scoresheet('dummy')['nb_scored_cards'] won't raise an exception, just return 0

    def register_rule(self, rulename, detail = '', score = None):
        self._extra.append({'cause': rulename, 'detail': detail, 'score': score})

    def calculate_score(self):
        score = 0
        for commodity_item in self.commodities:
            commodity_score = commodity_item['nb_scored_cards'] * commodity_item['actual_value']
            commodity_item['score'] = commodity_score
            score += commodity_score
        score += sum(item['score'] for item in self.extra if item['score'] is not None)
        return score
    
    @property
    def commodities(self):
        return self._commodities
    
    @property
    def extra(self):
        return self._extra
