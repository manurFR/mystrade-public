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
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    for item in scoresheet:
        if item['type'] == 'commodity' and item['commodity'].name == 'White':
            if item['accepted_cards'] > 3:
                item['actual_value'] = 0
            break
    return scoresheet

def HAG05(scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    for item in scoresheet:
        if item['type'] == 'commodity' and item['commodity'].name == 'Blue':
            max_orange = item['nb_cards']
            break
    for item in scoresheet:
        if item['type'] == 'commodity' and item['commodity'].name == 'Orange':
            if item['accepted_cards'] > max_orange:
                item['accepted_cards'] = max_orange
            break
    return scoresheet    

def calculate_score(scoresheet):
    score = 0
    for item in scoresheet:
        if item['type'] == 'commodity':
            score += item['accepted_cards'] * item['actual_value']
    return score