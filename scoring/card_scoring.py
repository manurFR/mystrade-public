def setup_scoresheet(hand):
    scoresheet = {}
    for commodity, nb_cards in hand.iteritems():
        scoresheet[commodity.name] = {'handed_cards': nb_cards,
                                      'scored_cards': nb_cards,
                                      'actual_value': commodity.value }
    scoresheet['extra'] = []
    return scoresheet

def HAG04(scoresheet):
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    if scoresheet['White']['handed_cards'] > 3:
        scoresheet['White']['actual_value'] = 0
    return scoresheet

def HAG05(scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    if scoresheet['Orange']['scored_cards'] > scoresheet['Blue']['handed_cards']:
        scoresheet['Orange']['scored_cards'] = scoresheet['Blue']['handed_cards']
    return scoresheet

def HAG09(scoresheet):
    """If a player hands in seven or more cards of the same color, 
       for each of these colors 10 points are deducted from his/her score.
    """
    for color, cards in scoresheet.iteritems():
        if color != 'extra':
            if cards['handed_cards'] >= 7:
                scoresheet['extra'].append(-10)
    return scoresheet

def calculate_score(scoresheet):
    score = 0
    for color, cards in scoresheet.iteritems():
        if color == 'extra':
            score += sum(cards)
        else:
            score += cards['scored_cards'] * cards['actual_value']
    return score