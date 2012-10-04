from django.test import TestCase
from django.contrib.auth.models import User

class UserProfileTest(TestCase):
    def test_name_first_and_last(self):
        user = User.objects.create(username = "username", first_name = "first", last_name="last")
        self.assertEqual("first last", user.get_profile().name)
        
    def test_name_firstBlank_and_last(self):
        user = User.objects.create(username = "username", first_name = "", last_name="last")
        self.assertEqual("last", user.get_profile().name)
        
    def test_only_username(self):
        user = User.objects.create(username = "username", first_name = "", last_name="")
        self.assertEqual("username", user.get_profile().name)
