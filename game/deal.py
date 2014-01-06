from random import shuffle
from ruleset.models import Commodity
from game.models import RuleInHand, CommodityInHand, GamePlayer
from scoring.card_scoring import Scoresheet, tally_scores
from scoring.models import ScoreFromCommodity


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

MAX_TRIES = 20
MAX_ACCEPTED_SPREAD = 25 # points of difference between highest and lowest initial scores
def deal_cards(game, nb_tries = 0):
    if nb_tries >= MAX_TRIES:
        return False

    try:
        gameplayers = GamePlayer.objects.filter(game = game)
        ruleset_commodities = Commodity.objects.filter(ruleset = game.ruleset)

        rules       = dispatch_cards(gameplayers, game.ruleset.starting_rules,       game.rules.all(),    RuleCardDealer())
        commodities = dispatch_cards(gameplayers, game.ruleset.starting_commodities, ruleset_commodities, CommodityCardDealer())

        # evaluate spread
        scoresheets = prepare_scoresheets(commodities)
        tally_scores(game, scoresheets)
        scores = [scoresheet.total_score for scoresheet in scoresheets]
        # print "try#{0} - min: {1} / max: {2} / diff: {3}".format(nb_tries, min(scores), max(scores), max(scores) - min(scores))
        if max(scores) - min(scores) > MAX_ACCEPTED_SPREAD:
            raise InappropriateDealingException

        for gameplayer, rulecards in rules.iteritems():
            for rulecard in rulecards:
                RuleInHand.objects.create(game = game, player = gameplayer.player, rulecard = rulecard, ownership_date = game.start_date)
        for gameplayer, commodities in commodities.iteritems():
            for commodity in set(commodities): # only one record per distinct commodity
                CommodityInHand.objects.create(game = game, player = gameplayer.player, commodity = commodity, nb_cards = commodities.count(commodity))

        return True
    except InappropriateDealingException:
        return deal_cards(game, nb_tries = nb_tries + 1) # recursive call to try again

def dispatch_cards(gameplayers, nb_cards_per_player, cards, card_dealer):
    """ A deck of n copies of the cards is prepared, with n chosen so that less than an
         additional complete copy will be needed for everyone to get nb_cards_per_player cards
         (if there are as many players as cards, n = nb_cards_per_player).
        Those cards are actually dealt by the card_dealer object, so that specific rules can
         be implemented here (for example, for rule cards there should be no duplicates in a hand).
        After that, if there are players left without all their intended nb_cards_per_player cards,
         a last copy of all cards is prepared and the appropriate players are dealt a last card.
        This way of dealing ensures that among all selected cards for this game, some cards will
         be dealt in n copies, and some in n+1 copies, but no card in less or more than that.
        If the card_dealer object detects a bad dealing of cards (for example, for rule cards the
         deck might only contain cards that a player already possess, which would lead to a duplicate),
         it is the card_dealer's responsibility to raise an InappropriateDealingException.
         It will make this function start the dealing from scratch.
    """
    hands = dict([(gameplayer, []) for gameplayer in gameplayers])

    copies = int(nb_cards_per_player * float(gameplayers.count()) / len(cards))
    deck = prepare_deck(cards, copies)

    for _i in range(nb_cards_per_player):
        for gameplayer, hand in hands.iteritems():
            card_dealer.add_a_card_to_hand(hand, deck)
            if len(deck) == 0:
                deck = prepare_deck(cards, 1)

    # idx = 0
    # while len(hands[idx % nb_players]) < nb_cards_per_player:
    #     card_dealer.add_a_card_to_hand(hands[idx % nb_players], deck)
    #     if len(deck) == 0:
    #         deck = prepare_deck(cards, 1)
    #     idx += 1
    return hands

def prepare_deck(cards, nb_copies = 1):
    """ Prepare nb_copies copies of each selected card from this game, and shuffle the deck """
    deck = []
    for _i in range(nb_copies):
        deck.extend(cards)
    shuffle(deck)
    return deck

def prepare_scoresheets(dealt_commodities):
    scoresheets = []
    for gameplayer, commodities in dealt_commodities.iteritems():
        scores_from_commodity = []
        for commodity in set(commodities):
            scores_from_commodity.append(ScoreFromCommodity(game = gameplayer.game, player = gameplayer.player,
                                                            commodity = commodity,
                                                            nb_submitted_cards = commodities.count(commodity),
                                                            nb_scored_cards = commodities.count(commodity),
                                                            actual_value = commodity.value))
        scoresheets.append(Scoresheet(gameplayer = gameplayer, scores_from_commodity = scores_from_commodity))
    return scoresheets

class InappropriateDealingException(Exception):
    pass