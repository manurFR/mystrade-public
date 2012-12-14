from random import shuffle

class CardDealer(object):
    def add_a_rule_to_hand(self, hand, deck):
        """ From this deck, add to the hand a rule that is not already present there """
        rule_index = -1
        while deck[rule_index] in hand:
            rule_index -= 1
            if rule_index < -len(deck):
                # This will be raised if there are no cards in the deck that are not yet in the hand
                raise InappropriateDealingException
        hand.append(deck.pop(rule_index))

def prepare_hands(game, card_dealer = CardDealer()):
    """ A deck of n copies of the rule cards is prepared, with n chosen so that less than an
         additional complete copy will be needed for everyone to get two cards (if there are
         as many players as rule cards, n = 2).
        Those rule cards are dealt so that a player has no duplicate card in his hand.
        After that, if there are players left without both their two rule cards, a last copy of
         all rule cards is prepared and the appropriate players are dealt a last card.
        This way of dealing ensures that among all selected rule cards for this game, some will
         have x copies, some x+1 copies, and no one more than that.
        It might happen occasionally that the last player to receive a rule card find only items
         in the deck that (s)he already possess. In this case we start again from the beginning.
    """
    nb_players = len(game.players.all())
    copies = int(2 * float(nb_players) / len(game.rules.all()))

    hands = [[] for _player in range(nb_players)]
    deck = prepare_rule_deck(game, copies)
    idx = 0
    while len(hands[idx % nb_players]) < 2:
        try:
            card_dealer.add_a_rule_to_hand(hands[idx % nb_players], deck)
            if len(deck) == 0:
                deck = prepare_rule_deck(game, 1)
            idx += 1
        except InappropriateDealingException: # let's start over, with a recursive call
            return prepare_hands(game)
    return hands

def prepare_rule_deck(game, nb_copies = 1):
    """ Prepare nb_copies copies of each selected rule from this game, and shuffle the deck """
    deck = []
    for _i in range(nb_copies):
        deck.extend(rulecard for rulecard in game.rules.all())
    shuffle(deck)
    return deck

class InappropriateDealingException(Exception):
    pass