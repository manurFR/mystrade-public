from game.models import RuleInHand, CommodityInHand
from random import shuffle
from scoring.models import Commodity

RULECARDS_PER_PLAYER = 2
COMMODITY_CARDS_PER_PLAYER = 10

class RuleCardDealer(object):
    def add_a_card_to_hand(self, hand, deck):
        """ From this deck, add to the hand a rule that is not already present there """
        rule_index = -1
        while deck[rule_index] in hand:
            rule_index -= 1
            if rule_index < -len(deck):
                # This will be raised if there are no cards in the deck that are not yet in the hand
                raise InappropriateDealingException
        hand.append(deck.pop(rule_index))

class CommodityCardDealer(object):
    def add_a_card_to_hand(self, hand, deck):
        """ From this deck, add to the hand a commodity. Duplicates are ok. """
        hand.append(deck.pop())

def deal_cards(game):
    players = game.players.all()
    nb_players = len(players)
    rules = dispatch_cards(nb_players, RULECARDS_PER_PLAYER, game.rules.all(), RuleCardDealer())
    commodities = dispatch_cards(nb_players, COMMODITY_CARDS_PER_PLAYER,
                                 Commodity.objects.filter(ruleset = game.ruleset), CommodityCardDealer())
    for idx, player in enumerate(players):
        for rulecard in rules[idx]:
            RuleInHand.objects.create(game = game, player = player, rulecard = rulecard, ownership_date = game.start_date)
        for commodity in set(commodities[idx]): # only one record per distinct commodity
            CommodityInHand.objects.create(game = game, player = player, commodity = commodity, nb_cards = commodities[idx].count(commodity))

def dispatch_cards(nb_players, nb_cards_per_player, cards, card_dealer):
    """ A deck of n copies of the cards is prepared, with n chosen so that less than an
         additional complete copy will be needed for everyone to get nb_cards_per_player cards
         (if there are as many players as cards, n = nb_cards_per_player).
        Those cards are actually dealt by the card_dealer object, so that specific rules can
         be implemented here (for example, for rule cards there should be no duplicates in a hand).
        After that, if there are players left without all their intended nb_cards_per_player cards,
         a last copy of all cards is prepared and the appropriate players are dealt a last card.
        This way of dealing ensures that among all selected cards for this game, some players will
         have x copies, some x+1 copies, but no one more than that.
        If the card_dealer object detects a bad dealing of cards (for example, for rule cards a
         player might have to choose among cards (s)he already possess in the deck, which would lead
         to a duplicate), it is the card_dealer's responsibility to raise an
         InappropriateDealingException. It will make this function start the dealing from scratch.
    """
    copies = int(nb_cards_per_player * float(nb_players) / len(cards))

    hands = [[] for _player in range(nb_players)]
    deck = prepare_deck(cards, copies)
    idx = 0
    while len(hands[idx % nb_players]) < nb_cards_per_player:
        try:
            card_dealer.add_a_card_to_hand(hands[idx % nb_players], deck)
            if len(deck) == 0:
                deck = prepare_deck(cards, 1)
            idx += 1
        except InappropriateDealingException: # let's start over, with a recursive call
            return dispatch_cards(nb_players, nb_cards_per_player, cards, card_dealer)
    return hands

def prepare_deck(cards, nb_copies = 1):
    """ Prepare nb_copies copies of each selected card from this game, and shuffle the deck """
    deck = []
    for _i in range(nb_copies):
        deck.extend(cards)
    shuffle(deck)
    return deck

class InappropriateDealingException(Exception):
    pass