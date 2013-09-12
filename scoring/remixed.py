"""
    Rule card scoring resolution for ruleset "Remixed Haggle"
"""
import random


def RMX04(self, scoresheet):
    """If a player has a combined number of yellow and green cards strictly higher than five cards,
        all of his/her green cards lose their value."""
    combined_number = scoresheet.nb_scored_cards('Yellow') + scoresheet.nb_scored_cards('Green')
    if combined_number > 5:
        scoresheet.set_actual_value('Green', actual_value = 0)
        scoresheet.register_score_from_rule(self,
            'Since the combined number of yellow cards ({0}) and green cards ({1}) is {2} (higher than five), the value of green cards is set to zero.'.format(
                scoresheet.nb_scored_cards('Yellow'), scoresheet.nb_scored_cards('Green'), combined_number))

def RMX05(self, scoresheet):
    """"A player can score only as many yellow cards as he/she has pink cards."""
    if scoresheet.nb_scored_cards('Yellow') > scoresheet.nb_scored_cards('Pink'):
        scoresheet.set_nb_scored_cards('Yellow', nb_scored_cards = scoresheet.nb_scored_cards('Pink'))
        scoresheet.register_score_from_rule(self,
                                            'Since there are {0} pink card(s), only {0} yellow card(s) score.'.format(scoresheet.nb_scored_cards('Pink')))

def RMX06(self, scoresheets):
    """If a player has five or more blue cards, 10 points are deducted from every other player's score.

        # Global rulecard #
    """
    culprits = []
    for player in scoresheets:
        if player.nb_scored_cards('Blue') >= 5:
            culprits.append(player)
    for culprit in culprits:
        for victim in scoresheets:
            if victim != culprit:
                victim.register_score_from_rule(self,
                                                'Since {0} has {1} blue cards, 10 points are deducted.'.format(culprit.player_name, culprit.nb_scored_cards('Blue')),
                                                score = -10)

def RMX07(self, scoresheet):
    """A set of three yellow cards protects you from one set of five blue cards."""
    nb_sets = int(scoresheet.nb_scored_cards('Yellow')) / 3
    for _i in range(nb_sets):
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard.ref_name == 'RMX06' and sfr.score:
                sfr.score = None
                sfr.detail = sfr.detail.replace('are deducted.', 'should have been deducted...')
                scoresheet.register_score_from_rule(self, '...but a set of three yellow cards cancels that penalty.')
    return scoresheet

def RMX08(self, scoresheet):
    """Each set of five different colors gives a bonus of 8 points."""
    min_color_number = None
    nb_colors = 0
    for sfc in scoresheet.scores_from_commodity:
        nb_colors += 1
        if min_color_number is None or sfc.nb_scored_cards < min_color_number:
            min_color_number = sfc.nb_scored_cards
    if min_color_number and nb_colors >= 5:
        for _i in range(min_color_number):
            scoresheet.register_score_from_rule(self, 'A set of five different colors gives a bonus of 8 points.', score = 8)

def RMX09(self, scoresheets):
    """The player with the most white cards triples their value.
        In case of a tie, no player collects the extra value.

        # Global rulecard #
    """
    winner = None
    whites = [player.nb_scored_cards('White') for player in scoresheets]
    if whites.count(max(whites)) == 1 and max(whites) > 0:
        winner = scoresheets[whites.index(max(whites))]
        winner.register_score_from_rule(self,
                                        'Having the most white cards ({0} cards) triples their value.'.format(winner.nb_scored_cards('White')),
                                        score = 2 * winner.nb_scored_cards('White') * winner.actual_value('White'))

