from random import shuffle

def deal_rule_cards(game):
    deck = prepare_rule_deck(game)

def prepare_rule_deck(game, nb_copies = 1):
    deck = []
    for _i in range(nb_copies):
        deck.append(rulecard for rulecard in game.rules)
    shuffle(deck)
    return deck