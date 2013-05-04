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
            '(4) Since the combined number of yellow cards ({}) and green cards ({}) is {} (higher than five), the value of green cards is set to zero.'.format(
                scoresheet.nb_scored_cards('Yellow'), scoresheet.nb_scored_cards('Green'), combined_number))

def RMX05(self, scoresheet):
    """"A player can score only as many yellow cards as he/she has pink cards."""
    if scoresheet.nb_scored_cards('Yellow') > scoresheet.nb_scored_cards('Pink'):
        scoresheet.set_nb_scored_cards('Yellow', nb_scored_cards = scoresheet.nb_scored_cards('Pink'))
        scoresheet.register_score_from_rule(self,
                                            '(5) Since there are {0} pink card(s), only {0} yellow card(s) score.'.format(scoresheet.nb_scored_cards('Pink')))

def RMX06(self, scoresheets):
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
                                                '(6) Since player #{} has {} blue cards, 10 points are deducted.'.format(culprit + 1, scoresheets[culprit].nb_scored_cards('Blue')),
                                                score = -10)

def RMX07(self, scoresheet):
    """A set of three yellow cards protects you from one set of five blue cards."""
    nb_sets = int(scoresheet.nb_scored_cards('Yellow')) / 3
    for _i in range(nb_sets):
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard.ref_name == 'RMX06' and sfr.score:
                sfr.score = None
                sfr.detail = sfr.detail.replace('are deducted.', 'should have been deducted...')
                scoresheet.register_score_from_rule(self, '(7) ...but a set of three yellow cards cancels that penalty.')
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
            scoresheet.register_score_from_rule(self, '(8) A set of five different colors gives a bonus of 8 points.', score = 8)

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
                                        '(9) Having the most white cards ({} cards) triples their value.'.format(winner.nb_scored_cards('White')),
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
        detail = '(10) Since the total of the basic values of your cards was {} points (more than 39), '.format(initial_score)
        detail += 'the following cards have been discarded to bring the new basic total (before applying all other rules) to {} points: '.format(scoresheet.total_score)
        for index, color in enumerate(discarded.iterkeys()):
            detail += '{} {} card'.format(discarded[color], color) + ('s' if discarded[color] > 1 else '')
            detail += ', ' if index < (len(discarded) - 1) else '.'
        scoresheet.register_score_from_rule(self, detail, is_random = True)
