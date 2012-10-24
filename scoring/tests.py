from django.contrib.auth.models import User
from django.test import TestCase
from scoring.card_scoring import calculate_score, setup_scoresheet, HAG04, HAG05, \
    HAG09, HAG10, HAG13, HAG14, HAG15, HAG11, HAG06, HAG07, HAG08, HAG12
from scoring.models import Commodity

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
                                     'commodities-TOTAL_FORMS': 0, 'commodities-INITIAL_FORMS': 0
                                    })

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "1 : Orange cards have a basic value of 4 and are equal to a red card and a yellow card.")
        self.assertContains(response, "2 : White cards have the highest basic value and are equal to a red card and a blue card.")
        self.assertContains(response, "3 : Blue cards have a basic value twice that of yellow and half that of orange.")
        self.assertContains(response, "10 : Each set of five different colors gives a bonus of 10 points.")
        self.assertContains(response, "13 : Each set of two yellow cards doubles the value of one white card.")

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
                                     'commodities-TOTAL_FORMS': 0, 'commodities-INITIAL_FORMS': 0
                                    })

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "1 : Orange cards have a basic value of 4 and are equal to a red card and a yellow card.")
        self.assertContains(response, "2 : White cards have the highest basic value and are equal to a red card and a blue card.")
        self.assertContains(response, "3 : Blue cards have a basic value twice that of yellow and half that of orange.")

    def test_specify_commodities(self):
        response = self.client.post("/scoring/",
                                    {'rulecards-TOTAL_FORMS': 0, 'rulecards-INITIAL_FORMS': 0,
                                     'commodities-TOTAL_FORMS': 5, 'commodities-INITIAL_FORMS': 5,
                                     'commodities-0-commodity_id': 1, 'commodities-0-nb_cards': 3,
                                     'commodities-1-commodity_id': 2,
                                     'commodities-2-commodity_id': 3, 'commodities-2-nb_cards': 0,
                                     'commodities-3-commodity_id': 4, 'commodities-3-nb_cards': 8,
                                     'commodities-4-commodity_id': 5,
                                    })

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Yellow : 3");
        self.assertContains(response, "Blue : 0");
        self.assertContains(response, "Red : 0");
        self.assertContains(response, "Orange : 8");
        self.assertContains(response, "White : 0");

