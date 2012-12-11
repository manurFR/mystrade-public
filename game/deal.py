from random import shuffle

def deal_rule_cards(game):
    deck = prepare_rule_deck(game, nb_copies = 2)
    hands = dict((player, []) for player in game.players)
    for player in hands.iterkeys():
        add_a_rule_to_hand(hands[player], deck)

def prepare_rule_deck(game, nb_copies = 1):
    """ Prepare nb_copies copies of each selected rule from this game, and shuffle the deck """ 
    deck = []
    for _i in range(nb_copies):
        deck.extend(rulecard for rulecard in game.rules.all())
    shuffle(deck)
    return deck

def add_a_rule_to_hand(hand, deck):
    """ From this deck, add to the hand a rule that is not already present there """
    rule_index = -1
    while deck[rule_index] in hand:
        rule_index -= 1
        if rule_index < -len(deck):
            # This will be raised if there are no cards in the deck that are not yet in the hand
            raise InappropriateDealingException
    hand.append(deck.pop(rule_index))

class InappropriateDealingException(Exception):
    pass