from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from model_mommy import mommy
from profile.models import MystradeUser

class MystradeUserNameTest(TestCase):
    def test_name_first_and_last(self):
        user = MystradeUser.objects.create(username = "username", first_name = "first", last_name="last")
        self.assertEqual("first last", user.name)

    def test_name_firstBlank_and_last(self):
        user = MystradeUser.objects.create(username = "username", first_name = "", last_name="last")
        self.assertEqual("last", user.name)

    def test_name_lastBlank_and_first(self):
        user = MystradeUser.objects.create(username = "username", first_name = "first", last_name="")
        self.assertEqual("first", user.name)

    def test_only_username(self):
        user = MystradeUser.objects.create(username = "username", first_name = "", last_name="")
        self.assertEqual("username", user.name)

class ViewsTest(TestCase):
    def setUp(self):
        self.testUser = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', bio = 'line\r\njump',
                                   send_notifications = True, timezone = 'Asia/Phnom_Penh')
        self.testUser.set_password('test');
        self.testUser.save()

        self.client.login(username = 'test', password = 'test')

    def test_display_own_profile(self):
        response = self.client.get("/profile/")

        self.assertContains(response, "test@aaa.com")
        self.assertContains(response, "line<br />jump")
        self.assertContains(response, "Yes")
        self.assertContains(response, "Asia/Phnom_Penh")
        self.assertTemplateUsed(response, 'profile/profile.html')

    def test_display_profile_with_own_id_is_redirected(self):
        response = self.client.get("/profile/{0}/".format(self.testUser.id))

        self.assertRedirects(response, "/profile/")

    def test_display_profile_for_other_player(self):
        otherUser = get_user_model()(username = 'someone', email = 'someone@bbb.com', first_name = 'luke', last_name = 'skywalker',
                                 contact = 'call me maybe', send_notifications = False, timezone = 'Europe/London')
        otherUser.set_password('password');
        otherUser.save()

        response = self.client.get("/profile/{0}/".format(otherUser.id))

        self.assertContains(response, "Luke Skywalker")
        self.assertNotContains(response, "someone@bbb.com")
        self.assertNotContains(response, "Yes")
        self.assertNotContains(response, "Europe/London")
        self.assertContains(response, "call me maybe")
        self.assertTemplateUsed(response, 'profile/otherprofile.html')

    def test_editprofile_change_user_fields_and_password(self):
        response = self.client.post("/profile/edit/",
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'send_notifications': '',
                                     'timezone': 'Europe/Rome',
                                     'email': 'test@aaa.com', 'bio': 'princess', 'contact': 'D2-R2',
                                     'old_password': 'test', 'new_password1': 'alderaan', 'new_password2': 'alderaan'},
                                    follow = True)

        self.assertEqual(200, response.status_code)
        modifiedUser = get_user_model().objects.get(pk = self.testUser.id)
        self.assertEqual("Leia Organa", modifiedUser.name)
        self.assertEqual("test@aaa.com", modifiedUser.email)
        self.assertEqual("Europe/Rome", modifiedUser.timezone)
        self.assertEqual("princess", modifiedUser.bio)
        self.assertEqual("D2-R2", modifiedUser.contact)
        self.assertFalse(modifiedUser.send_notifications)
        self.assertTrue(check_password('alderaan', modifiedUser.password))

        self.assertTemplateUsed(response, 'profile/profile.html')

    def test_editprofile_bad_old_password(self):
        response = self.client.post("/profile/edit/",
                                    {'old_password': 'BAD', 'new_password1': 'alderaan', 'new_password2': 'alderaan'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'old_password', "Your old password was entered incorrectly. Please enter it again.")

        response = self.client.post("/profile/edit/",
                                    {'old_password': '', 'new_password1': 'alderaan', 'new_password2': 'alderaan'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'old_password', "This field is required.")

    def test_editprofile_bad_new_passwords(self):
        response = self.client.post("/profile/edit/",
                                    {'old_password': 'test', 'new_password1': 'pass1', 'new_password2': ''},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password2', "This field is required.")

        response = self.client.post("/profile/edit/",
                                    {'old_password': 'test', 'new_password1': '', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password1', "This field is required.")

        response = self.client.post("/profile/edit/",
                                    {'old_password': 'test', 'new_password1': 'pass1', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password2', "The two password fields didn't match.")

    def test_editprofile_password_fields_not_evaluated_when_new_password1_is_empty(self):
        response = self.client.post("/profile/edit/",
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'timezone': 'Europe/Paris',
                                     'old_password': 'bogus', 'new_password1': '', 'new_password2': 'alderaan'},
                                    follow = True)
        self.assertNotContains(response, "Your old password was entered incorrectly. Please enter it again.")
        self.assertNotContains(response, "The two password fields didn&#39;t match.")

    def test_editprofile_timezone_is_validated_against_pytz_common_timezones(self):
        response = self.client.post("/profile/edit/",
                                    {'timezone': 'Alderaan/Aldera'},
                                    follow = True)

        self.assertFormError(response, 'user_form', 'timezone', "Select a valid choice. Alderaan/Aldera is not one of the available choices.")
