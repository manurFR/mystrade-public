import random

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

#
### Pre-treatment rules
# They should be applied before all other rules (for example because they can exclude any card from a hand)
#

def HAG15(scoresheet):
    """No more than thirteen cards in a hand can be scored.
       If more are handed in, the excess will be removed at random.
    """
    total_scored_cards = 0
    present_colors = []
    for color, details in scoresheet.iteritems():
        if color != 'extra' and details['scored_cards'] > 0:
            present_colors.append(color)
            total_scored_cards += details['scored_cards']
    while total_scored_cards > 13:
        selected_color = random.choice(present_colors)
        scoresheet[selected_color]['scored_cards'] -= 1
        if scoresheet[selected_color]['scored_cards'] == 0:
            present_colors.remove(selected_color)
        total_scored_cards -= 1
    return scoresheet

#
### Modifying rules
# These rules may modify the number of scored cards or their value.
#

def HAG04(scoresheet):
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    if scoresheet['White']['scored_cards'] > 3:
        scoresheet['White']['actual_value'] = 0
    return scoresheet

def HAG05(scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    if scoresheet['Orange']['scored_cards'] > scoresheet['Blue']['scored_cards']:
        scoresheet['Orange']['scored_cards'] = scoresheet['Blue']['scored_cards']
    return scoresheet

#
### Regular rules
# These rules are guaranteed that each commodity has a stable value and number of scored cards
# when they're applied (no future modifications).
# They may or may not use this property.
# These rules must be applied only after all Modifying rules.
#

def HAG09(scoresheet):
    """If a player hands in seven or more cards of the same color, 
       for each of these colors 10 points are deducted from his/her score.

       Note: this rule deals with cards *handed in*, not scored. Hence the use of 'handed_cards'.
    """
    for color, details in scoresheet.iteritems():
        if color != 'extra':
            if details['handed_cards'] >= 7:
                scoresheet['extra'].append({'score': -10, 'cause': 'HAG09'})
    return scoresheet

def HAG10(scoresheet):
    """Each set of five different colors gives a bonus of 10 points."""
    min_color_number = None
    nb_colors = 0
    for color, details in scoresheet.iteritems():
        if color != 'extra':
            nb_colors += 1
            if min_color_number is None or details['scored_cards'] < min_color_number:
                min_color_number = details['scored_cards']
    if min_color_number and nb_colors >= 5:
        for _i in range(min_color_number):
            scoresheet['extra'].append({'score': 10, 'cause': 'HAG10'})
    return scoresheet

def HAG13(scoresheet):
    """Each set of two yellow cards doubles the value of one white card."""
    nb_sets = int(scoresheet['Yellow']['scored_cards']) / 2
    nb_bonus = min(nb_sets, scoresheet['White']['scored_cards'])
    for _i in range(nb_bonus):
        scoresheet['extra'].append({'score': scoresheet['White']['actual_value'], 'cause': 'HAG13'})
    return scoresheet

def HAG14(scoresheet):
    """Each set of three blue cards quadruples the value of one orange card."""
    nb_sets = int(scoresheet['Blue']['scored_cards']) / 3
    nb_bonus = min(nb_sets, scoresheet['Orange']['scored_cards'])
    for _i in range(nb_bonus):
        scoresheet['extra'].append({'score': 3 * scoresheet['Orange']['actual_value'], 'cause': 'HAG14'})
    return scoresheet

#
## Global rules
# These rules may impact other players' score or may require a comparison of the hand of all players.
#

def HAG06(players):
    """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
    culprits = []
    for index, player in enumerate(players):
        if player['Blue']['scored_cards'] >= 5:
            culprits.append(index)
    for culprit in culprits:
        for index, victim in enumerate(players):
            if index != culprit:
                victim['extra'].append({'score': -10, 'cause': 'HAG06'})
    return players

def HAG07(players):
    """A set of three red cards protects you from one set of five blue cards."""
    for player in players:
        nb_sets = int(player['Red']['scored_cards']) / 3
        for _i in range(nb_sets):
            for extra in player['extra']:
                if extra['cause'] == 'HAG06' and extra['score'] <> 0:
                    extra['score'] = 0
                    extra['cause'] = 'HAG07' 
    return players

#
## Post-treatment rules
# These rules will be applies after all other rules (for example because they need the total score).
#

def HAG11(scoresheet):
    """If a \"pyramid\" is handed in with no other cards, the value of the hand is doubled. 
       A pyramid consists of four cards of one color, three cards of a second color, 
       two cards of a third, and one card of a fourth color.
       
       Note: this rule deals with cards *handed in*, not scored. Hence the use of 'handed_cards'.
    """
    nb_colors = []
    for color, details in scoresheet.iteritems():
        if color != 'extra':
            nb_colors.append(details['handed_cards'])
    if sorted(nb_colors) == [0, 1, 2, 3, 4]:
        scoresheet['extra'].append({'score': calculate_score(scoresheet), 'cause': 'HAG11'})
    return scoresheet