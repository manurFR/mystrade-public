"""
    Rule card scoring resolution for ruleset "Original Haggle"
"""
import random

def HAG04(self, scoresheet):
    """If a player has more than three white cards, all of his/her white cards lose their value."""
    if scoresheet.nb_scored_cards('White') > 3:
        scoresheet.set_actual_value('White', actual_value = 0)
        scoresheet.register_score_from_rule(self,
            '(4) Since there are {0} white cards (more than three), their value is set to zero.'.format(scoresheet.nb_scored_cards('White')))

def HAG05(self, scoresheet):
    """"A player can score only as many as orange cards as he/she has blue cards."""
    if scoresheet.nb_scored_cards('Orange') > scoresheet.nb_scored_cards('Blue'):
        scoresheet.set_nb_scored_cards('Orange', nb_scored_cards = scoresheet.nb_scored_cards('Blue'))
        scoresheet.register_score_from_rule(self,
            '(5) Since there are {0} blue card(s), only {0} orange card(s) score.'.format(scoresheet.nb_scored_cards('Blue')))

def HAG06(self, scoresheets):
    """If a player has five or more blue cards, 10 points are deducted from every other player's score.

        # Global rulecard #
    """
    culprits = []
    for index, player in enumerate(scoresheets):
        if player.nb_scored_cards('Blue') >= 5:
            culprits.append(index)
    for culprit in culprits:
        for index, victim in enumerate(scoresheets):
            if index != culprit:
                victim.register_score_from_rule(self,
                              '(6) Since player #{0} has {1} blue cards, 10 points are deducted.'.format(culprit + 1, scoresheets[culprit].nb_scored_cards('Blue')),
                              score = -10)

def HAG07(self, scoresheet):
    """A set of three red cards protects you from one set of five blue cards."""
    nb_sets = int(scoresheet.nb_scored_cards('Red')) / 3
    for _i in range(nb_sets):
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard.ref_name == 'HAG06' and sfr.score:
                sfr.score = None
                sfr.detail = sfr.detail.replace('are deducted.', 'should have been deducted...')
                scoresheet.register_score_from_rule(self, '(7) ...but a set of three red cards cancels that penalty.')
    return scoresheet

def HAG08(self, scoresheets):
    """The player with the most yellow cards gets a bonus of the number of those cards squared. 
       If two or more players tie for most yellow, the bonus is calculated instead for the player 
       with the next highest number of yellows.

        # Global rulecard #
    """
    yellows = [player.nb_scored_cards('Yellow') for player in scoresheets]
    for winning_number in range(max(yellows), 1, -1):
        if yellows.count(winning_number) == 1:
            winner = scoresheets[yellows.index(winning_number)]
            winner.register_score_from_rule(self,
                          '(8) Having the most yellow cards ({0} cards) gives a bonus of {0}x{0} points.'.format(winner.nb_scored_cards('Yellow')),
                          score = winner.nb_scored_cards('Yellow') ** 2)
            break

def HAG09(self, scoresheet):
    """If a player hands in seven or more cards of the same color, 
       for each of these colors 10 points are deducted from his/her score.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_submitted_cards >= 7:
            scoresheet.register_score_from_rule(self,
                              '(9) Since {0} {1} cards where submitted (seven or more), 10 points are deducted.'.format(sfc.nb_submitted_cards, sfc.name),
                              score = -10)

def HAG10(self, scoresheet):
    """Each set of five different colors gives a bonus of 10 points."""
    min_color_number = None
    nb_colors = 0
    for sfc in scoresheet.scores_from_commodity:
        nb_colors += 1
        if min_color_number is None or sfc.nb_scored_cards < min_color_number:
            min_color_number = sfc.nb_scored_cards
    if min_color_number and nb_colors >= 5:
        for _i in range(min_color_number):
            scoresheet.register_score_from_rule(self, '(10) A set of five different colors gives a bonus of 10 points.', score = 10)

def HAG11(self, scoresheet):
    """If a \"pyramid\" is submitted with no other cards, the value of the hand is doubled.
       A pyramid consists of four cards of one color, three cards of a second color, 
       two cards of a third, and one card of a fourth color.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    nb_colors = []
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_submitted_cards > 0:
            nb_colors.append({ 'color': sfc.name, 'nb_cards': sfc.nb_submitted_cards })
    nb_colors.sort(key = lambda item: item['nb_cards'])
    if [item['nb_cards'] for item in nb_colors] == [1, 2, 3, 4]:
        scoresheet.register_score_from_rule(self,
                      '(11) A pyramid of 4 {0} cards, 3 {1} cards, 2 {2} cards, 1 {3} card and no other card doubles the score.'.format(nb_colors[3]['color'], nb_colors[2]['color'], nb_colors[1]['color'], nb_colors[0]['color']),
                      score = scoresheet.total_score)

def HAG12(self, scoresheets):
    """The player with the most red cards double their value.
       In case of a tie, no player collects the extra value.

        # Global rulecard #
    """
    winner = None
    reds = [player.nb_scored_cards('Red') for player in scoresheets]
    if reds.count(max(reds)) == 1 and max(reds) > 0:
        winner = scoresheets[reds.index(max(reds))]
        winner.register_score_from_rule(self,
                      '(12) Having the most red cards ({0} cards) doubles their value.'.format(winner.nb_scored_cards('Red')),
                      score = winner.nb_scored_cards('Red') * winner.actual_value('Red'))

def HAG13(self, scoresheet):
    """Each set of two yellow cards doubles the value of one white card."""
    nb_sets = int(scoresheet.nb_scored_cards('Yellow')) / 2
    nb_bonus = min(nb_sets, scoresheet.nb_scored_cards('White'))
    for _i in range(nb_bonus):
        scoresheet.register_score_from_rule(self,
                      '(13) A pair of yellow cards doubles the value of one white card.',
                      score = scoresheet.actual_value('White'))

def HAG14(self, scoresheet):
    """Each set of three blue cards quadruples the value of one orange card."""
    nb_sets = int(scoresheet.nb_scored_cards('Blue')) / 3
    nb_bonus = min(nb_sets, scoresheet.nb_scored_cards('Orange'))
    for _i in range(nb_bonus):
        scoresheet.register_score_from_rule(self,
                      '(14) A set of three blue cards quadruples the value of one orange card.',
                      score = 3 * scoresheet.actual_value('Orange'))

def HAG15(self, scoresheet):
    """No more than thirteen cards in a hand can be scored.
       If more are submitted, the excess will be removed at random.
    """
    total_scored_cards = 0
    present_colors = []
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_scored_cards > 0:
            present_colors.append(sfc.name)
            total_scored_cards += sfc.nb_scored_cards
    if total_scored_cards > 13:
        detail = '(15) Since {0} cards had to be scored, {1} have been discarded (to keep only 13 cards) : '.format(total_scored_cards, total_scored_cards - 13)
        discarded = {}
        while total_scored_cards > 13:
            selected_color = random.choice(present_colors)
            scoresheet.set_nb_scored_cards(selected_color, nb_scored_cards = scoresheet.nb_scored_cards(selected_color) - 1)
            if selected_color not in discarded:
                discarded[selected_color] = 1
            else:
                discarded[selected_color] += 1
            if scoresheet.nb_scored_cards(selected_color) == 0:
                present_colors.remove(selected_color)
            total_scored_cards -= 1
        for index, color in enumerate(discarded.iterkeys()):
            detail += '{0} {1} card'.format(discarded[color], color) + ('s' if discarded[color] > 1 else '')
            detail += ', ' if index < (len(discarded) - 1) else '.'
        scoresheet.register_score_from_rule(self, detail, is_random = True)
