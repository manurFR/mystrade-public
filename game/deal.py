from random import shuffle
from game.models import RuleInHand

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

def deal_cards(game):
    players = game.players.all()
    nb_players = len(players)
    hands = prepare_hands(nb_players, game.rules.all())
    for idx, player in enumerate(players):
        for rulecard in hands[idx]:
            RuleInHand.objects.create(game = game, player = player, rulecard = rulecard, ownership_date = game.start_date)

def prepare_hands(nb_players, rules, card_dealer = CardDealer()):
    """ A deck of n copies of the rule cards is prepared, with n chosen so that less than an
         additional complete copy will be needed for everyone to get two cards (if there are
         as many players as rule cards, n = 2).
        Those rule cards are dealt so that a player has no duplicate card in his hand.
        After that, if there are players left without both their two rule cards, a last copy of
         all rule cards is prepared and the appropriate players are dealt a last card.
        This way of dealing ensures that among all selected rule cards for this game, some will
         have x copies, some x+1 copies, but no one more than that.
        It might happen occasionally that a player to receive a rule card find only items
         in the deck that (s)he already possess. In this case we start again from the beginning.
    """
    copies = int(2 * float(nb_players) / len(rules))

    hands = [[] for _player in range(nb_players)]
    deck = prepare_rule_deck(rules, copies)
    idx = 0
    while len(hands[idx % nb_players]) < 2:
        try:
            card_dealer.add_a_rule_to_hand(hands[idx % nb_players], deck)
            if len(deck) == 0:
                deck = prepare_rule_deck(rules, 1)
            idx += 1
        except InappropriateDealingException: # let's start over, with a recursive call
            return prepare_hands(nb_players, rules)
    return hands

def prepare_rule_deck(rules, nb_copies = 1):
    """ Prepare nb_copies copies of each selected rule from this game, and shuffle the deck """
    deck = []
    for _i in range(nb_copies):
        deck.extend(rules)
    shuffle(deck)
    return deck

class InappropriateDealingException(Exception):
    pass