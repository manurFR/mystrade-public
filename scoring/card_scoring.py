import importlib

def scoring(hands, ruleset, selected_rules):
    module = importlib.import_module(ruleset.module)
    scoresheets = [_hand_to_scoresheet(hand) for hand in hands]
    rules = sorted(selected_rules, key = lambda rule : rule.step)
    for rule in rules:
        if rule.step is None:
            continue
        func = getattr(module, rule.ref_name)
        if rule.glob:
            scoresheets = func(scoresheets)
        else:
            for scoresheet in scoresheets:
                scoresheet = func(scoresheet)
    return scoresheets

def calculate_player_score(scoresheet):
    score = 0
    for color, details in scoresheet.iteritems():
        if color == 'extra':
            score += sum([extra['score'] for extra in details])
        else:
            score += details['scored_cards'] * details['actual_value']
    return score

def _hand_to_scoresheet(hand):
    scoresheet = {}
    for commodity, nb_cards in hand.iteritems():
        scoresheet[commodity.name] = {'handed_cards': nb_cards,
                                      'scored_cards': nb_cards,
                                      'actual_value': commodity.value }
    scoresheet['extra'] = []
    return scoresheet
