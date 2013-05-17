from django.contrib.auth import get_user_model
from django.test import TestCase
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
        self.testUser = get_user_model()(username = 'test', email = 'test@aaa.com', bio = 'line\r\njump', send_notifications = True)
        self.testUser.make_password('test');
        self.testUser.save()

        self.client.login(username = 'test', password = 'test')

    def test_display_own_profile(self):
        response = self.client.get("/profile/")

        self.assertContains(response, "test@aaa.com")
        self.assertContains(response, "line<br />jump")
        self.assertContains(response, "Yes")
        self.assertTemplateUsed(response, 'profile/profile.html')

    def test_display_profile_with_own_id_is_redirected(self):
        response = self.client.get("/profile/{}/".format(self.testUser.id))

        self.assertRedirects(response, "/profile/")

    def test_display_profile_for_other_player(self):
        otherUser = get_user_model()(username = 'someone', email = 'someone@bbb.com', first_name = 'luke', last_name = 'skywalker',
                                 contact = 'call me maybe', send_notifications = False)
        otherUser.make_password('password');
        otherUser.save()

        response = self.client.get("/profile/{}/".format(otherUser.id))

        self.assertContains(response, "Luke Skywalker")
        self.assertNotContains(response, "someone@bbb.com")
        self.assertNotContains(response, "Yes")
        self.assertContains(response, "call me maybe")
        self.assertTemplateUsed(response, 'profile/otherprofile.html')

    def test_editprofile_change_user_and_profile(self):
        response = self.client.post("/profile/edit/",
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'send_notifications': '',
                                     'email': 'test@aaa.com', 'bio': 'princess', 'contact': 'D2-R2'},
                                    follow = True)

        self.assertEqual(200, response.status_code)
        modifiedUser = get_user_model().objects.get(pk = self.testUser.id)
        self.assertEqual("Leia Organa", modifiedUser.name)
        self.assertEqual("test@aaa.com", modifiedUser.email)
        self.assertEqual("princess", modifiedUser.bio)
        self.assertEqual("D2-R2", modifiedUser.contact)
        self.assertFalse(modifiedUser.send_notifications)

        self.assertTemplateUsed(response, 'profile/profile.html')

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
