from django.contrib.auth.models import User
from django.test import TestCase
from scoring.card_scoring import tally_scores, calculate_player_score, \
    _hand_to_scoresheet, register_rule
from scoring.haggle import HAG04, HAG05, HAG06, HAG07, HAG08, HAG09, HAG10, \
    HAG11, HAG12, HAG13, HAG14, HAG15
from scoring.models import Ruleset, RuleCard, Commodity

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
        self.assertContains(response, "Player : 1 [Yellow : 3 | Blue : 0 | Red : 0 | Orange : 8 | White : 0]")
        self.assertContains(response, "Player : 2 [Yellow : 1 | Blue : 2 | Red : 3 | Orange : 4 | White : 5]")

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
        self.assertContains(response, "Player : 1 [Yellow : 0 | Blue : 0 | Red : 0 | Orange : 0 | White : 0]")

class ScoringTest(TestCase):
    def test_tally_scores(self):
        haggle_ruleset = Ruleset.objects.get(pk = 1)
        haggle_all_rulecards = RuleCard.objects.filter(ruleset = haggle_ruleset)
        hands = [_prepare_hand(yellow = 2, blue = 1, red = 3, orange = 3, white = 4),
                 _prepare_hand(yellow = 3, blue = 5, red = 3, orange = 0, white = 1),
                 _prepare_hand(yellow = 3, blue = 1, red = 1, orange = 7, white = 1),
                 _prepare_hand(yellow = 0, blue = 3, red = 4, orange = 2, white = 1)]
        scores = tally_scores(hands, haggle_ruleset, [rule for rule in haggle_all_rulecards])
        self.assertEqual(31, scores[0])
        self.assertEqual(32, scores[1])
        self.assertEqual(12, scores[2])
        self.assertEqual(110, scores[3])

    def test_tally_scores_rules_subset(self):
        haggle_ruleset = Ruleset.objects.get(pk = 1)
        haggle_rulecards = RuleCard.objects.filter(ruleset = haggle_ruleset, public_name__in = ['4', '8', '10', '12', '13'])
        hands = [_prepare_hand(yellow = 4, blue = 2, red = 2, orange = 3, white = 2),
                 _prepare_hand(yellow = 2, blue = 5, red = 0, orange = 0, white = 5),
                 _prepare_hand(yellow = 1, blue = 1, red = 1, orange = 7, white = 0),
                 _prepare_hand(yellow = 0, blue = 3, red = 4, orange = 2, white = 1)]
        scores = tally_scores(hands, haggle_ruleset, [rule for rule in haggle_rulecards])
        self.assertEqual(82, scores[0])
        self.assertEqual(12, scores[1])
        self.assertEqual(34, scores[2])
        self.assertEqual(43, scores[3])

    def test_calculate_player_score(self):
        scoresheet = {'Blue': { 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 2 },
                      'Red' : { 'handed_cards': 4, 'scored_cards': 3, 'actual_value': 1 },
                      'extra': [ {'cause': 'HELLO', 'score': -5} , {'cause': 'WORLD', 'score': None} ] }
        self.assertEqual(2, calculate_player_score(scoresheet))
    
    def test_hand_to_scoresheet(self):
        """Yellow = 1 / Blue = 2 / Red = 3 / Orange = 4 / White = 5
           This is a test of the 3 mandatory rulecards for the initial values.
        """
        scoresheet = _prepare_scoresheet(1, 1, 1, 1, 1)
        self.assertEqual({'Yellow' : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 1 },
                          'Blue'   : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          'Red'    : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 3 },
                          'Orange' : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 4 },
                          'White'  : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 5 },
                          'extra'  : [] },
                         scoresheet)
        self.assertEqual(15, calculate_player_score(scoresheet))

        scoresheet = _prepare_scoresheet(blue = 1, red = 2, orange = 3)
        self.assertEqual({'Yellow' : { 'handed_cards': 0, 'scored_cards': 0, 'actual_value': 1 },
                          'Blue'   : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          'Red'    : { 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 3 },
                          'Orange' : { 'handed_cards': 3, 'scored_cards': 3, 'actual_value': 4 },
                          'White'  : { 'handed_cards': 0, 'scored_cards': 0, 'actual_value': 5 },
                          'extra'  : [] },
                         scoresheet)
        self.assertEqual(20, calculate_player_score(scoresheet))

    def test_register_rule(self):
        scoresheet = _prepare_scoresheet(blue = 1)
        scoresheet = register_rule(scoresheet, 'RUL04', 'test', 10)
        self.assertIn('extra', scoresheet)
        self.assertEqual([{'cause': 'RUL04', 'detail': 'test', 'score': 10}], scoresheet['extra'])

    def test_register_rule_no_score(self):
        scoresheet = _prepare_scoresheet(blue = 1)
        scoresheet = register_rule(scoresheet, 'DUMMY', 'test')
        self.assertIn('extra', scoresheet)
        self.assertEqual([{'cause': 'DUMMY', 'detail': 'test', 'score': None}], scoresheet['extra'])