class ScoringTest(TestCase):
    def test_calculate_score(self):
        scoresheet = {'Blue': { 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 2 },
                      'Red' : { 'handed_cards': 4, 'scored_cards': 3, 'actual_value': 1 },
                      'extra': [ {'score': 5} , {'score': -10} ] }
        self.assertEqual(2, calculate_score(scoresheet))
    
    def test_setup_scoresheet(self):
        """Yellow = 1 / Blue = 2 / Red = 3 / Orange = 4 / White = 5
           This is a test of the 3 mandatory rulecards for the initial values.
        """
        scoresheet = self._prepare_scoresheet(1, 1, 1, 1, 1)
        self.assertEqual({'Yellow' : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 1 },
                          'Blue'   : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          'Red'    : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 3 },
                          'Orange' : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 4 },
                          'White'  : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 5 },
                          'extra'  : [] },
                         scoresheet)
        self.assertEqual(15, calculate_score(scoresheet))

        scoresheet = self._prepare_scoresheet(blue = 1, red = 2, orange = 3)
        self.assertEqual({'Yellow' : { 'handed_cards': 0, 'scored_cards': 0, 'actual_value': 1 },
                          'Blue'   : { 'handed_cards': 1, 'scored_cards': 1, 'actual_value': 2 },
                          'Red'    : { 'handed_cards': 2, 'scored_cards': 2, 'actual_value': 3 },
                          'Orange' : { 'handed_cards': 3, 'scored_cards': 3, 'actual_value': 4 },
                          'White'  : { 'handed_cards': 0, 'scored_cards': 0, 'actual_value': 5 },
                          'extra'  : [] },
                         scoresheet)
        self.assertEqual(20, calculate_score(scoresheet))

    def test_haggle_HAG04(self):
        """If a player has more than three white cards, all of his/her white cards lose their value."""
        self.assertEqual(15, calculate_score(HAG04(self._prepare_scoresheet(white = 3))))
        self.assertEqual(0,  calculate_score(HAG04(self._prepare_scoresheet(white = 4))))
    
    def test_haggle_HAG05(self):
        """"A player can score only as many as orange cards as he/she has blue cards."""
        self.assertEqual(18, calculate_score(HAG05(self._prepare_scoresheet(blue = 3, orange = 3))))
        self.assertEqual(12, calculate_score(HAG05(self._prepare_scoresheet(blue = 2, orange = 3))))

    def test_haggle_HAG06(self):
        """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
        player1 = self._prepare_scoresheet(blue = 5)
        player2 = self._prepare_scoresheet(blue = 6, orange = 1)
        player3 = self._prepare_scoresheet(yellow = 4, blue = 2, white = 4)
        players = HAG06([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(10-10, calculate_score(players[0]))
        self.assertEqual(16-10, calculate_score(players[1]))
        self.assertEqual(28-20, calculate_score(players[2]))

    def test_haggle_HAG07(self):
        """A set of three red cards protects you from one set of five blue cards."""
        player1 = self._prepare_scoresheet(blue = 5)
        player2 = self._prepare_scoresheet(blue = 6, red = 3)
        player3 = self._prepare_scoresheet(yellow = 2, blue = 2, red = 6)
        players = HAG07(HAG06([player1, player2, player3]))
        self.assertEqual(3, len(players))
        self.assertEqual(10-10, calculate_score(players[0]))
        self.assertEqual(21, calculate_score(players[1]))
        self.assertEqual(24, calculate_score(players[2]))
        
    def test_haggle_HAG08(self):
        """The player with the most yellow cards gets a bonus of the number of those cards squared. 
           If two or more players tie for most yellow, the bonus is calculated instead for the player 
           with the next highest number of yellows.
        """
        player1 = self._prepare_scoresheet(yellow = 5)
        player2 = self._prepare_scoresheet(yellow = 3, red = 3)
        player3 = self._prepare_scoresheet(orange = 2)
        players = HAG08([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(5+(5**2), calculate_score(players[0]))
        self.assertEqual(12, calculate_score(players[1]))
        self.assertEqual(8, calculate_score(players[2]))

    def test_haggle_HAG08_tie(self):
        player1 = self._prepare_scoresheet(yellow = 3, blue = 1) 
        player2 = self._prepare_scoresheet(yellow = 3, red = 3)
        player3 = self._prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG08([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(5, calculate_score(players[0]))
        self.assertEqual(12, calculate_score(players[1]))
        self.assertEqual(10+(2**2), calculate_score(players[2]))

    def test_haggle_HAG09(self):
        """If a player hands in seven or more cards of the same color, 
           for each of these colors 10 points are deducted from his/her score.
        """
        self.assertEqual(17, calculate_score(HAG09(self._prepare_scoresheet(yellow = 6, blue = 3, white = 1))))
        self.assertEqual(8,  calculate_score(HAG09(self._prepare_scoresheet(yellow = 7, blue = 3, white = 1))))
        self.assertEqual(8,  calculate_score(HAG09(self._prepare_scoresheet(yellow = 7, blue = 8, white = 1))))
        
    def test_haggle_HAG10(self):
        """Each set of five different colors gives a bonus of 10 points."""
        self.assertEqual(20, calculate_score(HAG10(self._prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1))))
        self.assertEqual(35, calculate_score(HAG10(self._prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1, white = 1))))
        self.assertEqual(63, calculate_score(HAG10(self._prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 3, white = 3))))

    def test_haggle_HAG11(self):
        """If a \"pyramid\" is handed in with no other cards, the value of the hand is doubled. 
           A pyramid consists of four cards of one color, three cards of a second color, 
           two cards of a third, and one card of a fourth color.
        """
        self.assertEqual(20*2, calculate_score(HAG11(self._prepare_scoresheet(yellow = 4, blue = 3, red = 2, orange = 1))))
        self.assertEqual(37*2, calculate_score(HAG11(self._prepare_scoresheet(yellow = 1, blue = 2, orange = 3, white = 4))))
        self.assertEqual(40, calculate_score(HAG11(self._prepare_scoresheet(yellow = 1, blue = 2, red = 1, orange = 3, white = 4))))

    def test_haggle_HAG12(self):
        """The player with the most red cards double their value.
           In case of a tie, no player collects the extra value.
        """
        player1 = self._prepare_scoresheet(yellow = 3, red = 4)
        player2 = self._prepare_scoresheet(blue = 1, red = 3)
        player3 = self._prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG12([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(15+12, calculate_score(players[0]))
        self.assertEqual(11, calculate_score(players[1]))
        self.assertEqual(10, calculate_score(players[2]))

    def test_haggle_HAG12_tie(self):
        player1 = self._prepare_scoresheet(yellow = 3, red = 3)
        player2 = self._prepare_scoresheet(blue = 1, red = 3)
        player3 = self._prepare_scoresheet(yellow = 2, orange = 2)
        players = HAG12([player1, player2, player3])
        self.assertEqual(3, len(players))
        self.assertEqual(12, calculate_score(players[0]))
        self.assertEqual(11, calculate_score(players[1]))
        self.assertEqual(10, calculate_score(players[2]))

    def test_haggle_HAG13(self):
        """Each set of two yellow cards doubles the value of one white card."""
        self.assertEqual(15, calculate_score(HAG13(self._prepare_scoresheet(white = 3))))
        self.assertEqual(16, calculate_score(HAG13(self._prepare_scoresheet(yellow = 1, white = 3))))
        self.assertEqual(17+5, calculate_score(HAG13(self._prepare_scoresheet(yellow = 2, white = 3))))
        self.assertEqual(21+3*5, calculate_score(HAG13(self._prepare_scoresheet(yellow = 6, white = 3))))
        self.assertEqual(23+3*5, calculate_score(HAG13(self._prepare_scoresheet(yellow = 8, white = 3))))

    def test_haggle_HAG14(self):
        """Each set of three blue cards quadruples the value of one orange card."""
        self.assertEqual(8, calculate_score(HAG14(self._prepare_scoresheet(orange = 2))))
        self.assertEqual(12, calculate_score(HAG14(self._prepare_scoresheet(blue = 2, orange = 2))))
        self.assertEqual(14+12, calculate_score(HAG14(self._prepare_scoresheet(blue = 3, orange = 2))))
        self.assertEqual(20+24, calculate_score(HAG14(self._prepare_scoresheet(blue = 6, orange = 2))))
        self.assertEqual(26+24, calculate_score(HAG14(self._prepare_scoresheet(blue = 9, orange = 2))))

    def test_haggle_HAG15(self):
        """No more than thirteen cards in a hand can be scored. 
           If more are handed in, the excess will be removed at random.
        """
        scoresheet = HAG15(self._prepare_scoresheet(5, 5, 5, 5, 15))
        total_scored_cards = 0
        for color, cards in scoresheet.iteritems():
            if color != 'extra':
                total_scored_cards += cards['scored_cards']
        self.assertEqual(13, total_scored_cards)

    def _prepare_scoresheet(self, yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
        return setup_scoresheet({ Commodity.objects.get(ruleset = 1, name ='Yellow') : yellow,
                                  Commodity.objects.get(ruleset = 1, name ='Blue') : blue,
                                  Commodity.objects.get(ruleset = 1, name ='Red') : red,
                                  Commodity.objects.get(ruleset = 1, name ='Orange') : orange,
                                  Commodity.objects.get(ruleset = 1, name ='White') : white })