def RMX10(self, scoresheet):
    """If the total of the basic values of all the cards handed in by a player is higher than 39 points,
        cards are removed at random until the total becomes less or equal than 39 points.
        Only the basic values of the cards are considered, before any other rule is applied.
    """
    present_colors = []
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_scored_cards > 0:
            present_colors.append(sfc.name)
    initial_score = scoresheet.total_score
    if initial_score > 39:
        discarded = {}
        while scoresheet.total_score > 39:
            selected_color = random.choice(present_colors)
            scoresheet.set_nb_scored_cards(selected_color, nb_scored_cards = scoresheet.nb_scored_cards(selected_color) - 1)
            if selected_color not in discarded:
                discarded[selected_color] = 1
            else:
                discarded[selected_color] += 1
            if scoresheet.nb_scored_cards(selected_color) == 0:
                present_colors.remove(selected_color)
        detail = 'Since the total of the basic values of your cards was {0} points (more than 39), '.format(initial_score)
        detail += 'the following cards have been discarded to bring the new basic total (before applying all other rules) to {0} points: '.format(scoresheet.total_score)
        for index, color in enumerate(discarded.iterkeys()):
            detail += '{0} {1} card'.format(discarded[color], color) + ('s' if discarded[color] > 1 else '')
            detail += ', ' if index < (len(discarded) - 1) else '.'
        scoresheet.register_score_from_rule(self, detail, is_random = True)

def RMX11(self, scoresheet):
    """If a player hands in seven or more cards of the same color,
       for each of these colors 10 points are deducted from his/her score.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_submitted_cards >= 7:
            scoresheet.register_score_from_rule(self,
                                                'Since {0} {1} cards where submitted (seven or more), 10 points are deducted.'.format(sfc.nb_submitted_cards, sfc.name),
                                                score = -10)

def RMX12(self, scoresheets):
    """The player with the most blue cards doubles the value of his/her pink cards.
        In case of a tie, no player collects the extra value.

        # Global rulecard #
    """
    winner = None
    blues = [player.nb_scored_cards('Blue') for player in scoresheets]
    if blues.count(max(blues)) == 1 and max(blues) > 0:
        winner = scoresheets[blues.index(max(blues))]
        winner.register_score_from_rule(self,
                                        'Having the most blue cards ({0} cards) doubles the value of pink cards.'.format(winner.nb_scored_cards('Blue')),
                                        score = winner.nb_scored_cards('Pink') * winner.actual_value('Pink'))

def RMX13(self, scoresheet):
    """If four colors are handed in with the same number of cards for each,
        and no cards are handed in from the fifth color, the value of the hand is doubled.

       Note: this rule deals with cards *submitted*, not scored. Hence the use of 'nb_submitted_cards'.
    """
    nb_colors = []
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_submitted_cards > 0:
            nb_colors.append({ 'color': sfc.name, 'nb_cards': sfc.nb_submitted_cards })
    if len(nb_colors) == 4 and all(item['nb_cards'] == nb_colors[0]['nb_cards'] for item in nb_colors):
        scoresheet.register_score_from_rule(self,
                                            'A set of the same number of cards for 4 colors ({0}, {1}, {2}, {3}) and no other cards doubles the score.'.format(
                                                nb_colors[0]['color'], nb_colors[1]['color'], nb_colors[2]['color'], nb_colors[3]['color']),
                                            score = scoresheet.total_score)

def RMX14(self, scoresheet):
    """Each set of two pink cards doubles the value of one yellow card."""
    nb_sets = int(scoresheet.nb_scored_cards('Pink')) / 2
    nb_bonus = min(nb_sets, scoresheet.nb_scored_cards('Yellow'))
    for _i in range(nb_bonus):
        scoresheet.register_score_from_rule(self,
                                            'A pair of pink cards doubles the value of one yellow card.',
                                            score = scoresheet.actual_value('Yellow'))

def RMX15(self, scoresheet):
    """Each set of three white cards triples the value of one green card."""
    nb_sets = int(scoresheet.nb_scored_cards('White')) / 3
    nb_bonus = min(nb_sets, scoresheet.nb_scored_cards('Green'))
    for _i in range(nb_bonus):
        scoresheet.register_score_from_rule(self,
                                            'A set of three white cards triples the value of one green card.',
                                            score = 2 * scoresheet.actual_value('Green'))