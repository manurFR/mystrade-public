"""
    Rule card scoring resolution for ruleset "Original Haggle"
"""

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