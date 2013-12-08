"""
    Rule card scoring resolution for ruleset "Pizzaz!"
"""
from django.db.models import Q
from trade.models import Trade


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

    min_toppings = min(toppings_count.values())

    for player, nb_toppings in toppings_count.iteritems():
        if nb_toppings == min_toppings:
            player.register_score_from_rule(rulecard, 'You have the smallest number of different toppings ({0} toppings) of all the players. You earn a bonus of 12 points.'.format(min_toppings),
                                            score = 12)

def PIZ13(rulecard, scoresheets):
    """The trade featuring the largest number of cards of the game (rules and toppings given by both players
        combined) will give a bonus of 10 points to both players involved. Only accepted trades count.
        In case of a tie between two or more trades, no one earns the bonus.

        # Global rulecard #
    """
    MESSAGE_DETAIL = 'Your trade with {0} (accepted on {1:%Y/%m/%d %I:%M %p}) included {2} cards. It is the largest number of cards exchanged in a trade. You both earn a bonus of 10 points.'

    cards_count = {}
    for trade in Trade.objects.filter(game = scoresheets[0].gameplayer.game, status = 'ACCEPTED'):
        nb_cards = trade.initiator_offer.rules.count() + sum([tc.nb_traded_cards for tc in trade.initiator_offer.tradedcommodities_set.all()])
        nb_cards += trade.responder_offer.rules.count() + sum([tc.nb_traded_cards for tc in trade.responder_offer.tradedcommodities_set.all()])
        cards_count[trade] = nb_cards

    max_cards = max(cards_count.values())

    if cards_count.values().count(max_cards) == 1: # detect tie
        for trade, nb_cards in cards_count.iteritems():
            if nb_cards == max_cards:
                scoresheet_initiator = None
                scoresheet_responder = None
                for scoresheet in scoresheets:
                    if scoresheet.gameplayer.player == trade.initiator:
                        scoresheet_initiator = scoresheet
                    elif scoresheet.gameplayer.player == trade.responder:
                        scoresheet_responder = scoresheet

                scoresheet_initiator.register_score_from_rule(rulecard, MESSAGE_DETAIL.format(trade.responder.name, trade.closing_date, nb_cards), score = 10)
                scoresheet_responder.register_score_from_rule(rulecard, MESSAGE_DETAIL.format(trade.initiator.name, trade.closing_date, nb_cards), score = 10)

def PIZ14(rulecard, scoresheets):
    """ The player(s) having traded the largest number of toppings (cards given + cards received) during
         the course of the game will earn a 10 points bonus. In case of a tie, each player will earn the bonus. """
    toppings_count = {}
    for scoresheet in scoresheets:
        nb_traded_toppings = 0
        for trade in Trade.objects.filter(Q(initiator = scoresheet.gameplayer.player) | Q(responder = scoresheet.gameplayer.player),
                                          game = scoresheet.gameplayer.game, status = 'ACCEPTED'):
            nb_traded_toppings += sum([tc.nb_traded_cards for tc in trade.initiator_offer.tradedcommodities_set.all()]
                                    + [tc.nb_traded_cards for tc in trade.responder_offer.tradedcommodities_set.all()])
        toppings_count[scoresheet] = nb_traded_toppings

    max_toppings = max(toppings_count.values())
    winners = [scoresheet for scoresheet, nb_traded_toppings in toppings_count.iteritems() if nb_traded_toppings == max_toppings]

    for scoresheet in winners:
        tied = ""
        if len(winners) > 1:
            tied = ", tied with {0}".format(", ".join([player.gameplayer.player.name for player in winners if player != scoresheet]))
        scoresheet.register_score_from_rule(rulecard, 'Your trades have included the largest number of exchanged toppings in the game ({0} toppings{1}). You earn a bonus of 10 point.'.format(max_toppings, tied),
                                            score = 10)