from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.timezone import get_default_timezone
from game.forms import validate_number_of_players
from scoring.models import Ruleset
import datetime

class ViewsTest(TestCase):
    def setUp(self):
        self.testUserCanCreate = User.objects.create_user('testCanCreate', 'test@aaa.com', 'test')
        self.testUserCanCreate.user_permissions.add(Permission.objects.get(codename = 'add_game'))
        self.testUsersNoCreate = []
        for i in range(3):
            self.testUsersNoCreate.append(User.objects.create_user('testNoCreate{}'.format(i), 'test@aaa.com', 'test'))
        
        self.client.login(username = 'testCanCreate', password = 'test')

    def test_create_game_only_with_the_permission(self):
        # initially logged as testCanCreate
        response = self.client.get("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.client.login(username = 'testNoCreate0', password = 'test')
        response = self.client.get("/game/create/")
        self.assertEqual(302, response.status_code)
        self.client.logout()

    def test_create_game_without_dates_fails(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date': '', 'end_date': '11/13/2012 00:15'})
        self.assertFormError(response, 'form', 'start_date', 'This field is required.')

        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date':'11/10/2012 15:30', 'end_date': ''})
        self.assertFormError(response, 'form', 'end_date', 'This field is required.')

    def test_create_game_without_enough_players(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 
                                                      'start_date': '11/10/2012 18:30', 
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': self.testUsersNoCreate[0].id})
        self.assertFormError(response, 'form', None, 'Please select at least 3 players (as many as there are mandatory rule cards in this ruleset).')

    def test_create_game_first_page(self):
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate]})
        self.assertRedirects(response, "/game/rules/")
        #created_game = Game.objects.get(master = self.testUserCanCreate.id)
        self.assertEqual(1, self.client.session['ruleset'].id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), self.client.session['start_date'])
        self.assertEqual(datetime.datetime(2012, 11, 13, 00, 15, tzinfo = get_default_timezone()), self.client.session['end_date'])
        #self.assertListEqual(self.testUsersNoCreate, list(created_game.players.all()))
        self.assertListEqual(self.testUsersNoCreate, self.client.session['players'])

    def test_access_rules_with_incomplete_session_redirects_to_first_page(self):
        self.client.session.clear()
        response = self.client.get("/game/rules/", {'ruleset': 1})
        self.assertRedirects(response, "/game/create/")

class FormsTest(TestCase):
    def test_validate_number_of_players(self):
        chosen_ruleset = Ruleset.objects.get(id = 1)
        self.assertRaisesMessage(ValidationError, 'Please select at least 3 players (as many as there are mandatory rule cards in this ruleset).', 
                                 validate_number_of_players, ['user1', 'user2'], chosen_ruleset)
        try:
            validate_number_of_players(['user1', 'user2', 'user3'], chosen_ruleset)
        except ValidationError:
            self.fail("validate_number_of_players should not fail when there are as many players as mandatory rule cards")