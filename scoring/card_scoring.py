def tally_scores(hands, ruleset, selected_rules):
    scoresheets = [_hand_to_scoresheet(hand) for hand in hands]
    rules = sorted(selected_rules, key = lambda rule : rule.step)
    for rule in rules:
        if rule.step is None:
            continue
        players = rule.perform(scoresheets)
    return ([calculate_player_score(scoresheet) for scoresheet in scoresheets], scoresheets)

def calculate_player_score(scoresheet):
    score = 0
    for color, details in scoresheet.iteritems():
        if color == 'extra':
            score += sum(extra['score'] for extra in details if extra['score'] is not None)
        else:
            score += details['scored_cards'] * details['actual_value']
    return score

def register_rule(scoresheet, rulename, detail = '', score = None):
    scoresheet['extra'].append({'cause': rulename, 'detail': detail, 'score': score})
    return scoresheet

def _hand_to_scoresheet(hand):
    scoresheet = {}
    for commodity, nb_cards in hand.iteritems():
        scoresheet[commodity.name] = {'handed_cards': nb_cards,
                                      'scored_cards': nb_cards,
                                      'actual_value': commodity.value }
    scoresheet['extra'] = []
    return scoresheet
