"""
    Rule card scoring resolution for ruleset "Pizzaz!"
"""
from math import ceil
from django.db.models import Q
from trade.models import Trade


def PIZ04(rulecard, scoresheet):
    """ If your pizza contains no Cheese, Don Peppino will curse you but his wife will arrange so
        that you get a bonus of 6 points (damn doctors!).  """
    if scoresheet.nb_scored_cards_from_categories('Cheese') == 0:
        scoresheet.register_score_from_rule(rulecard, u'A pizza with no cheese gives you a bonus of 6 points.', score = 6)

def PIZ06(rulecard, scoresheet):
    """Don Peppino likes his pizza with no more than 10 toppings (cards). Each added topping removes 5 points."""
    total_scored_cards = 0
    for sfc in scoresheet.scores_from_commodity:
        total_scored_cards += sfc.nb_scored_cards
    if total_scored_cards > 10:
        removed_points = (total_scored_cards - 10) * 5
        scoresheet.register_score_from_rule(rulecard, u'Since your pizza has {0} toppings (more than 10), you lose {1} points.'.format(total_scored_cards, removed_points),
                                            score = -removed_points)

def PIZ07(rulecard, scoresheet):
    """If you pizza has more Vegetable [V] cards than Meat [M], Fish & Seafood [F&S] and Cheese [C] cards combined,
        there is a bonus of 12 points for you."""
    vegetables = scoresheet.nb_scored_cards_from_categories('Vegetable')
    proteins = scoresheet.nb_scored_cards_from_categories('Meat', 'Fish & Seafood', 'Cheese')
    if vegetables > proteins:
        scoresheet.register_score_from_rule(rulecard, u'There is more Vegetable cards in your pizza than Meat, Fish & Seafood and Cheese cards combined. You earn a bonus of 12 points.',
                                            score = 12)

def PIZ08(rulecard, scoresheet):
    """ Don Peppino dislikes the following toppings, unless paired with the appropriate ingredient:
        peppers, pineapple and ham. Absolutely no points can be earned from those. """
    if scoresheet.nb_scored_cards('Peppers') + scoresheet.nb_scored_cards('Pineapple') + scoresheet.nb_scored_cards('Ham') > 0:
        scoresheet.register_score_from_rule(rulecard, u'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')
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
                scoresheet.register_score_from_rule(rulecard, u'...but since your pizza contains one garlic, he tolerates them. Phew!')
                scoresheet.set_nb_scored_cards('Peppers', nb_scored_cards = scoresheet.score_for_commodity('Peppers').nb_submitted_cards)
                scoresheet.set_nb_scored_cards('Pineapple', nb_scored_cards = scoresheet.score_for_commodity('Pineapple').nb_submitted_cards)
                scoresheet.set_nb_scored_cards('Ham', nb_scored_cards = scoresheet.score_for_commodity('Ham').nb_submitted_cards)
            break

