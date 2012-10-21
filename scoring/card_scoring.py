def HAG01(hand):
    scoresheet = []
    for commodity, nb_cards in hand.iteritems():
        scoresheet.append({'type':              'commodity',
                           'commodity':         commodity,
                           'nb_cards':          nb_cards,
                           'actual_value':      commodity.value,
                           'accepted_cards':    nb_cards})
    return scoresheet
    # HAG02 and HAG03 are already included above

def HAG04(scoresheet):
    for item in scoresheet:
        if item['type'] == 'commodity' and item['commodity'].name == 'White':
            if item['accepted_cards'] > 3:
                item['actual_value'] = 0
            break
    return scoresheet

def calculate_score(scoresheet):
    score = 0
    for item in scoresheet:
        if item['type'] == 'commodity':
            score += item['accepted_cards'] * item['actual_value']
    return score