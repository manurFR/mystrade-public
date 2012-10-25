#def scoring(hands, rules):
#    scoresheets = [setup_scoresheet(hand) for hand in hands]

def setup_scoresheet(hand):
    scoresheet = {}
    for commodity, nb_cards in hand.iteritems():
        scoresheet[commodity.name] = {'handed_cards': nb_cards,
                                      'scored_cards': nb_cards,
                                      'actual_value': commodity.value }
    scoresheet['extra'] = []
    return scoresheet

def calculate_score(scoresheet):
    score = 0
    for color, details in scoresheet.iteritems():
        if color == 'extra':
            score += sum([extra['score'] for extra in details])
        else:
            score += details['scored_cards'] * details['actual_value']
    return score