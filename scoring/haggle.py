"""
    Rule card scoring resolution for ruleset "Original Haggle"
"""
from scoring.card_scoring import calculate_player_score, register_rule
import random

def HAG04(scoresheet):
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    if scoresheet['White']['scored_cards'] > 3:
        scoresheet['White']['actual_value'] = 0
        register_rule(scoresheet, 'HAG04')
    return scoresheet

def HAG05(scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    if scoresheet['Orange']['scored_cards'] > scoresheet['Blue']['scored_cards']:
        scoresheet['Orange']['scored_cards'] = scoresheet['Blue']['scored_cards']
        register_rule(scoresheet, 'HAG05')
    return scoresheet

def HAG06(players):
    """If a player has five or more blue cards, 10 points are deducted from every other player's score.

        # Global rulecard #
    """
    culprits = []
    for index, player in enumerate(players):
        if player['Blue']['scored_cards'] >= 5:
            culprits.append(index)
    for culprit in culprits:
        for index, victim in enumerate(players):
            if index != culprit:
                register_rule(victim, 'HAG06', score = -10)
    return players

def HAG07(scoresheet):
    """A set of three red cards protects you from one set of five blue cards."""
    nb_sets = int(scoresheet['Red']['scored_cards']) / 3
    for _i in range(nb_sets):
        for extra in scoresheet['extra']:
            if extra['cause'] == 'HAG06' and extra['score'] <> 0:
                extra['score'] = 0
                register_rule(scoresheet, 'HAG07')
    return scoresheet

def HAG08(players):
    """The player with the most yellow cards gets a bonus of the number of those cards squared. 
       If two or more players tie for most yellow, the bonus is calculated instead for the player 
       with the next highest number of yellows.

        # Global rulecard #
    """
    winner = None
    yellows = [player['Yellow']['scored_cards'] for player in players]
    for winning_number in range(max(yellows), 1, -1):
        if yellows.count(winning_number) == 1:
            winner = players[yellows.index(winning_number)]
            register_rule(winner, 'HAG08', score = winner['Yellow']['scored_cards'] ** 2)
            break
    return players

def HAG09(scoresheet):
    """If a player hands in seven or more cards of the same color, 
       for each of these colors 10 points are deducted from his/her score.

       Note: this rule deals with cards *handed in*, not scored. Hence the use of 'handed_cards'.
    """
    for color, details in scoresheet.iteritems():
        if color != 'extra':
            if details['handed_cards'] >= 7:
                register_rule(scoresheet, 'HAG09', score = -10)
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
            register_rule(scoresheet, 'HAG10', score = 10)
    return scoresheet

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
        register_rule(scoresheet, 'HAG11', score = calculate_player_score(scoresheet))
    return scoresheet

def HAG12(players):
    """The player with the most red cards double their value.
       In case of a tie, no player collects the extra value.

        # Global rulecard #
    """
    winner = None
    reds = [player['Red']['scored_cards'] for player in players]
    if reds.count(max(reds)) == 1:
        winner = players[reds.index(max(reds))]
        register_rule(winner, 'HAG12', score = winner['Red']['scored_cards'] * winner['Red']['actual_value'])
    return players

def HAG13(scoresheet):
    """Each set of two yellow cards doubles the value of one white card."""
    nb_sets = int(scoresheet['Yellow']['scored_cards']) / 2
    nb_bonus = min(nb_sets, scoresheet['White']['scored_cards'])
    for _i in range(nb_bonus):
        register_rule(scoresheet, 'HAG13', score = scoresheet['White']['actual_value'])
    return scoresheet

def HAG14(scoresheet):
    """Each set of three blue cards quadruples the value of one orange card."""
    nb_sets = int(scoresheet['Blue']['scored_cards']) / 3
    nb_bonus = min(nb_sets, scoresheet['Orange']['scored_cards'])
    for _i in range(nb_bonus):
        register_rule(scoresheet, 'HAG14', score = 3 * scoresheet['Orange']['actual_value'])
    return scoresheet

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
    if total_scored_cards > 13:
        register_rule(scoresheet, 'HAG15')
        while total_scored_cards > 13:
            selected_color = random.choice(present_colors)
            scoresheet[selected_color]['scored_cards'] -= 1
            if scoresheet[selected_color]['scored_cards'] == 0:
                present_colors.remove(selected_color)
            total_scored_cards -= 1
    return scoresheet