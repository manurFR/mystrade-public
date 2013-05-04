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

