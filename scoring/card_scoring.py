def tally_scores(hands, selected_rules):
    """ hands = [{commodity1: <nb_submitted_cards>, commodity2: <nb_submitted_cards>, ...}, # player 1
                 {commodity1: <nb_submitted_cards>, commodity2: <nb_submitted_cards>, ...}, # player 2 etc.
                 ...]
        selected_rules = [rulecard1, rulecard2, ...]
    """
    scoresheets = [Scoresheet(hand) for hand in hands]
    rules = sorted(selected_rules, key = lambda rule : rule.step)
    for rule in rules:
        if rule.step is None:
            continue
        rule.perform(scoresheets)
    return [scoresheet.calculate_score() for scoresheet in scoresheets], scoresheets

class Scoresheet(object):
    def __init__(self, hand):
        self._commodities = []
        for commodity, nb_submitted_cards in hand.iteritems():
            self._commodities.append({'name'                : commodity.name,
                                      'nb_submitted_cards'  : nb_submitted_cards,
                                      'nb_scored_cards'     : nb_submitted_cards,
                                      'actual_value'        : commodity.value })
        self._extra = []

    def commodity(self, name):
        for c in self.commodities:
            if c['name'] == name:
                return c
        return None

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
