from django.contrib.auth.models import User
from django.test import TestCase
from ruleset.models import RuleCard, Commodity
from scoring.card_scoring import tally_scores, Scoresheet
from scoring.haggle import HAG04, HAG05, HAG06, HAG07, HAG08, HAG09, HAG10,\
HAG11, HAG12, HAG13, HAG14, HAG15

class ViewsTest(TestCase):
    def setUp(self):
        self.testUser = User.objects.create_user('test', 'test@aaa.com', 'test')
        self.client.login(username = 'test', password = 'test')

    def test_display_rulecards(self):
        response = self.client.get("/scoring/")
        self.assertTemplateUsed(response, 'scoring/choose_rulecards.html')

    def test_choose_some_rulecards(self):
        response = self.client.post("/scoring/",
                                    {'rulecards-TOTAL_FORMS': 15, 'rulecards-INITIAL_FORMS': 15,
                                     'rulecards-0-card_id': 1, 'rulecards-0-selected_rule': 'on',
                                     'rulecards-1-card_id': 2, 'rulecards-1-selected_rule': 'on',
                                     'rulecards-2-card_id': 3, 'rulecards-2-selected_rule': 'on',
                                     'rulecards-3-card_id': 4,
                                     'rulecards-4-card_id': 5,
                                     'rulecards-5-card_id': 6,
                                     'rulecards-6-card_id': 7,
                                     'rulecards-7-card_id': 8,
                                     'rulecards-8-card_id': 9,
                                     'rulecards-9-card_id': 10, 'rulecards-9-selected_rule': 'on',
                                     'rulecards-10-card_id': 11,
                                     'rulecards-11-card_id': 12,
                                     'rulecards-12-card_id': 13, 'rulecards-12-selected_rule': 'on',
                                     'rulecards-13-card_id': 14,
                                     'rulecards-14-card_id': 15,
                                     'hands-TOTAL_FORMS': 0, 'hands-INITIAL_FORMS': 0
                                    })

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'scoring/result.html')
        self.assertEqual(['1', '2', '3', '10', '13'], [card.public_name for card in response.context['rules']])

    def test_mandatory_cards(self):
        response = self.client.post("/scoring/",
                                    {'rulecards-TOTAL_FORMS': 15, 'rulecards-INITIAL_FORMS': 15,
                                     'rulecards-0-card_id': 1,
                                     'rulecards-1-card_id': 2,
                                     'rulecards-2-card_id': 3,
                                     'rulecards-3-card_id': 4,
                                     'rulecards-4-card_id': 5,
                                     'rulecards-5-card_id': 6,
                                     'rulecards-6-card_id': 7,
                                     'rulecards-7-card_id': 8,
                                     'rulecards-8-card_id': 9,
                                     'rulecards-9-card_id': 10,
                                     'rulecards-10-card_id': 11,
                                     'rulecards-11-card_id': 12,
                                     'rulecards-12-card_id': 13,
                                     'rulecards-13-card_id': 14,
                                     'rulecards-14-card_id': 15,
                                     'hands-TOTAL_FORMS': 0, 'hands-INITIAL_FORMS': 0
                                    })

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'scoring/result.html')
        self.assertEqual(['1', '2', '3'], [card.public_name for card in response.context['rules']])

    def test_specify_hands(self):
        response = self.client.post("/scoring/",
                                    {'rulecards-TOTAL_FORMS': 0, 'rulecards-INITIAL_FORMS': 0,
                                     'hands-TOTAL_FORMS': 2, 'hands-INITIAL_FORMS': 2,
                                     'hands-0-yellow': 3,
                                     'hands-0-blue': 0,
                                     'hands-0-orange': 8,
                                     'hands-1-yellow': 1,
                                     'hands-1-blue': 2,
                                     'hands-1-red': 3,
                                     'hands-1-orange': 4,
                                     'hands-1-white': 5
                                    })

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'scoring/result.html')
        self.assertContains(response, "Yellow : 3, Blue : 0, Red : 0, Orange : 8, White : 0")
        self.assertContains(response, "Yellow : 1, Blue : 2, Red : 3, Orange : 4, White : 5")

    def test_specify_hands_only_empty_fields(self):
        response = self.client.post("/scoring/",
                                    {'rulecards-TOTAL_FORMS': 0, 'rulecards-INITIAL_FORMS': 0,
                                     'hands-TOTAL_FORMS': 1, 'hands-INITIAL_FORMS': 1,
                                     'hands-0-yellow': '',
                                     'hands-0-blue': '',
                                     'hands-0-red': '',
                                     'hands-0-orange': '',
                                     'hands-0-white': ''
                                    })

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'scoring/result.html')
        self.assertContains(response, "Yellow : 0, Blue : 0, Red : 0, Orange : 0, White : 0")

