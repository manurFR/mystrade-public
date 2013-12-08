import datetime
from django.test import TestCase
from django.utils.timezone import utc
from model_mommy import mommy
from game.models import Game, CommodityInHand, RuleInHand
from ruleset.models import Ruleset, RuleCard
from scoring.tests.commons import _prepare_scoresheet, assertRuleNotApplied, assertRuleApplied
from trade.models import Trade, Offer, TradedCommodities


class PizzazTest(TestCase):
    def setUp(self):
        self.game = mommy.make(Game, ruleset = Ruleset.objects.get(id = 3))

    def test_PIZ04(self):
        """If your pizza contains no Cheese, Don Peppino will curse you but his wife will arrange so that
            you get a bonus of 6 points (damn doctors!)."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ04')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 1, mushrooms = 3, parmesan = 1) # ham: 3 pts, mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 1, mushrooms = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(15, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A pizza with no cheese gives you a bonus of 6 points.', score = 6)

    def test_PIZ06(self):
        """Don Peppino likes his pizza with no more than 10 toppings (cards). Each added topping removes 5 points."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ06')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 6, mushrooms = 5) # ham: 3 pts, mushrooms: 2 pts
        rulecard.perform(scoresheet)
        self.assertEqual(6*3 + 5*2 - 5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since your pizza had 11 toppings (more than 10), you lose 5 points.', score = -5)

    def test_PIZ07(self):
        """ If your pizza has more Vegetable [V] cards than Meat [M], Fish & Seafood [F&S] and Cheese [C] cards combined,
            there is a bonus of 12 points for you."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ07')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 2, mushrooms = 5, parmesan = 2) # ham: 3 pts, mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 5*2 + 2*3 + 12, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'There is more Vegetable cards in your pizza than Meat, Fish & Seafood and Cheese cards combined. You earn a bonus of 12 points.',
                          score = 12)

        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 2, mushrooms = 3, parmesan = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 3*2 + 3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ08(self):
        """ Don Peppino dislikes the following toppings, unless paired with the appropriate ingredient:
            peppers, pineapple and ham. Absolutely no points can be earned from those. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ08')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, parmesan = 2, ham = 1, pineapple = 1, peppers = 1) # mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 2*3 + 0 + 0 + 0, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, parmesan = 2) # mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 2*3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ09(self):
        """ One garlic card makes Don Peppino tolerate all the toppings he usually dislikes. But beware!
            More than one garlic and he'll revert to his usual distastes. """
        rulecardPIZ08 = RuleCard.objects.get(ref_name = 'PIZ08')
        rulecardPIZ09 = RuleCard.objects.get(ref_name = 'PIZ09')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, pineapple = 1, garlic = 1) # mushrooms: 2 pts, pineapple: 2 pts, garlic: 0 pts
        rulecardPIZ08.perform(scoresheet)
        rulecardPIZ09.perform(scoresheet)
        self.assertEqual(3*2 + 2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecardPIZ08, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards should give you no points...')
        assertRuleApplied(scoresheet, rulecardPIZ09, '...but since your pizza contains one garlic, he tolerates them. Phew!')

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, pineapple = 1, garlic = 2) # mushrooms: 2 pts, pineapple: 2 pts, garlic: 0 pts
        rulecardPIZ08.perform(scoresheet)
        rulecardPIZ09.perform(scoresheet)
        self.assertEqual(3*2 + 0, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecardPIZ08, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')
        assertRuleNotApplied(scoresheet, rulecardPIZ09)

    def test_PIZ10(self):
        """ Each topping with at least a double ration (two cards or more) is worth 4 points more. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ10')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 2, ham = 1) # mushrooms: 2 pts, ham: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(2*2 + 3 + 4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Mushrooms gives you a bonus of 4 points.', score = 4)
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and 'Ham' in sfr.detail:
                self.fail("The PIZ10 bonus should not have been given for only one Ham.")

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 4, ham = 2) # mushrooms: 2 pts, ham: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(4*2 + 2*3 + 4 + 4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Mushrooms gives you a bonus of 4 points.', score = 4)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Ham gives you a bonus of 4 points.', score = 4)
        number_of_bonus_for_mushrooms = 0
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and 'Mushrooms' in sfr.detail:
                number_of_bonus_for_mushrooms += 1
        self.assertEqual(1, number_of_bonus_for_mushrooms, "The PIZ10 bonus for a double ration of mushrooms should have been given only once (actual: {0}x).".format(number_of_bonus_for_mushrooms))

    def test_PIZ11(self):
        """ A pizza with at least three different toppings whose name begins with the same letter brings
            a bonus of 8 points. (Different letters will add up.) """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ11')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 1, mussels = 1, mozzarella = 1,
                                                          parmesan = 1, pineapple = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(2 + 3 + 3 + 3 + 2 + 8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '3 different toppings starting by the letter M (Mozzarella, Mushrooms, Mussels) give you a bonus of 8 points.', score = 8)

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, mussels = 1, mozzarella = 1, # mushrooms: 2 pts, mussels: 3 pts, mozza: 3 pts
                                                          parmesan = 1, pepperoni = 2, pineapple = 1, prosciutto = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 3 + 3 + 3 + 2*3 + 2 + 3 + 8 + 8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '3 different toppings starting by the letter M (Mozzarella, Mushrooms, Mussels) give you a bonus of 8 points.', score = 8)
        assertRuleApplied(scoresheet, rulecard, '4 different toppings starting by the letter P (Parmesan, Pepperoni, Pineapple, Prosciutto) give you a bonus of 8 points.', score = 8)

    def test_PIZ12(self):
        """ The cook whose pizza has the smallest number of different toppings will earn a bonus of 12 points.
            In case of a tie, each player will earn the bonus. (Multiple copies of the same topping count for one.) """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ12')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 5, ham = 1)
        player2 = _prepare_scoresheet(self.game, "p2", mushrooms = 1, mussels = 1, mozzarella = 2)
        player3 = _prepare_scoresheet(self.game, "p3", parmesan = 1, pepperoni = 2, pineapple = 1, prosciutto = 1)
        rulecard.perform([player1, player2, player3])
        self.assertEqual(5*2 + 3 + 12, player1.total_score)
        assertRuleApplied(player1, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)
        self.assertEqual(2 + 3 + 2*3, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(3 + 2*3 + 2 + 3, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_PIZ12_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ12')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 5, ham = 1)
        player2 = _prepare_scoresheet(self.game, "p2", mushrooms = 1, mussels = 1, mozzarella = 2)
        player3 = _prepare_scoresheet(self.game, "p3", pepperoni = 2, pineapple = 1)
        rulecard.perform([player1, player2, player3])
        self.assertEqual(5*2 + 3 + 12, player1.total_score)
        assertRuleApplied(player1, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)
        self.assertEqual(2 + 3 + 2*3, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(2*3 + 2 + 12, player3.total_score)
        assertRuleApplied(player3, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)

    def test_PIZ13(self):
        """The trade featuring the largest number of cards of the game (rules and toppings given by both players
            combined) will give a bonus of 10 points to both players involved. Only accepted trades count.
            In case of a tie between two or more trades, no one earns the bonus."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ13')
        player1, scoresheet1 = _prepare_scoresheet_and_returns_tuple(self.game, "p1", mushrooms = 5, ham = 1)
        player2, scoresheet2 = _prepare_scoresheet_and_returns_tuple(self.game, "p2", olives = 3, mozzarella = 3, pepperoni = 2, pineapple = 1)
        player3, scoresheet3 = _prepare_scoresheet_and_returns_tuple(self.game, "p3", mushrooms = 2, mozzarella = 2, pineapple = 4)

        rih1 = mommy.make(RuleInHand, game = self.game, player = player1, rulecard = rulecard)
        rih2 = mommy.make(RuleInHand, game = self.game, player = player2, rulecard = rulecard)
        rih3 = mommy.make(RuleInHand, game = self.game, player = player3, rulecard = rulecard)

        mommy.make(Trade, game = self.game, initiator = player1, responder = player2, status = 'REPLIED',  # 12 cards included, but trade not ACEPTED
                    initiator_offer = _prepare_offer(self.game, player1, [rih1], {'mushrooms': 5, 'ham': 1}),
                    responder_offer = _prepare_offer(self.game, player2, [rih2], {'olives': 3, 'mozzarella': 3}))
        mommy.make(Trade, game = self.game, initiator = player2, responder = player3, status = 'ACCEPTED',  # 8 cards included, including 2 rulecards
                    initiator_offer = _prepare_offer(self.game, player2, [rih3], {'mushrooms': 2, 'mozzarella': 2}), # (see below)
                    responder_offer = _prepare_offer(self.game, player3, [rih2], {'pepperoni': 1, 'pineapple': 1}),
                    closing_date = utc.localize(datetime.datetime(2013, 11, 21, 15, 25, 0)))
        mommy.make(Trade, game = self.game, initiator = player1, responder = player3, status = 'ACCEPTED',  # 7 cards included, only commodities
                    initiator_offer = _prepare_offer(self.game, player1, [], {'mushrooms': 3}),         # (to test that rulecards are included)
                    responder_offer = _prepare_offer(self.game, player3, [], {'pineapple': 4}),
                    closing_date = utc.localize(datetime.datetime(2013, 11, 22, 16, 25, 0)))

        rulecard.perform([scoresheet1, scoresheet2, scoresheet3])

        self.assertEqual(5*2 + 3, scoresheet1.total_score)
        assertRuleNotApplied(scoresheet1, rulecard)
        self.assertEqual(3*2 + 3*3 + 2*3 + 2 + 10, scoresheet2.total_score)
        assertRuleApplied(scoresheet2, rulecard, 'Your trade with p3 (accepted on 2013/11/21 03:25 PM) included 8 cards. ' +
                                             'It is the largest number of cards exchanged in a trade. You both earn a bonus of 10 points.',
                                             score = 10)
        self.assertEqual(2*2 + 2*3 + 4*2 + 10, scoresheet3.total_score)
        assertRuleApplied(scoresheet3, rulecard, 'Your trade with p2 (accepted on 2013/11/21 03:25 PM) included 8 cards. ' +
                                             'It is the largest number of cards exchanged in a trade. You both earn a bonus of 10 points.',
                                             score = 10)

    def test_PIZ13_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ13')
        player1, scoresheet1 = _prepare_scoresheet_and_returns_tuple(self.game, "p1", olives = 3, mozzarella = 2)
        player2, scoresheet2 = _prepare_scoresheet_and_returns_tuple(self.game, "p2", pepperoni = 2, pineapple = 1, ham = 1)
        player3, scoresheet3 = _prepare_scoresheet_and_returns_tuple(self.game, "p3", mushrooms = 2, mozzarella = 2)

        mommy.make(Trade, game = self.game, initiator = player1, responder = player2, status = 'ACCEPTED',  # 8 cards
                    initiator_offer = _prepare_offer(self.game, player1, [], {'mushrooms': 2, 'ham': 1}),
                    responder_offer = _prepare_offer(self.game, player2, [], {'olives': 3, 'mozzarella': 2}),
                    closing_date = utc.localize(datetime.datetime(2013, 11, 18, 15, 35, 0)))
        mommy.make(Trade, game = self.game, initiator = player2, responder = player3, status = 'ACCEPTED',  # 8 cards too
                    initiator_offer = _prepare_offer(self.game, player2, [], {'mushrooms': 2, 'mozzarella': 2}),
                    responder_offer = _prepare_offer(self.game, player3, [], {'pepperoni': 2, 'pineapple': 2}),
                    closing_date = utc.localize(datetime.datetime(2013, 11, 21, 12, 12, 0)))

        rulecard.perform([scoresheet1, scoresheet2, scoresheet3])
        self.assertEqual(3*2 + 2*3, scoresheet1.total_score)
        assertRuleNotApplied(scoresheet1, rulecard)
        self.assertEqual(2*3 + 2 + 3, scoresheet2.total_score)
        assertRuleNotApplied(scoresheet2, rulecard)
        self.assertEqual(2*2 + 2*3, scoresheet3.total_score)
        assertRuleNotApplied(scoresheet3, rulecard)

    def test_PIZ14(self):
        """ The player(s) having traded the largest number of toppings (cards given + cards received) during
             the course of the game will earn a 10 points bonus. In case of a tie, each player will earn the bonus. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ14')
        player1, scoresheet1 = _prepare_scoresheet_and_returns_tuple(self.game, "p1", olives = 3, mozzarella = 2)
        player2, scoresheet2 = _prepare_scoresheet_and_returns_tuple(self.game, "p2", pepperoni = 2, pineapple = 1, ham = 1)
        player3, scoresheet3 = _prepare_scoresheet_and_returns_tuple(self.game, "p3", mushrooms = 2, mozzarella = 2)

        rih1, rih2 = mommy.make(RuleInHand, game = self.game, player = player1, _quantity = 2)

        # p2 has 17 cards exchanged, p1 only 16 because we don't take into account the rulecards and the DECLINED trade
        mommy.make(Trade, game = self.game, initiator = player1, responder = player2, status = 'ACCEPTED',      # 9 cards for p1 & p2
                   initiator_offer = _prepare_offer(self.game, player1, [], {'mushrooms': 2, 'ham': 1}),
                   responder_offer = _prepare_offer(self.game, player2, [], {'olives': 3, 'mozzarella': 3}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 1, 13, 00, 0)))
        mommy.make(Trade, game = self.game, initiator = player2, responder = player3, status = 'ACCEPTED',
                   initiator_offer = _prepare_offer(self.game, player2, [], {'mushrooms': 2, 'mozzarella': 2}), # 8 cards for p2 & p3
                   responder_offer = _prepare_offer(self.game, player3, [], {'pepperoni': 2, 'pineapple': 2}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 2, 13, 00, 0)))
        mommy.make(Trade, game = self.game, initiator = player1, responder = player3, status = 'ACCEPTED',
                   initiator_offer = _prepare_offer(self.game, player1, [rih1, rih2], {'pineapple': 3, 'artichoke': 2}),
                   responder_offer = _prepare_offer(self.game, player3, [], {'olives': 2}),                     # 7 cards for p1 & p3
                   closing_date = utc.localize(datetime.datetime(2013, 11, 3, 13, 00, 0)))
        mommy.make(Trade, game = self.game, initiator = player1, responder = player3, status = 'DECLINED',
                   initiator_offer = _prepare_offer(self.game, player1, [], {'mozzarella': 2}),
                   responder_offer = _prepare_offer(self.game, player3, [], {'ham': 1}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 4, 13, 00, 0)))

        rulecard.perform([scoresheet1, scoresheet2, scoresheet3])

        self.assertEqual(3*2 + 2*3, scoresheet1.total_score)
        assertRuleNotApplied(scoresheet1, rulecard)
        self.assertEqual(2*3 + 2 + 3 + 10, scoresheet2.total_score)
        assertRuleApplied(scoresheet2, rulecard, 'Your trades have included the largest number of exchanged toppings in the game (17 toppings). You earn a bonus of 10 point.',
                          score = 10)
        self.assertEqual(2*2 + 2*3, scoresheet3.total_score)
        assertRuleNotApplied(scoresheet3, rulecard)

    def test_PIZ14_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ14')
        player1, scoresheet1 = _prepare_scoresheet_and_returns_tuple(self.game, "p1", olives = 3, mozzarella = 2)
        player2, scoresheet2 = _prepare_scoresheet_and_returns_tuple(self.game, "p2", pepperoni = 2, pineapple = 1, ham = 1)
        player3, scoresheet3 = _prepare_scoresheet_and_returns_tuple(self.game, "p3", mushrooms = 2, mozzarella = 2)
        player4, scoresheet4 = _prepare_scoresheet_and_returns_tuple(self.game, "p4", artichoke = 2)

        mommy.make(Trade, game = self.game, initiator = player1, responder = player2, status = 'ACCEPTED',  # 9 cards for p1 & p2
                   initiator_offer = _prepare_offer(self.game, player1, [], {'mushrooms': 2, 'ham': 1}),
                   responder_offer = _prepare_offer(self.game, player2, [], {'olives': 3, 'mozzarella': 3}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 1, 13, 00, 0)))
        mommy.make(Trade, game = self.game, initiator = player3, responder = player4, status = 'ACCEPTED',
                   initiator_offer = _prepare_offer(self.game, player3, [], {'artichoke': 2}),              # 5 cards for p3 & p4
                   responder_offer = _prepare_offer(self.game, player4, [], {'pepperoni': 3}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 2, 13, 00, 0)))

        rulecard.perform([scoresheet1, scoresheet2, scoresheet3, scoresheet4])

        self.assertEqual(3*2 + 2*3 + 10, scoresheet1.total_score)
        assertRuleApplied(scoresheet1, rulecard, 'Your trades have included the largest number of exchanged toppings in the game (9 toppings, tied with p2). You earn a bonus of 10 point.',
                          score = 10)
        self.assertEqual(2*3 + 2 + 3 + 10, scoresheet2.total_score)
        assertRuleApplied(scoresheet2, rulecard, 'Your trades have included the largest number of exchanged toppings in the game (9 toppings, tied with p1). You earn a bonus of 10 point.',
                          score = 10)
        self.assertEqual(2*2 + 2*3, scoresheet3.total_score)
        assertRuleNotApplied(scoresheet3, rulecard)
        self.assertEqual(2*2, scoresheet4.total_score)
        assertRuleNotApplied(scoresheet4, rulecard)

def _prepare_scoresheet_and_returns_tuple(game, player, **commodities):
    scoresheet = _prepare_scoresheet(game, player, **commodities)
    player = scoresheet.gameplayer.player
    return player, scoresheet

def _prepare_offer(game, player, rules, commodities):
    offer = mommy.make(Offer, rules = rules)
    for name, nb_traded_cards in commodities.iteritems():
        try:
            cih = CommodityInHand.objects.get(game = game, player = player, commodity__name__iexact = name)
        except CommodityInHand.DoesNotExist:
            cih = mommy.make(CommodityInHand, game = game, player = player, commodity__name = name, nb_cards = 0)
        tc = mommy.make(TradedCommodities, offer = offer, commodityinhand = cih, nb_traded_cards = nb_traded_cards)
        offer.tradedcommodities_set.add(tc)
    return offer