def PIZ10(rulecard, scoresheet):
    """ Each topping with at least a double ration (two cards or more) is worth 4 points more. """
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_scored_cards > 1:
            scoresheet.register_score_from_rule(rulecard, u'A double ration of {0} gives you a bonus of 4 points.'.format(sfc.commodity.name), score = 4)

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
            scoresheet.register_score_from_rule(rulecard, u'{0} different toppings starting by the letter {1} ({2}) give you a bonus of 8 points.'
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
            player.register_score_from_rule(rulecard, u'You have the smallest number of different toppings ({0} toppings) of all the players. You earn a bonus of 12 points.'.format(min_toppings),
                                            score = 12)

def PIZ13(rulecard, scoresheets):
    """The trade featuring the largest number of cards of the game (rules and toppings given by both players
        combined) will give a bonus of 10 points to both players involved. Only accepted trades count.
        In case of a tie between two or more trades, no one earns the bonus.

        # Global rulecard #
    """
    MESSAGE_DETAIL = u'Your trade with {0} (accepted on {1:%Y/%m/%d %I:%M %p}) included {2} cards. It is the largest number of cards exchanged in a trade. You both earn a bonus of 10 points.'

    cards_count = {}
    for trade in Trade.objects.filter(game = scoresheets[0].gameplayer.game, status = 'ACCEPTED'):
        cards_count[trade] = trade.initiator_offer.total_traded_cards + trade.responder_offer.total_traded_cards

    if len(cards_count) == 0:
        return

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
    """  The player(s) having traded the largest number of rule cards (given + received) during the course of
          the game will earn a 10 points bonus. In case of a tie, each player will earn the bonus.

        # Global rulecard #
    """
    rulecards_count = {}
    for scoresheet in scoresheets:
        nb_traded_rulecards= 0
        for trade in Trade.objects.filter(Q(initiator = scoresheet.gameplayer.player) | Q(responder = scoresheet.gameplayer.player),
                                          game = scoresheet.gameplayer.game, status = 'ACCEPTED'):
            nb_traded_rulecards += len(trade.initiator_offer.rules.all()) + len(trade.responder_offer.rules.all())
        rulecards_count[scoresheet] = nb_traded_rulecards

    max_rulecards = max(rulecards_count.values())
    winners = [scoresheet for scoresheet, nb_traded_rulecards in rulecards_count.iteritems() if nb_traded_rulecards == max_rulecards]

    for scoresheet in winners:
        tied = ""
        if len(winners) > 1:
            tied = u", tied with {0}".format(", ".join([player.gameplayer.player.name for player in winners if player != scoresheet]))
        scoresheet.register_score_from_rule(rulecard, u'Your trades have included the largest number of exchanged rule cards in the game ({0} cards{1}). You earn a bonus of 10 point.'.format(max_rulecards, tied),
                                            score = 10)

def PIZ15(rulecard, scoresheet):
    """ The cooks who will not have performed a trade with at least 7 different players during the game will
         lose 10 points. Only accepted trades with at least one card (rule or topping) given by each player count. """
    traders = set()
    for trade in Trade.objects.filter(game = scoresheet.gameplayer.game, status = 'ACCEPTED', initiator = scoresheet.gameplayer.player):
        if trade.initiator_offer.total_traded_cards > 0 and trade.responder_offer.total_traded_cards > 0:
            traders.add(trade.responder)
    for trade in Trade.objects.filter(game = scoresheet.gameplayer.game, status = 'ACCEPTED', responder = scoresheet.gameplayer.player):
        if trade.initiator_offer.total_traded_cards > 0 and trade.responder_offer.total_traded_cards > 0:
            traders.add(trade.initiator)

    if len(traders) == 0:
        scoresheet.register_score_from_rule(rulecard, u'Since you have not performed any trades (including one card or more given by each player) although you were required to do it with at least 7 other players, you lose 10 points.',
                                            score = -10)
    elif len(traders) == 1:
        scoresheet.register_score_from_rule(rulecard, u'Since you have performed trades (including one card or more given by each player) with only 1 other player (less than the 7 players required), you lose 10 points.',
                                            score = -10)
    elif len(traders) < 7:
        scoresheet.register_score_from_rule(rulecard, u'Since you have performed trades (including one card or more given by each player) with only {0} different players (less than the 7 players required), you lose 10 points.'.format(len(traders)),
                                            score = -10)

def PIZ16(rulecard, scoresheet):
    """ The default value of a card is doubled if the card name contains at least once the letter K or Z. """
    for sfc in scoresheet.scores_from_commodity:
        if 'k' in sfc.commodity.name.lower():
            sfc.actual_value *= 2
            scoresheet.register_score_from_rule(rulecard, u'Since it contains the letter K, the value of each {0} card is doubled.'.format(sfc.commodity.name))
        elif 'z' in sfc.commodity.name.lower():
            sfc.actual_value *= 2
            scoresheet.register_score_from_rule(rulecard, u'Since it contains the letter Z, the value of each {0} card is doubled.'.format(sfc.commodity.name))

def PIZ17(rulecard, scoresheet):
    """ If a topping's name starts with a letter from the last ten of the alphabet, the topping is worth
         2 more points than its default value. """
    for sfc in scoresheet.scores_from_commodity:
        if ord('z') - ord(sfc.commodity.name.lower()[0:1]) < 10:
            sfc.actual_value += 2
            scoresheet.register_score_from_rule(rulecard, u'Since it starts with a letter from the last ten of the alphabet (Q to Z), each {0} card is worth two more points than other {1} cards.'
                                                          .format(sfc.commodity.name, sfc.commodity.category))

def PIZ18(rulecard, scoresheet):
    """ Each Herb [H] card gives a bonus of 2 points to a maximum of two Vegetable [V] cards.
         Each Vegetable card can earn the bonus from one Herb card only. """
    herbs = scoresheet.nb_scored_cards_from_categories('Herb')
    vegetables = scoresheet.nb_scored_cards_from_categories('Vegetable')
    if herbs and vegetables:
        if herbs * 2 < vegetables: # more vegetables than we can attribute the bonus to : limit the number of vegetables that will earn it
            vegetables = herbs * 2
        elif herbs * 2 > vegetables: # less vegetables than the largest number we can attribute the bonus to : limit the number of herbs that are used to give the bonus
            herbs = int(ceil(float(vegetables) / 2))

        scoresheet.register_score_from_rule(rulecard, u'{0} Herb card{1} have given a bonus of 2 points each to a total of {2} Vegetable card{3} in your hand.'
                                                      .format(herbs, 's' if herbs > 1 else '', vegetables, 's' if vegetables > 1 else ''), score = vegetables * 2)

def PIZ19(rulecard, scoresheets):
    """ The pizza with the most Herb [H] cards earns a bonus of 10 points.
         In case of a tie, each cook will earn only 3 points.

        # Global rulecard #
    """
    herbs_count = dict((player, player.nb_scored_cards_from_categories('Herb')) for player in scoresheets)

    max_herbs = max(herbs_count.values())
    winners = sorted([scoresheet for scoresheet, nb_herbs in herbs_count.iteritems() if nb_herbs == max_herbs],
                     key = lambda scoresheet: scoresheet.gameplayer.player.name.lower())

    for scoresheet in winners:
        bonus = 10
        tied = ""
        if len(winners) > 1:
            bonus = 3
            tied = u", tied with {0}".format(", ".join([player.gameplayer.player.name for player in winners if player != scoresheet]))
        scoresheet.register_score_from_rule(rulecard, u'Your pizza has the most Herb cards from all the players ({0} Herb cards{1}). You earn a bonus of {2} points.'
                                                      .format(max_herbs, tied, bonus), score = bonus)

def PIZ20(rulecard, scoresheet):
    """ Mamma Peppino cooked mussels with parmesan for Christmas and eggplant with gorgonzola for Good Friday.
         Each of these pairing will earn you a bonus of 6 points (for at least one card of both topping). Rest In Peace, Mamma. """
    if scoresheet.nb_scored_cards('Mussels') > 0 and scoresheet.nb_scored_cards('Parmesan') > 0:
        scoresheet.register_score_from_rule(rulecard, u'Since your pizza includes at least one Mussels card and at least one Parmesan card, you earn a bonus of 6 points.',
                                            score = 6)
    if scoresheet.nb_scored_cards('Eggplant') > 0 and scoresheet.nb_scored_cards('Gorgonzola') > 0:
        scoresheet.register_score_from_rule(rulecard, u'Since your pizza includes at least one Eggplant card and at least one Gorgonzola card, you earn a bonus of 6 points.',
                                            score = 6)