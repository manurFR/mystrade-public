"""
    Rule card scoring resolution for ruleset "Original Haggle"
"""
import random

def HAG04(self, scoresheet):
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    if scoresheet.commodity('White')['nb_scored_cards'] > 3:
        scoresheet.commodity('White')['actual_value'] = 0
        scoresheet.register_rule(self,
            '(4) Since there are {} white cards (more than three), their value is set to zero.'.format(scoresheet.commodity('White')['nb_scored_cards']))

def HAG05(self, scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    if scoresheet.commodity('Orange')['nb_scored_cards'] > scoresheet.commodity('Blue')['nb_scored_cards']:
        scoresheet.commodity('Orange')['nb_scored_cards'] = scoresheet.commodity('Blue')['nb_scored_cards']
        scoresheet.register_rule(self,
            '(5) Since there are {0} blue card(s), only {0} orange card(s) score.'.format(scoresheet.commodity('Blue')['nb_scored_cards']))

def HAG06(self, scoresheets):
    """If a player has five or more blue cards, 10 points are deducted from every other player's score.

        # Global rulecard #
    """
    culprits = []
    for index, player in enumerate(scoresheets):
        if player.commodity('Blue')['nb_scored_cards'] >= 5:
            culprits.append(index)
    for culprit in culprits:
        for index, victim in enumerate(scoresheets):
            if index != culprit:
                victim.register_rule(self,
                              '(6) Since player #{} has {} blue cards, 10 points are deducted.'.format(culprit + 1, scoresheets[culprit].commodity('Blue')['nb_scored_cards']),
                              score = -10)

def HAG07(self, scoresheet):
    """A set of three red cards protects you from one set of five blue cards."""
    nb_sets = int(scoresheet.commodity('Red')['nb_scored_cards']) / 3
    for _i in range(nb_sets):
        for extra in scoresheet.extra:
            if extra['cause'] == 'HAG06' and extra['score'] <> 0:
                extra['score'] = None
                extra['detail'] = extra['detail'].replace('are deducted.', 'should have been deducted...')
                scoresheet.register_rule(self, '(7) ...but a set of three red cards cancels that penalty.')
    return scoresheet

def HAG08(self, scoresheets):
    """The player with the most yellow cards gets a bonus of the number of those cards squared. 
       If two or more players tie for most yellow, the bonus is calculated instead for the player 
       with the next highest number of yellows.

        # Global rulecard #
    """
    yellows = [player.commodity('Yellow')['nb_scored_cards'] for player in scoresheets]
    for winning_number in range(max(yellows), 1, -1):
        if yellows.count(winning_number) == 1:
            winner = scoresheets[yellows.index(winning_number)]
            winner.register_rule(self,
                          '(8) Having the most yellow cards ({0} cards) gives a bonus of {0}x{0} points.'.format(winner.commodity('Yellow')['nb_scored_cards']),
                          score = winner.commodity('Yellow')['nb_scored_cards'] ** 2)
            break

def HAG09(self, scoresheet):
    """If a player hands in seven or more cards of the same color, 
       for each of these colors 10 points are deducted from his/her score.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    for commodity in scoresheet.commodities:
        if commodity['nb_submitted_cards'] >= 7:
            scoresheet.register_rule(self,
                              '(9) Since {} {} cards where submitted (seven or more), 10 points are deducted.'.format(commodity['nb_submitted_cards'], commodity['name'].lower()),
                              score = -10)

def HAG10(self, scoresheet):
    """Each set of five different colors gives a bonus of 10 points."""
    min_color_number = None
    nb_colors = 0
    for commodity in scoresheet.commodities:
        nb_colors += 1
        if min_color_number is None or commodity['nb_scored_cards'] < min_color_number:
            min_color_number = commodity['nb_scored_cards']
    if min_color_number and nb_colors >= 5:
        for _i in range(min_color_number):
            scoresheet.register_rule(self, '(10) A set of five different colors gives a bonus of 10 points.', score = 10)

def HAG11(self, scoresheet):
    """If a \"pyramid\" is submitted with no other cards, the value of the hand is doubled.
       A pyramid consists of four cards of one color, three cards of a second color, 
       two cards of a third, and one card of a fourth color.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    nb_colors = []
    for commodity in scoresheet.commodities:
        if commodity['nb_submitted_cards'] > 0:
            nb_colors.append({ 'color': commodity['name'].lower(), 'nb_cards': commodity['nb_submitted_cards'] })
    nb_colors.sort(key = lambda item: item['nb_cards'])
    if [item['nb_cards'] for item in nb_colors] == [1, 2, 3, 4]:
        scoresheet.register_rule(self,
                      '(11) A pyramid of 4 {} cards, 3 {} cards, 2 {} cards, 1 {} card and no other card doubles the score.'.format(nb_colors[3]['color'], nb_colors[2]['color'], nb_colors[1]['color'], nb_colors[0]['color']),
                      score = scoresheet.calculate_score())

def HAG12(self, scoresheets):
    """The player with the most red cards double their value.
       In case of a tie, no player collects the extra value.

        # Global rulecard #
    """
    winner = None
    reds = [player.commodity('Red')['nb_scored_cards'] for player in scoresheets]
    if reds.count(max(reds)) == 1 and max(reds) > 0:
        winner = scoresheets[reds.index(max(reds))]
        winner.register_rule(self,
                      '(12) Having the most red cards ({} cards) doubles their value.'.format(winner.commodity('Red')['nb_scored_cards']),
                      score = winner.commodity('Red')['nb_scored_cards'] * winner.commodity('Red')['actual_value'])

def HAG13(self, scoresheet):
    """Each set of two yellow cards doubles the value of one white card."""
    nb_sets = int(scoresheet.commodity('Yellow')['nb_scored_cards']) / 2
    nb_bonus = min(nb_sets, scoresheet.commodity('White')['nb_scored_cards'])
    for _i in range(nb_bonus):
        scoresheet.register_rule(self,
                      '(13) A pair of yellow cards doubles the value of one white card.',
                      score = scoresheet.commodity('White')['actual_value'])

def HAG14(self, scoresheet):
    """Each set of three blue cards quadruples the value of one orange card."""
    nb_sets = int(scoresheet.commodity('Blue')['nb_scored_cards']) / 3
    nb_bonus = min(nb_sets, scoresheet.commodity('Orange')['nb_scored_cards'])
    for _i in range(nb_bonus):
        scoresheet.register_rule(self,
                      '(14) A set of three blue cards quadruples the value of one orange card.',
                      score = 3 * scoresheet.commodity('Orange')['actual_value'])

def HAG15(self, scoresheet):
    """No more than thirteen cards in a hand can be scored.
       If more are submitted, the excess will be removed at random.
    """
    total_scored_cards = 0
    present_colors = []
    for commodity in scoresheet.commodities:
        if commodity['nb_scored_cards'] > 0:
            present_colors.append(commodity['name'])
            total_scored_cards += commodity['nb_scored_cards']
    if total_scored_cards > 13:
        detail = '(15) Since {} cards had to be scored, {} have been discarded (to keep only 13 cards) : '.format(total_scored_cards, total_scored_cards - 13)
        discarded = {}
        while total_scored_cards > 13:
            selected_color = random.choice(present_colors)
            scoresheet.commodity(selected_color)['nb_scored_cards'] -= 1
            if selected_color not in discarded:
                discarded[selected_color] = 1
            else:
                discarded[selected_color] += 1
            if scoresheet.commodity(selected_color)['nb_scored_cards'] == 0:
                present_colors.remove(selected_color)
            total_scored_cards -= 1
        for index, color in enumerate(discarded.iterkeys()):
            detail += '{} {} card'.format(discarded[color], color.lower()) + ('s' if discarded[color] > 1 else '')
            detail += ', ' if index < (len(discarded) - 1) else '.'
        scoresheet.register_rule(self, detail)
