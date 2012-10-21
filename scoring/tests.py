from django.contrib.auth.models import User
from django.test import TestCase
from scoring.card_scoring import calculate_score, HAG01, HAG04, HAG05
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
    def test_haggle_initial_values(self):
        """Yellow = 1 / Blue = 2 / Red = 3 / Orange = 4 / White = 5"""
        self.assertEqual(15, calculate_score(HAG01(self.prepare_hand(1, 1, 1, 1, 1))))
        self.assertEqual(20, calculate_score(HAG01(self.prepare_hand(blue = 1, red = 2, orange = 3))))

    def test_haggle_HAG04(self):
        """If a player has more than three white cards, all of his/her white cards lose their value."""
        self.assertEqual(15, calculate_score(HAG04(HAG01(self.prepare_hand(white = 3)))))
        self.assertEqual(0, calculate_score(HAG04(HAG01(self.prepare_hand(white = 4)))))
    
    def test_haggle_HAG05(self):
        """"A player can score only as many as orange cards as he/she has blue cards."""
        self.assertEqual(18, calculate_score(HAG05(HAG01(self.prepare_hand(blue = 3, orange = 3)))))
        self.assertEqual(12, calculate_score(HAG05(HAG01(self.prepare_hand(blue = 2, orange = 3)))))
        
    def prepare_hand(self, yellow = 0, blue = 0, red = 0, orange = 0, white = 0):
        return { Commodity.objects.get(ruleset = 1, name ='Yellow') : yellow,
                 Commodity.objects.get(ruleset = 1, name ='Blue') : blue,
                 Commodity.objects.get(ruleset = 1, name ='Red') : red,
                 Commodity.objects.get(ruleset = 1, name ='Orange') : orange,
                 Commodity.objects.get(ruleset = 1, name ='White') : white }