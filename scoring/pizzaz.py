"""
    Rule card scoring resolution for ruleset "Pizzaz!"
"""

def PIZ04(rulecard, scoresheet):
    """ If your pizza contains no Cheese, Don Peppino will curse you but his wife will arrange so
        that you get a bonus of 6 points (damn doctors!).  """
    nb_cheeses = 0
    for sfc in scoresheet.scores_from_commodity:
        if sfc.commodity.category.lower() == 'cheese':
            nb_cheeses += 1
    if nb_cheeses == 0:
        scoresheet.register_score_from_rule(rulecard, 'A pizza with no cheese gives you a bonus of 6 points.', score = 6)

def PIZ06(rulecard, scoresheet):
    """Don Peppino likes his pizza with no more than 10 toppings (cards). Each added topping removes 5 points."""
    total_scored_cards = 0
    for sfc in scoresheet.scores_from_commodity:
        total_scored_cards += sfc.nb_scored_cards
    if total_scored_cards > 10:
        removed_points = (total_scored_cards - 10) * 5
        scoresheet.register_score_from_rule(rulecard, 'Since your pizza had {0} toppings (more than 10), you lose {1} points.'.format(total_scored_cards, removed_points),
                                            score = -removed_points)

def PIZ07(rulecard, scoresheet):
    """If you pizza has more Vegetable [V] cards than Meat [M], Fish & Seafood [F&S] and Cheese [C] cards combined,
        there is a bonus of 12 points for you."""
    vegetables = 0
    proteins = 0
    for sfc in scoresheet.scores_from_commodity:
        category = sfc.commodity.category.lower()
        if category == 'vegetable':
            vegetables += sfc.nb_scored_cards
        elif category in ['meat', 'fish & seafood', 'cheese']:
            proteins += sfc.nb_scored_cards
    if vegetables > proteins:
        scoresheet.register_score_from_rule(rulecard, 'There is more Vegetable cards in your pizza than Meat, Fish & Seafood and Cheese cards combined. You earn a bonus of 12 points.',
                                            score = 12)

def PIZ08(rulecard, scoresheet):
    """ Don Peppino dislikes the following toppings, unless paired with the appropriate ingredient:
        peppers, pineapple and ham. Absolutely no points can be earned from those. """
    if scoresheet.nb_scored_cards('Peppers') + scoresheet.nb_scored_cards('Pineapple') + scoresheet.nb_scored_cards('Ham') > 0:
        scoresheet.register_score_from_rule(rulecard, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')
    scoresheet.set_nb_scored_cards('Peppers', nb_scored_cards = 0)
    scoresheet.set_nb_scored_cards('Pineapple', nb_scored_cards = 0)
    scoresheet.set_nb_scored_cards('Ham', nb_scored_cards = 0)

def PIZ09(rulecard, scoresheet):
    """ One garlic card makes Don Peppino tolerate all the toppings he usually dislikes. But beware!
        More than one garlic and he'll revert to his usual distastes. """
    for sfr in scoresheet.scores_from_rule:
        if sfr.rulecard.ref_name == 'PIZ08':
            if scoresheet.nb_scored_cards('Garlic') == 1:
                sfr.detail = sfr.detail.replace('give you no points.', 'should give you no points...')
                scoresheet.register_score_from_rule(rulecard, '...but since your pizza contains one garlic, he tolerates them. Phew!')
                scoresheet.set_nb_scored_cards('Peppers', nb_scored_cards = scoresheet.score_for_commodity('Peppers').nb_submitted_cards)
                scoresheet.set_nb_scored_cards('Pineapple', nb_scored_cards = scoresheet.score_for_commodity('Pineapple').nb_submitted_cards)
                scoresheet.set_nb_scored_cards('Ham', nb_scored_cards = scoresheet.score_for_commodity('Ham').nb_submitted_cards)
            break

def PIZ10(rulecard, scoresheet):
    """ Each topping with at least a double ration (two cards or more) is worth 4 points more. """
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_scored_cards > 1:
            scoresheet.register_score_from_rule(rulecard, 'A double ration of {0} gives you a bonus of 4 points.'.format(sfc.commodity.name), score = 4)

def PIZ11(rulecard, scoresheet):
    """ A pizza with at least three different toppings whose name begins with the same letter brings
        a bonus of 8 points. (Different letters will add up.) """
    letters = {}
    for sfc in scoresheet.scores_from_commodity:
        capital = sfc.commodity.name[0:1].upper()
        if capital in letters:
            letters[capital].append(sfc.commodity.name)
        else:
            letters[capital] = [sfc.commodity.name]
    for capital, toppings in letters.iteritems():
        if len(toppings) >= 3:
            # sort (alphabetically) the list of toppings to have a determinist output
            scoresheet.register_score_from_rule(rulecard, '{0} different toppings starting by the letter {1} ({2}) give you a bonus of 8 points.'
                                                            .format(len(toppings), capital, ', '.join(sorted(toppings))), score = 8)

def PIZ12(rulecard, scoresheets):
    """ The cook whose pizza has the smallest number of different toppings will earn a bonus of 12 points.
        In case of a tie, each player will earn the bonus. (Multiple copies of the same topping count for one.)

        # Global rulecard #
    """
    toppings_count = {}
    for player in scoresheets:
        # use of nb_submitted_cards and not nb_scored_cards because cards excluded by other rules (such as PIZ08) should not help us win here
        toppings_count[player] = len([sfc for sfc in player.scores_from_commodity if sfc.nb_submitted_cards > 0])

    min_toppings = min(toppings_count.itervalues())

    for player, nb_toppings in toppings_count.iteritems():
        if nb_toppings == min_toppings:
            player.register_score_from_rule(rulecard, 'You have the smallest number of different toppings ({0} toppings) of all the players. You earn a bonus of 12 points.'.format(min_toppings),
                                            score = 12)