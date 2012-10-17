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
                                    {'form-TOTAL_FORMS': 15, 'form-INITIAL_FORMS': 15, 
                                     'form-0-card_id': 1, 'form-0-selected_rule': 'on', 
                                     'form-1-card_id': 2, 'form-1-selected_rule': 'on',
                                     'form-2-card_id': 3, 'form-2-selected_rule': 'on',
                                     'form-3-card_id': 4,
                                     'form-4-card_id': 5,
                                     'form-5-card_id': 6,
                                     'form-6-card_id': 7,
                                     'form-7-card_id': 8,
                                     'form-8-card_id': 9,
                                     'form-9-card_id': 10, 'form-9-selected_rule': 'on',
                                     'form-10-card_id': 11,
                                     'form-11-card_id': 12,
                                     'form-12-card_id': 13, 'form-12-selected_rule': 'on',
                                     'form-13-card_id': 14,
                                     'form-14-card_id': 15,
                                    })

        self.assertEqual(200, response.status_code)
        self.assertContains(response, "1 : Orange cards have a basic value of 4 and are equal to a red card and a yellow card.")
        self.assertContains(response, "2 : White cards have the highest basic value and are equal to a red card and a blue card.")
        self.assertContains(response, "3 : Blue cards have a basic value twice that of yellow and half that of orange.")
        self.assertContains(response, "10 : Each set of five different colors gives a bonus of 10 points.")
        self.assertContains(response, "13 : Each set of two yellow cards doubles the value of one white card.")
        
        #self.assertTemplateUsed(response, 'userprofile/profile.html')