class ScoringTest(TestCase):
    def test_tally_scores(self):
        haggle_all_rulecards = RuleCard.objects.filter(ruleset__id = 1)
        hands = [_prepare_hand(yellow = 2, blue = 1, red = 3, orange = 3, white = 4),
                 _prepare_hand(yellow = 3, blue = 5, red = 3, orange = 0, white = 1),
                 _prepare_hand(yellow = 3, blue = 1, red = 1, orange = 7, white = 1),
                 _prepare_hand(yellow = 0, blue = 3, red = 4, orange = 2, white = 1)]
        scores, scoresheets = tally_scores(hands, [rule for rule in haggle_all_rulecards])
        self.assertEqual(31, scores[0])
        self.assertEqual(32, scores[1])
        self.assertEqual(12, scores[2])
        self.assertEqual(110, scores[3])
        self.assertEqual(4, len(scoresheets))

    def test_tally_scores_rules_subset(self):
        haggle_rulecards = RuleCard.objects.filter(ruleset__id = 1, public_name__in = ['4', '8', '10', '12', '13'])
        hands = [_prepare_hand(yellow = 4, blue = 2, red = 2, orange = 3, white = 2),
                 _prepare_hand(yellow = 2, blue = 5, red = 0, orange = 0, white = 5),
                 _prepare_hand(yellow = 1, blue = 1, red = 1, orange = 7, white = 0),
                 _prepare_hand(yellow = 0, blue = 3, red = 4, orange = 2, white = 1)]
        scores, scoresheets = tally_scores(hands, [rule for rule in haggle_rulecards])
        self.assertEqual(82, scores[0])
        self.assertEqual(12, scores[1])
        self.assertEqual(34, scores[2])
        self.assertEqual(43, scores[3])
        self.assertEqual(4, len(scoresheets))
        self.assertEqual([{ 'name': 'Yellow', 'handed_cards': 4, 'scored_cards': 4, 'actual_value': 1, 'score': 4 },
                          { 'name': 'Blue',   'handed_cards': 2, 'scored_cards': 2, 'actual_value': 2, 'score': 4 },
                          { 'name': 'Red',    'handed_cards': 2, 'scored_cards': 2, 'actual_value': 3, 'score': 6 },
                          { 'name': 'Orange', 'handed_cards': 3, 'scored_cards': 3, 'actual_value': 4, 'score': 12 },
                          { 'name': 'White',  'handed_cards': 2, 'scored_cards': 2, 'actual_value': 5, 'score': 10 }],
                         scoresheets[0].commodities)
        self.assertEqual([{'cause': 'HAG10', 'detail': '(10) A set of five different colors gives a bonus of 10 points.', 'score': 10 },
                          {'cause': 'HAG10', 'detail': '(10) A set of five different colors gives a bonus of 10 points.', 'score': 10 },
                          {'cause': 'HAG13', 'detail': '(13) A pair of yellow cards doubles the value of one white card.', 'score': 5 },
                          {'cause': 'HAG13', 'detail': '(13) A pair of yellow cards doubles the value of one white card.', 'score': 5 },
                          {'cause': 'HAG08', 'detail': '(8) Having the most yellow cards (4 cards) gives a bonus of 4x4 points.', 'score': 16 }],
                         scoresheets[0].extra )

    def test_calculate_score(self):
        class MockScoresheet(Scoresheet):
            def __init__(self, hand = None):
                self._commodities = [{ 'name': 'Blue', 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 2 },
                                    { 'name': 'Red' , 'handed_cards': 4, 'scored_cards': 3, 'actual_value': 1 }]
                self._extra = [{'cause': 'HELLO', 'score': -5} , {'cause': 'WORLD', 'score': None}]
        scoresheet = MockScoresheet()
        self.assertEqual(2, scoresheet.calculate_score())
        self.assertEqual([{ 'name': 'Blue', 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 2, 'score': 4 },
                          { 'name': 'Red' , 'handed_cards': 4, 'scored_cards': 3, 'actual_value': 1, 'score': 3 }], 
                         scoresheet.commodities)
    
    def test_Scoresheet_init(self):
        """Yellow = 1 / Blue = 2 / Red = 3 / Orange = 4 / White = 5
           This is a test of the 3 mandatory rulecards for the initial values.
        """
        scoresheet = _prepare_scoresheet(1, 1, 1, 1, 1)
        self.assertEqual([{'name': 'Yellow', 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 1 },
                          {'name': 'Blue',   'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          {'name': 'Red',    'handed_cards': 1, 'scored_cards': 1, 'actual_value': 3 },
                          {'name': 'Orange', 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 4 },
                          {'name': 'White',  'handed_cards': 1, 'scored_cards': 1, 'actual_value': 5 }],
                         scoresheet.commodities)
        self.assertEqual(15, scoresheet.calculate_score())

        scoresheet = _prepare_scoresheet(blue = 1, red = 2, orange = 3)
        self.assertEqual([{'name': 'Yellow', 'handed_cards': 0, 'scored_cards': 0, 'actual_value': 1 },
                          {'name': 'Blue',   'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          {'name': 'Red',    'handed_cards': 2, 'scored_cards': 2, 'actual_value': 3 },
                          {'name': 'Orange', 'handed_cards': 3, 'scored_cards': 3, 'actual_value': 4 },
                          {'name': 'White',  'handed_cards': 0, 'scored_cards': 0, 'actual_value': 5 }],
                         scoresheet.commodities)
        self.assertEqual(20, scoresheet.calculate_score())

    def test_register_rule(self):
        scoresheet = _prepare_scoresheet(blue = 1)
        scoresheet.register_rule('rule_name', 'test', 10)
        self.assertEqual([{'cause': 'rule_name', 'detail': 'test', 'score': 10}], scoresheet.extra)

    def test_register_rule_no_score(self):
        scoresheet = _prepare_scoresheet(blue = 1)
        scoresheet.register_rule('HAG04', 'test')
        self.assertEqual([{'cause': 'HAG04', 'detail': 'test', 'score': None}], scoresheet.extra)

class HaggleTest(TestCase):

    def test_haggle_HAG04(self):
        """If a player has more than three white cards, all of his/her white cards lose their value."""
        scoresheet = _prepare_scoresheet(white = 3)
        HAG04(scoresheet)
        self.assertEqual(15, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG04')

        scoresheet = _prepare_scoresheet(white = 4)
        HAG04(scoresheet)
        self.assertEqual(0, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG04', '(4) Since there are 4 white cards (more than three), their value is set to zero.')
    
    def test_haggle_HAG05(self):
        """"A player can score only as many as orange cards as he/she has blue cards."""
        scoresheet = _prepare_scoresheet(blue = 3, orange = 3)
        HAG05(scoresheet)
        self.assertEqual(18, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG05')

        scoresheet = _prepare_scoresheet(blue = 2, orange = 3)
        HAG05(scoresheet)
        self.assertEqual(12, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG05', '(5) Since there are 2 blue card(s), only 2 orange card(s) score.')

    def test_haggle_HAG06(self):
        """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
        player1 = _prepare_scoresheet(blue = 5)
        player2 = _prepare_scoresheet(blue = 6, orange = 1)
        player3 = _prepare_scoresheet(yellow = 4, blue = 2, white = 4)
        players = [player1, player2, player3]
        HAG06(players)
        self.assertEqual(3, len(players))
        self.assertEqual(10-10, players[0].calculate_score())
        self.assertRuleApplied(players[0], 'HAG06', '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(16-10, players[1].calculate_score())
        self.assertRuleApplied(players[1], 'HAG06', '(6) Since player #1 has 5 blue cards, 10 points are deducted.', -10)
        self.assertEqual(28-20, players[2].calculate_score())
        self.assertRuleApplied(players[2], 'HAG06', '(6) Since player #1 has 5 blue cards, 10 points are deducted.', -10)
        self.assertRuleApplied(players[2], 'HAG06', '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)

    def test_haggle_HAG07(self):
        """A set of three red cards protects you from one set of five blue cards."""
        player1 = _prepare_scoresheet(blue = 5)
        player2 = _prepare_scoresheet(blue = 6, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, blue = 2, red = 6)
        HAG06([player1, player2, player3])
        HAG07(player1)
        HAG07(player2)
        HAG07(player3)
        self.assertEqual(10-10, player1.calculate_score())
        self.assertRuleApplied(player1, 'HAG06', '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(21, player2.calculate_score())
        self.assertRuleApplied(player2, 'HAG06', '(6) Since player #1 has 5 blue cards, 10 points should have been deducted...')
        self.assertRuleApplied(player2, 'HAG07', '(7) ...but a set of three red cards cancels that penalty.')
        self.assertEqual(24, player3.calculate_score())
        self.assertRuleApplied(player3, 'HAG06', '(6) Since player #1 has 5 blue cards, 10 points should have been deducted...')
        self.assertRuleApplied(player3, 'HAG06', '(6) Since player #2 has 6 blue cards, 10 points should have been deducted...')
        self.assertRuleApplied(player3, 'HAG07', '(7) ...but a set of three red cards cancels that penalty.', times = 2)
        
    def test_haggle_HAG08(self):
        """The player with the most yellow cards gets a bonus of the number of those cards squared. 
           If two or more players tie for most yellow, the bonus is calculated instead for the player 
           with the next highest number of yellows.
        """
        player1 = _prepare_scoresheet(yellow = 5)
        player2 = _prepare_scoresheet(yellow = 3, red = 3)
        player3 = _prepare_scoresheet(orange = 2)
        players = [player1, player2, player3]
        HAG08(players)
        self.assertEqual(3, len(players))
        self.assertEqual(5+(5**2), players[0].calculate_score())
        self.assertRuleApplied(players[0], 'HAG08', '(8) Having the most yellow cards (5 cards) gives a bonus of 5x5 points.', 5**2)
        self.assertEqual(12, players[1].calculate_score())
        self.assertEqual(8, players[2].calculate_score())

    def test_haggle_HAG08_tie(self):
        player1 = _prepare_scoresheet(yellow = 3, blue = 1) 
        player2 = _prepare_scoresheet(yellow = 3, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = [player1, player2, player3]
        HAG08(players)
        self.assertEqual(3, len(players))
        self.assertEqual(5, players[0].calculate_score())
        self.assertRuleNotApplied(players[0], 'HAG08')
        self.assertEqual(12, players[1].calculate_score())
        self.assertRuleNotApplied(players[1], 'HAG08')
        self.assertEqual(10+(2**2), players[2].calculate_score())
        self.assertRuleApplied(players[2], 'HAG08', '(8) Having the most yellow cards (2 cards) gives a bonus of 2x2 points.', 2**2)

    def test_haggle_HAG09(self):
        """If a player hands in seven or more cards of the same color, 
           for each of these colors 10 points are deducted from his/her score.
        """
        scoresheet = _prepare_scoresheet(yellow = 6, blue = 3, white = 1)
        HAG09(scoresheet)
        self.assertEqual(17, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG09')

        scoresheet = _prepare_scoresheet(yellow = 7, blue = 3, white = 1)
        HAG09(scoresheet)
        self.assertEqual(8, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG09', '(9) Since 7 yellow cards where handed in (seven or more), 10 points are deducted.', -10)

        scoresheet = _prepare_scoresheet(yellow = 7, blue = 8, white = 1)
        HAG09(scoresheet)
        self.assertEqual(8, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG09', '(9) Since 7 yellow cards where handed in (seven or more), 10 points are deducted.', -10)
        self.assertRuleApplied(scoresheet, 'HAG09', '(9) Since 8 blue cards where handed in (seven or more), 10 points are deducted.', -10)

    def test_haggle_HAG10(self):
        """Each set of five different colors gives a bonus of 10 points."""
        scoresheet = _prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1)
        HAG10(scoresheet)
        self.assertEqual(20, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG10')

        scoresheet = _prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1, white = 1)
        HAG10(scoresheet)
        self.assertEqual(35, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG10', '(10) A set of five different colors gives a bonus of 10 points.', 10)

        scoresheet = _prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 3, white = 3)
        HAG10(scoresheet)
        self.assertEqual(63, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG10', '(10) A set of five different colors gives a bonus of 10 points.', 10, times = 2)

    def test_haggle_HAG11(self):
        """If a \"pyramid\" is handed in with no other cards, the value of the hand is doubled. 
           A pyramid consists of four cards of one color, three cards of a second color, 
           two cards of a third, and one card of a fourth color.
        """
        scoresheet = _prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1)
        HAG11(scoresheet)
        self.assertEqual(20*2, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG11', '(11) A pyramid of 4 yellow cards, 3 blue cards, 2 red cards, 1 orange card and no other card doubles the score.', 20)

        scoresheet = _prepare_scoresheet(yellow = 1, blue = 2, orange = 3, white = 4)
        HAG11(scoresheet)
        self.assertEqual(37*2, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG11', '(11) A pyramid of 4 white cards, 3 orange cards, 2 blue cards, 1 yellow card and no other card doubles the score.', 37)

        scoresheet = _prepare_scoresheet(yellow = 1, blue = 2, red = 1, orange = 3, white = 4)
        HAG11(scoresheet)
        self.assertEqual(40, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG11')

    def test_haggle_HAG12(self):
        """The player with the most red cards double their value.
           In case of a tie, no player collects the extra value.
        """
        player1 = _prepare_scoresheet(yellow = 3, red = 4)
        player2 = _prepare_scoresheet(blue = 1, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = [player1, player2, player3]
        HAG12(players)
        self.assertEqual(3, len(players))
        self.assertEqual(15+12, player1.calculate_score())
        self.assertRuleApplied(player1, 'HAG12', '(12) Having the most red cards (4 cards) doubles their value.', 12)
        self.assertEqual(11, player2.calculate_score())
        self.assertRuleNotApplied(player2, 'HAG12')
        self.assertEqual(10, player3.calculate_score())
        self.assertRuleNotApplied(player3, 'HAG12')

    def test_haggle_HAG12_tie(self):
        player1 = _prepare_scoresheet(yellow = 3, red = 3)
        player2 = _prepare_scoresheet(blue = 1, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = [player1, player2, player3]
        HAG12(players)
        self.assertEqual(3, len(players))
        self.assertEqual(12, player1.calculate_score())
        self.assertRuleNotApplied(player1, 'HAG12')
        self.assertEqual(11, player2.calculate_score())
        self.assertRuleNotApplied(player2, 'HAG12')
        self.assertEqual(10, player3.calculate_score())
        self.assertRuleNotApplied(player3, 'HAG12')

    def test_haggle_HAG13(self):
        """Each set of two yellow cards doubles the value of one white card."""
        scoresheet = _prepare_scoresheet(white = 3)
        HAG13(scoresheet)
        self.assertEqual(15, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG13')

        scoresheet = _prepare_scoresheet(yellow = 1, white = 3)
        HAG13(scoresheet)
        self.assertEqual(16, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG13')

        scoresheet = _prepare_scoresheet(yellow = 2, white = 3)
        HAG13(scoresheet)
        self.assertEqual(17+5, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG13', '(13) A pair of yellow cards doubles the value of one white card.', 5)

        scoresheet = _prepare_scoresheet(yellow = 6, white = 3)
        HAG13(scoresheet)
        self.assertEqual(21+3*5, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG13', '(13) A pair of yellow cards doubles the value of one white card.', 5, times = 3)

        scoresheet = _prepare_scoresheet(yellow = 8, white = 3)
        HAG13(scoresheet)
        self.assertEqual(23+3*5, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG13', '(13) A pair of yellow cards doubles the value of one white card.', 5, times = 3)

    def test_haggle_HAG14(self):
        """Each set of three blue cards quadruples the value of one orange card."""
        scoresheet = _prepare_scoresheet(orange = 2)
        HAG14(scoresheet)
        self.assertEqual(8, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG14')

        scoresheet = _prepare_scoresheet(blue = 2, orange = 2)
        HAG14(scoresheet)
        self.assertEqual(12, scoresheet.calculate_score())
        self.assertRuleNotApplied(scoresheet, 'HAG14')

        scoresheet = _prepare_scoresheet(blue = 3, orange = 2)
        HAG14(scoresheet)
        self.assertEqual(14+12, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG14', '(14) A set of three blue cards quadruples the value of one orange card.', 12)

        scoresheet = _prepare_scoresheet(blue = 6, orange = 2)
        HAG14(scoresheet)
        self.assertEqual(20+24, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG14', '(14) A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

        scoresheet = _prepare_scoresheet(blue = 9, orange = 2)
        HAG14(scoresheet)
        self.assertEqual(26+24, scoresheet.calculate_score())
        self.assertRuleApplied(scoresheet, 'HAG14', '(14) A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

    def test_haggle_HAG15(self):
        """No more than thirteen cards in a hand can be scored. 
           If more are handed in, the excess will be removed at random.
        """
        scoresheet = _prepare_scoresheet(5, 5, 5, 5, 15)
        HAG15(scoresheet)
        total_scored_cards = sum(commodity['scored_cards'] for commodity in scoresheet.commodities)
        self.assertEqual(13, total_scored_cards)
        self.assertEqual(1, len(scoresheet.extra))
        extra = scoresheet.extra[0]
        self.assertEqual('HAG15', extra['cause'])
        self.assertTrue(extra['detail'].startswith('(15) Since 35 cards had to be scored, 22 have been discarded'))

    def assertRuleApplied(self, scoresheet, rule, detail = '', score = None, times = 1):
        for _i in range(times):
            self.assertIn({'cause': rule, 'detail': detail, 'score': score}, scoresheet.extra)
            scoresheet.extra.remove({'cause': rule, 'detail': detail, 'score': score})

    def assertRuleNotApplied(self, scoresheet, rule):
        for item in scoresheet.extra:
            self.assertNotEqual(rule, item['cause'])

def _prepare_hand(yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
    return { Commodity.objects.get(ruleset = 1, name ='Yellow') : yellow,
             Commodity.objects.get(ruleset = 1, name ='Blue') : blue,
             Commodity.objects.get(ruleset = 1, name ='Red') : red,
             Commodity.objects.get(ruleset = 1, name ='Orange') : orange,
             Commodity.objects.get(ruleset = 1, name ='White') : white }

def _prepare_scoresheet(yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
    return Scoresheet(_prepare_hand(yellow, blue, red, orange, white))