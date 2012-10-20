from django.contrib.auth.models import User
from django.test import TestCase

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
        self.assertContains(response, "Orange : 4");
        self.assertContains(response, "White : 0");