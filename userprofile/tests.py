from django.contrib.auth.models import User
from django.test import TestCase

class UserProfileTest(TestCase):
    def test_name_first_and_last(self):
        user = User.objects.create(username = "username", first_name = "first", last_name="last")
        self.assertEqual("first last", user.get_profile().name)

    def test_name_firstBlank_and_last(self):
        user = User.objects.create(username = "username", first_name = "", last_name="last")
        self.assertEqual("last", user.get_profile().name)

    def test_name_lastBlank_and_first(self):
        user = User.objects.create(username = "username", first_name = "first", last_name="")
        self.assertEqual("first", user.get_profile().name)

    def test_only_username(self):
        user = User.objects.create(username = "username", first_name = "", last_name="")
        self.assertEqual("username", user.get_profile().name)

class ViewsTest(TestCase):
    def setUp(self):
        self.testUser = User.objects.create_user('test', 'test@aaa.com', 'test')
        profile = self.testUser.get_profile()
        profile.bio = 'line\r\njump'
        profile.send_notifications = True
        profile.save()

        self.client.login(username = 'test', password = 'test')

    def test_display_own_profile(self):
        response = self.client.get("/profile/")

        self.assertContains(response, "test@aaa.com")
        self.assertContains(response, "line<br />jump")
        self.assertContains(response, "Yes")
        self.assertTemplateUsed(response, 'userprofile/profile.html')

    def test_display_profile_with_own_id_is_redirected(self):
        response = self.client.get("/profile/{}/".format(self.testUser.id))

        self.assertRedirects(response, "/profile/")

    def test_display_profile_for_other_player(self):
        otherUser = User.objects.create_user('someone', 'someone@bbb.com', 'password')
        otherUser.first_name = 'luke'
        otherUser.last_name = 'skywalker'
        otherUser.save()
        profile = otherUser.get_profile()
        profile.contact = 'call me maybe'
        profile.send_notifications = False
        profile.save()

        response = self.client.get("/profile/{}/".format(otherUser.id))

        self.assertContains(response, "Luke Skywalker")
        self.assertNotContains(response, "someone@bbb.com")
        self.assertNotContains(response, "Yes")
        self.assertContains(response, "call me maybe")
        self.assertTemplateUsed(response, 'userprofile/otherprofile.html')

    def test_editprofile_change_user_and_profile(self):
        response = self.client.post("/profile/edit/",
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'send_notifications': '',
                                     'email': 'test@aaa.com', 'bio': 'princess', 'contact': 'D2-R2'},
                                    follow = True)

        self.assertEqual(200, response.status_code)
        modifiedUser = User.objects.get(pk = self.testUser.id)
        self.assertEqual("Leia Organa", modifiedUser.get_profile().name)
        self.assertEqual("test@aaa.com", modifiedUser.email)
        self.assertEqual("princess", modifiedUser.get_profile().bio)
        self.assertEqual("D2-R2", modifiedUser.get_profile().contact)
        self.assertFalse(modifiedUser.get_profile().send_notifications)

        self.assertTemplateUsed(response, 'userprofile/profile.html')

    def test_editprofile_bad_password_confirmation(self):
        expectedMessage = "The two password fields didn't match."

        response = self.client.post("/profile/edit/",
                                    {'new_password1': 'pass1', 'new_password2': ''},
                                    follow = True)
        self.assertFormError(response, 'user_form', 'new_password2', expectedMessage)

        response = self.client.post("/profile/edit/",
                                    {'new_password1': '', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'user_form', 'new_password2', expectedMessage)

        response = self.client.post("/profile/edit/",
                                    {'new_password1': 'pass1', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'user_form', 'new_password2', expectedMessage)