class HaggleTest(TestCase):        

    def test_haggle_HAG04(self):
        """If a player has more than three white cards, all of his/her white cards lose their value."""
        scoresheet = HAG04(_prepare_scoresheet(white = 3))
        self.assertEqual(15, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG04')

        scoresheet = HAG04(_prepare_scoresheet(white = 4))
        self.assertEqual(0,  calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG04', 'Since there are 4 white cards (more than three), their value is set to zero.')
    
    def test_haggle_HAG05(self):
        """"A player can score only as many as orange cards as he/she has blue cards."""
        scoresheet = HAG05(_prepare_scoresheet(blue = 3, orange = 3))
        self.assertEqual(18, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG05')

        scoresheet = HAG05(_prepare_scoresheet(blue = 2, orange = 3))
        self.assertEqual(12, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG05', 'Since there are 2 blue card(s), only 2 orange card(s) score.')

    def test_haggle_HAG06(self):
        """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
        player1 = _prepare_scoresheet(blue = 5)
        player2 = _prepare_scoresheet(blue = 6, orange = 1)
        player3 = _prepare_scoresheet(yellow = 4, blue = 2, white = 4)
        players = HAG06([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(10-10, calculate_player_score(players[0]))
        self.assertRuleApplied(players[0], 'HAG06', 'Since player #1 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(16-10, calculate_player_score(players[1]))
        self.assertRuleApplied(players[1], 'HAG06', 'Since player #0 has 5 blue cards, 10 points are deducted.', -10)
        self.assertEqual(28-20, calculate_player_score(players[2]))
        self.assertRuleApplied(players[2], 'HAG06', 'Since player #0 has 5 blue cards, 10 points are deducted.', -10)
        self.assertRuleApplied(players[2], 'HAG06', 'Since player #1 has 6 blue cards, 10 points are deducted.', -10)

    def test_haggle_HAG07(self):
        """A set of three red cards protects you from one set of five blue cards."""
        player1 = _prepare_scoresheet(blue = 5)
        player2 = _prepare_scoresheet(blue = 6, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, blue = 2, red = 6)
        players = HAG06([player1, player2, player3])
        player1 = HAG07(players[0])
        player2 = HAG07(players[1])
        player3 = HAG07(players[2])
        self.assertEqual(10-10, calculate_player_score(player1))
        self.assertRuleApplied(player1, 'HAG06', 'Since player #1 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(21, calculate_player_score(player2))
        self.assertRuleApplied(player2, 'HAG06', 'Since player #0 has 5 blue cards, 10 points should have been deducted...', 0)
        self.assertRuleApplied(player2, 'HAG07', '...but a set of three red cards cancels that penalty.')
        self.assertEqual(24, calculate_player_score(player3))
        self.assertRuleApplied(player3, 'HAG06', 'Since player #0 has 5 blue cards, 10 points should have been deducted...', 0)
        self.assertRuleApplied(player3, 'HAG06', 'Since player #1 has 6 blue cards, 10 points should have been deducted...', 0)
        self.assertRuleApplied(player3, 'HAG07', '...but a set of three red cards cancels that penalty.', times = 2)
        
    def test_haggle_HAG08(self):
        """The player with the most yellow cards gets a bonus of the number of those cards squared. 
           If two or more players tie for most yellow, the bonus is calculated instead for the player 
           with the next highest number of yellows.
        """
        player1 = _prepare_scoresheet(yellow = 5)
        player2 = _prepare_scoresheet(yellow = 3, red = 3)
        player3 = _prepare_scoresheet(orange = 2)
        players = HAG08([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(5+(5**2), calculate_player_score(players[0]))
        self.assertRuleApplied(players[0], 'HAG08', 'Having the most yellow cards (5 cards) gives a bonus of 5x5 points.', 5**2)
        self.assertEqual(12, calculate_player_score(players[1]))
        self.assertEqual(8, calculate_player_score(players[2]))

    def test_haggle_HAG08_tie(self):
        player1 = _prepare_scoresheet(yellow = 3, blue = 1) 
        player2 = _prepare_scoresheet(yellow = 3, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG08([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(5, calculate_player_score(players[0]))
        self.assertRuleNotApplied(players[0], 'HAG08')
        self.assertEqual(12, calculate_player_score(players[1]))
        self.assertRuleNotApplied(players[1], 'HAG08')
        self.assertEqual(10+(2**2), calculate_player_score(players[2]))
        self.assertRuleApplied(players[2], 'HAG08', 'Having the most yellow cards (2 cards) gives a bonus of 2x2 points.', 2**2)

    def test_haggle_HAG09(self):
        """If a player hands in seven or more cards of the same color, 
           for each of these colors 10 points are deducted from his/her score.
        """
        scoresheet = HAG09(_prepare_scoresheet(yellow = 6, blue = 3, white = 1))
        self.assertEqual(17, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG09')

        scoresheet = HAG09(_prepare_scoresheet(yellow = 7, blue = 3, white = 1))
        self.assertEqual(8, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG09', 'Since 7 yellow cards where handed in, 10 points are deducted.', -10)

        scoresheet = HAG09(_prepare_scoresheet(yellow = 7, blue = 8, white = 1))
        self.assertEqual(8, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG09', 'Since 7 yellow cards where handed in, 10 points are deducted.', -10)
        self.assertRuleApplied(scoresheet, 'HAG09', 'Since 8 blue cards where handed in, 10 points are deducted.', -10)

    def test_haggle_HAG10(self):
        """Each set of five different colors gives a bonus of 10 points."""
        scoresheet = HAG10(_prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1))
        self.assertEqual(20, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG10')

        scoresheet = HAG10(_prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1, white = 1))
        self.assertEqual(35, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG10', 'A set of five different colors gives a bonus.', 10)

        scoresheet = HAG10(_prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 3, white = 3))
        self.assertEqual(63, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG10', 'A set of five different colors gives a bonus.', 10, times = 2)

    def test_haggle_HAG11(self):
        """If a \"pyramid\" is handed in with no other cards, the value of the hand is doubled. 
           A pyramid consists of four cards of one color, three cards of a second color, 
           two cards of a third, and one card of a fourth color.
        """
        scoresheet = HAG11(_prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1))
        self.assertEqual(20*2, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG11', 'A pyramid of 4 yellow cards, 3 blue cards, 2 red cards, 1 orange card and no other card doubles the score.', 20)

        scoresheet = HAG11(_prepare_scoresheet(yellow = 1, blue = 2, orange = 3, white = 4))
        self.assertEqual(37*2, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG11', 'A pyramid of 4 white cards, 3 orange cards, 2 blue cards, 1 yellow card and no other card doubles the score.', 37)

        scoresheet = HAG11(_prepare_scoresheet(yellow = 1, blue = 2, red = 1, orange = 3, white = 4))
        self.assertEqual(40, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG11')

    def test_haggle_HAG12(self):
        """The player with the most red cards double their value.
           In case of a tie, no player collects the extra value.
        """
        player1 = _prepare_scoresheet(yellow = 3, red = 4)
        player2 = _prepare_scoresheet(blue = 1, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG12([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(15+12, calculate_player_score(players[0]))
        self.assertRuleApplied(players[0], 'HAG12', 'Having the most red cards (4 cards) doubles their value.', 12)
        self.assertEqual(11, calculate_player_score(players[1]))
        self.assertRuleNotApplied(players[1], 'HAG12')
        self.assertEqual(10, calculate_player_score(players[2]))
        self.assertRuleNotApplied(players[2], 'HAG12')

    def test_haggle_HAG12_tie(self):
        player1 = _prepare_scoresheet(yellow = 3, red = 3)
        player2 = _prepare_scoresheet(blue = 1, red = 3)
        player3 = _prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG12([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(12, calculate_player_score(players[0]))
        self.assertRuleNotApplied(players[0], 'HAG12')
        self.assertEqual(11, calculate_player_score(players[1]))
        self.assertRuleNotApplied(players[1], 'HAG12')
        self.assertEqual(10, calculate_player_score(players[2]))
        self.assertRuleNotApplied(players[2], 'HAG12')

    def test_haggle_HAG13(self):
        """Each set of two yellow cards doubles the value of one white card."""
        scoresheet = HAG13(_prepare_scoresheet(white = 3))
        self.assertEqual(15, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG13')

        scoresheet = HAG13(_prepare_scoresheet(yellow = 1, white = 3))
        self.assertEqual(16, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG13')

        scoresheet = HAG13(_prepare_scoresheet(yellow = 2, white = 3))
        self.assertEqual(17+5, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG13', 'A pair of yellow cards doubles the value of one white card.', 5)

        scoresheet = HAG13(_prepare_scoresheet(yellow = 6, white = 3))
        self.assertEqual(21+3*5, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG13', 'A pair of yellow cards doubles the value of one white card.', 5, times = 3)

        scoresheet = HAG13(_prepare_scoresheet(yellow = 8, white = 3))
        self.assertEqual(23+3*5, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG13', 'A pair of yellow cards doubles the value of one white card.', 5, times = 3)

    def test_haggle_HAG14(self):
        """Each set of three blue cards quadruples the value of one orange card."""
        scoresheet = HAG14(_prepare_scoresheet(orange = 2))
        self.assertEqual(8, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG14')

        scoresheet = HAG14(_prepare_scoresheet(blue = 2, orange = 2))
        self.assertEqual(12, calculate_player_score(scoresheet))
        self.assertRuleNotApplied(scoresheet, 'HAG14')

        scoresheet = HAG14(_prepare_scoresheet(blue = 3, orange = 2))
        self.assertEqual(14+12, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG14', 'A set of three blue cards quadruples the value of one orange card.', 12)

        scoresheet = HAG14(_prepare_scoresheet(blue = 6, orange = 2))
        self.assertEqual(20+24, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG14', 'A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

        scoresheet = HAG14(_prepare_scoresheet(blue = 9, orange = 2))
        self.assertEqual(26+24, calculate_player_score(scoresheet))
        self.assertRuleApplied(scoresheet, 'HAG14', 'A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

    def test_haggle_HAG15(self):
        """No more than thirteen cards in a hand can be scored. 
           If more are handed in, the excess will be removed at random.
        """
        scoresheet = HAG15(_prepare_scoresheet(5, 5, 5, 5, 15))
        total_scored_cards = 0
        for color, cards in scoresheet.iteritems():
            if color != 'extra':
                total_scored_cards += cards['scored_cards']
        self.assertEqual(13, total_scored_cards)
        self.assertIn('extra', scoresheet)
        self.assertEqual(1, len(scoresheet['extra']))
        extra = scoresheet['extra'][0]
        self.assertEqual('HAG15', extra['cause'])
        self.assertTrue(extra['detail'].startswith('Since 35 cards had to be scored, 22 have been discarded'))

    def assertRuleApplied(self, scoresheet, rule, detail = '', score = None, times = 1):
        self.assertIn('extra', scoresheet)
        extra = scoresheet['extra']
        for _i in range(times):
            self.assertIn({'cause': rule, 'detail': detail, 'score': score}, extra)
            extra.remove({'cause': rule, 'detail': detail, 'score': score})

    def assertRuleNotApplied(self, scoresheet, rule):
        self.assertIn('extra', scoresheet)
        for item in scoresheet['extra']:
            self.assertNotEqual(rule, item['cause'])

def _prepare_hand(yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
    return { Commodity.objects.get(ruleset = 1, name ='Yellow') : yellow,
             Commodity.objects.get(ruleset = 1, name ='Blue') : blue,
             Commodity.objects.get(ruleset = 1, name ='Red') : red,
             Commodity.objects.get(ruleset = 1, name ='Orange') : orange,
             Commodity.objects.get(ruleset = 1, name ='White') : white }

def _prepare_scoresheet(yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
    return _hand_to_scoresheet(_prepare_hand(yellow, blue, red, orange, white))