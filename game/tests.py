from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.utils.timezone import utc, get_default_timezone
from game.models import Game
import datetime

class ViewsTest(TestCase):
    def setUp(self):
        self.testUserCanCreate = User.objects.create_user('testCanCreate', 'test@aaa.com', 'test')
        self.testUserCanCreate.user_permissions.add(Permission.objects.get(codename = 'add_game'))
        self.testUserNoCreate  = User.objects.create_user('testNoCreate', 'test@aaa.com', 'test')
        
        self.client.login(username = 'testCanCreate', password = 'test')

    def test_create_game_only_with_the_permission(self):
        # initially logged as testCanCreate
        response = self.client.post("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.client.login(username = 'testNoCreate', password = 'test')
        response = self.client.post("/game/create/")
        self.assertEqual(302, response.status_code)
        self.client.logout()

    def test_create_game_without_dates_fails(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date': '', 'end_date': '11/13/2012 00:15'})
        self.assertFormError(response, 'form', 'start_date', 'This field is required.')

        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date':'11/10/2012 15:30', 'end_date': ''})
        self.assertFormError(response, 'form', 'end_date', 'This field is required.')

    def test_create_game_step1(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date': '11/10/2012 18:30', 'end_date': '11/13/2012 00:15'})
        self.assertEqual(200, response.status_code)
        created_game = Game.objects.get(master = self.testUserCanCreate.id)
        self.assertEqual(1, created_game.ruleset.id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), created_game.start_date)
        self.assertEqual(datetime.datetime(2012, 11, 13, 00, 15, tzinfo = get_default_timezone()), created_game.end_date)