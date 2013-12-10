import datetime
from django.test import TestCase
from django.utils.timezone import utc
from model_mommy import mommy
from game.models import Game, CommodityInHand, RuleInHand
from ruleset.models import Ruleset, RuleCard
from scoring.card_scoring import tally_scores
from scoring.tests.commons import _prepare_scoresheet, assertRuleNotApplied, assertRuleApplied, _prepare_hand
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
        assertRuleApplied(scoresheet, rulecard, 'Since your pizza has 11 toppings (more than 10), you lose 5 points.', score = -5)

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

    def test_PIZ13_no_trades_should_not_raise_ValueError(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ13')
        player1, scoresheet1 = _prepare_scoresheet_and_returns_tuple(self.game, "p1", olives = 3, mozzarella = 2)
        player2, scoresheet2 = _prepare_scoresheet_and_returns_tuple(self.game, "p2", pepperoni = 2, pineapple = 1, ham = 1)
        player3, scoresheet3 = _prepare_scoresheet_and_returns_tuple(self.game, "p3", mushrooms = 2, mozzarella = 2)

        try:
            rulecard.perform([scoresheet1, scoresheet2, scoresheet3])
        except ValueError:
            self.fail("PIZ13 for a player without accepted trades should not raise a ValueError")

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

    def test_PIZ15(self):
        """ The cooks who will not have performed a trade with at least 7 different players during the game will
             lose 10 points. Only accepted trades with at least one card (rule or topping) given by each player count. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ15')
        players = []
        scoresheets = []
        rih = []
        for i in range(11):
            player, scoresheet = _prepare_scoresheet_and_returns_tuple(self.game, "p{0}".format(i), olives = 3, mozzarella = 2)
            players.append(player)
            scoresheets.append(scoresheet)
            rih.append(mommy.make(RuleInHand, game = self.game, player = player))

        for i in range(9): # 2 trades with 2 different players for each player 1 to 8, plus one trade including player 0 and one including player 9
            mommy.make(Trade, game = self.game, initiator = players[i], responder = players[i+1], status = 'ACCEPTED',
                       initiator_offer = _prepare_offer(self.game, players[i], [], {'olives': 1}),
                       responder_offer = _prepare_offer(self.game, players[i+1], [], {'mozzarella': 1}),
                       closing_date = utc.localize(datetime.datetime(2013, 11, i+1, 13, 00, 0)))
        for i in range(1, 6): # 5 more different friends to trade with for player 0, but those trades do not include cards, only free informations
            mommy.make(Trade, game = self.game, initiator = players[0], responder = players[i], status = 'ACCEPTED',
                       initiator_offer = mommy.make(Offer, free_information = 'free'),
                       responder_offer = mommy.make(Offer, free_information = 'info'),
                       closing_date = utc.localize(datetime.datetime(2013, 11, 10+i, 14, 00, 0)))
        for i in range(1, 6): # 5 more different friends to trade with for player 1, but those trades were not ACCEPTED
            mommy.make(Trade, game = self.game, initiator = players[1], responder = players[i], status = 'REPLIED',
                       initiator_offer = _prepare_offer(self.game, players[1], [], {'olives': 2}),
                       responder_offer = _prepare_offer(self.game, players[i], [], {'mozzarella': 2}),
                       closing_date = utc.localize(datetime.datetime(2013, 11, 15+i, 15, 00, 0)))
        for i in range(1, 6): # 5 more different friends to trade with for player 2, but the responder did not give any card
            mommy.make(Trade, game = self.game, initiator = players[2], responder = players[i], status = 'ACCEPTED',
                       initiator_offer = _prepare_offer(self.game, players[2], [], {'olives': 2}),
                       responder_offer = mommy.make(Offer, free_information = 'info'),
                       closing_date = utc.localize(datetime.datetime(2013, 11, 20+i, 16, 00, 0)))
        for i in range(1, 6): # 5 more different friends to trade with players 7 and 8, making them both avoiding the loss
            mommy.make(Trade, game = self.game, initiator = players[7], responder = players[i], status = 'ACCEPTED',
                       initiator_offer = _prepare_offer(self.game, players[7], [], {'olives': 2}),
                       responder_offer = _prepare_offer(self.game, players[i], [rih[i]], {}), # only a rulecard, to check they are taken in account
                       closing_date = utc.localize(datetime.datetime(2013, 11, 24+i, 17, 00, 0)))
            mommy.make(Trade, game = self.game, initiator = players[i], responder = players[8], status = 'ACCEPTED',
                       initiator_offer = _prepare_offer(self.game, players[i], [rih[i]], {}),
                       responder_offer = _prepare_offer(self.game, players[8], [], {'mozzarella': 2}),
                       closing_date = utc.localize(datetime.datetime(2013, 11, 24+i, 18, 00, 0)))

        for scoresheet in scoresheets:
            rulecard.perform(scoresheet)

        for i in [0, 9]:
            self.assertEqual(3*2 + 2*3 - 10, scoresheets[i].total_score)
            assertRuleApplied(scoresheets[i], rulecard, 'Since you have performed trades (including one card or more given by each player) with only 1 other player (less than the 7 players required), you lose 10 points.', score = -10)
        for i in range(1, 6):
            self.assertEqual(3*2 + 2*3 - 10, scoresheets[i].total_score)
            assertRuleApplied(scoresheets[i], rulecard, 'Since you have performed trades (including one card or more given by each player) with only 4 different players (less than the 7 players required), you lose 10 points.', score = -10)
        self.assertEqual(3*2 + 2*3 - 10, scoresheets[6].total_score)
        assertRuleApplied(scoresheets[6], rulecard, 'Since you have performed trades (including one card or more given by each player) with only 2 different players (less than the 7 players required), you lose 10 points.', score = -10)

        self.assertEqual(3*2 + 2*3, scoresheets[7].total_score)
        assertRuleNotApplied(scoresheets[7], rulecard)
        self.assertEqual(3*2 + 2*3, scoresheets[8].total_score)
        assertRuleNotApplied(scoresheets[8], rulecard)

        self.assertEqual(3*2 + 2*3 - 10, scoresheets[10].total_score)
        assertRuleApplied(scoresheets[10], rulecard, 'Since you have not performed any trades (including one card or more given by each player) although you were required to do it with at least 7 other players, you lose 10 points.', score = -10)

    def test_PIZ16(self):
        """ The default value of a card is doubled if the card name contains at least once the letter K or Z. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ16')
        scoresheet = _prepare_scoresheet(self.game, "p1", artichoke = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since it contains the letter K, the value of each Artichoke card is doubled.')

        scoresheet = _prepare_scoresheet(self.game, "p1", mozzarella = 1) # doubled only once even if there are 2 Zs
        rulecard.perform(scoresheet)
        self.assertEqual(6, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since it contains the letter Z, the value of each Mozzarella card is doubled.')

        scoresheet = _prepare_scoresheet(self.game, "p1", bacon = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ17(self):
        """ If a topping's name starts with a letter from the last ten of the alphabet, the topping is worth
             2 more points than its default value. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ17')
        scoresheet = _prepare_scoresheet(self.game, "p1", anchovies = 1, peppers = 1, sausage = 1, tuna = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(3 + 2 + 5 + 5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since it starts with a letter from the last ten of the alphabet (Q to Z), each Sausage card is worth two more points than other Meat cards.')
        assertRuleApplied(scoresheet, rulecard, 'Since it starts with a letter from the last ten of the alphabet (Q to Z), each Tuna card is worth two more points than other Fish & Seafood cards.')

    def test_PIZ18(self):
        """ Each Herb [H] card gives a bonus of 2 points to a maximum of two Vegetable [V] cards.
             Each Vegetable card can earn the bonus from one Herb card only. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ18')
        scoresheet = _prepare_scoresheet(self.game, "p1", basil = 2, peppers = 2, olives = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(0 + 2*2 + 2 + 3*2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '2 Herb cards have given a bonus of 2 points each to a total of 3 Vegetable cards in your hand.', score = 6)

        scoresheet = _prepare_scoresheet(self.game, "p1", basil = 1, olives = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(0 + 2 + 2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '1 Herb card have given a bonus of 2 points each to a total of 1 Vegetable card in your hand.', score = 2)

        scoresheet = _prepare_scoresheet(self.game, "p1", basil = 3, peppers = 4, olives = 4)
        rulecard.perform(scoresheet)
        self.assertEqual(0 + 4*2 + 4*2 + 6*2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '3 Herb cards have given a bonus of 2 points each to a total of 6 Vegetable cards in your hand.', score = 12)

        scoresheet = _prepare_scoresheet(self.game, "p1", basil = 1, ham = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(0 + 3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", peppers = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(2*2, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ19(self):
        """ The pizza with the most Herb [H] cards earns a bonus of 10 points.
             In case of a tie, each cook will earn only 3 points. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ19')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 2, basil = 2)
        player2 = _prepare_scoresheet(self.game, "p2", mussels = 4, oregano = 3, garlic = 2)
        player3 = _prepare_scoresheet(self.game, "p3", parmesan = 3, basil = 1, oregano = 1, garlic = 1)
        rulecard.perform([player1, player2, player3])

        self.assertEqual(2*2 + 0, player1.total_score)
        assertRuleNotApplied(player1, rulecard)
        self.assertEqual(4*3 + 0 + 0 + 10, player2.total_score)
        assertRuleApplied(player2, rulecard, 'Your pizza has the most Herb cards from all the players (5 Herb cards). You earn a bonus of 10 points.', score = 10)
        self.assertEqual(3*3 + 0 + 0 + 0, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_PIZ19_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ19')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 2, basil = 4)
        player2 = _prepare_scoresheet(self.game, "p2", mussels = 4, oregano = 2, garlic = 2)
        player3 = _prepare_scoresheet(self.game, "p3", parmesan = 3, basil = 1, oregano = 1, garlic = 2)
        rulecard.perform([player1, player2, player3])

        self.assertEqual(2*2 + 0 + 3, player1.total_score)
        assertRuleApplied(player1, rulecard, 'Your pizza has the most Herb cards from all the players (4 Herb cards, tied with p2, p3). You earn a bonus of 3 points.', score = 3)
        self.assertEqual(4*3 + 0 + 0 + 3, player2.total_score)
        assertRuleApplied(player2, rulecard, 'Your pizza has the most Herb cards from all the players (4 Herb cards, tied with p1, p3). You earn a bonus of 3 points.', score = 3)
        self.assertEqual(3*3 + 0 + 0 + 0 + 3, player3.total_score)
        assertRuleApplied(player3, rulecard, 'Your pizza has the most Herb cards from all the players (4 Herb cards, tied with p1, p2). You earn a bonus of 3 points.', score = 3)

    def test_PIZ20(self):
        """ Mamma Peppino cooked mussels with parmesan for Christmas and eggplant with gorgonzola for Good Friday.
             Each of these pairing will earn you a bonus of 6 points (for at least one card of both topping). Rest In Peace, Mamma. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ20')
        scoresheet = _prepare_scoresheet(self.game, "p1", mussels = 2, parmesan = 3, gorgonzola = 2, eggplant = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 3*3 + 2*3 + 3*2 + 6 + 6, scoresheet.total_score) # only one bonus for each dish
        assertRuleApplied(scoresheet, rulecard, 'Since your pizza includes at least one Mussels card and at least one Parmesan card, you earn a bonus of 6 points.', score = 6)
        assertRuleApplied(scoresheet, rulecard, 'Since your pizza includes at least one Eggplant card and at least one Gorgonzola card, you earn a bonus of 6 points.', score = 6)

        scoresheet = _prepare_scoresheet(self.game, "p1", mussels = 2, eggplant = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 3*2, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_all_rules_pizzaz_together(self):
        for rule in RuleCard.objects.filter(ruleset__id = 3):
            self.game.rules.add(rule)
        gp1 = _prepare_hand(self.game, "p1", peppers = 2, chicken = 2, eggplant = 1, gorgonzola = 1) # PIZ08, PIZ10, PIZ16x2, PIZ20
        gp2 = _prepare_hand(self.game, "p2", ham = 4, garlic = 1, mushrooms = 1) # PIZ04, PIZ08, PIZ09, PIZ10, PIZ12, PIZ18
        gp3 = _prepare_hand(self.game, "p3", capers = 3, mushrooms = 3, sausage = 3, bacon = 1) # PIZ04, PIZ07, PIZ10x3, PIZ17
        gp4 = _prepare_hand(self.game, "p4", bacon = 3, oregano = 1, gorgonzola = 2, artichoke = 1, prosciutto = 3, tomato = 2) # PIZ06, PIZ10x4, PIZ16x2, PIZ17, PIZ18
        gp5 = _prepare_hand(self.game, "p5", anchovies = 1, artichoke = 1, arugula = 1, olives = 1, onions = 1, oregano = 2) # PIZ04, PIZ07, PIZ10, PIZ11x2, PIZ16x3, PIZ18, PIZ19
        gp6 = _prepare_hand(self.game, "p6", mussels = 2, parmesan = 1, olives = 1) # PIZ10, PIZ12, PIZ20

        mommy.make(Trade, game = self.game, initiator = gp2.player, responder = gp6.player, status = 'ACCEPTED',  # PIZ13 & PIZ14 to p2 and p6
                   initiator_offer = _prepare_offer(self.game, gp2.player, [], {'mussels': 2, 'parmesan': 1}),
                   responder_offer = _prepare_offer(self.game, gp6.player, [], {'ham': 4, 'garlic': 1}),
                   closing_date = utc.localize(datetime.datetime(2013, 11, 1, 13, 00, 0)))

        # + everyone loses 10 points with PIZ15

        scoresheets = tally_scores(self.game)
        self.assertEqual(6, len(scoresheets))

        self.assertEqual(0 + 2*6 + 2 + 3*2 + 4 + 6 - 10,                            scoresheets[0].total_score)
        self.assertEqual(4*3 + 0 + 2 + 6 + 4 + 12 + 2 + 10 + 10 - 10,               scoresheets[1].total_score)
        self.assertEqual(3*2 + 3*2 + 3*5 + 3 + 6 + 12 + 3*4 - 10,                   scoresheets[2].total_score)
        self.assertEqual(3*3 + 0 + 2*6 + 4 + 3*3 + 2*4 - 2*5 + 4*4 + 2*2 - 10,      scoresheets[3].total_score)
        self.assertEqual(3 + 4 + 4 + 2 + 4 + 0 + 6 + 12 + 4 + 2*8 + 4*2 + 10 - 10,  scoresheets[4].total_score)
        self.assertEqual(2*3 + 3 + 2 + 4 + 12 + 6 + 10 + 10 - 10,                   scoresheets[5].total_score)

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