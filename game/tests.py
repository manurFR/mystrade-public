from django.contrib.auth.models import User, Permission
from django.test import TestCase

class ViewsTest(TestCase):
    def setUp(self):
        self.testUserCanCreate = User.objects.create_user('testCanCreate', 'test@aaa.com', 'test')
        self.testUserCanCreate.user_permissions.add(Permission.objects.get(codename = 'add_game'))
        self.testUserNoCreate  = User.objects.create_user('testNoCreate', 'test@aaa.com', 'test')

    def test_create_game_only_with_the_permission(self):
        self.client.login(username = 'testCanCreate', password = 'test')
        response = self.client.post("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.client.login(username = 'testNoCreate', password = 'test')
        response = self.client.post("/game/create/")
        self.assertEqual(302, response.status_code)
        self.client.logout()
