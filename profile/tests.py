import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now
from model_mommy import mommy
from game.models import Message, Game, GamePlayer
from profile.models import MystradeUser
from profile.views import _generate_activation_key
from utils.tests import MystradeTestCase


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
                                   send_notifications = True, timezone = 'Asia/Phnom_Penh', palette = MystradeUser.FUNKY_ORANGE)
        self.testUser.set_password('test');
        self.testUser.save()

        self.client.login(username = 'test', password = 'test')

    def test_display_own_profile(self):
        response = self.client.get(reverse("profile"))

        self.assertContains(response, "test@aaa.com")
        self.assertContains(response, "line<br />jump")
        self.assertContains(response, "Yes")
        self.assertContains(response, "Asia/Phnom_Penh")
        self.assertTemplateUsed(response, 'profile/profile.html')

    def test_display_profile_with_own_id_is_redirected(self):
        response = self.client.get(reverse("otherprofile", args = [self.testUser.id]))

        self.assertRedirects(response, "/profile/")

    def test_display_profile_for_other_player(self):
        otherUser = get_user_model()(username = 'someone', email = 'someone@bbb.com', first_name = 'luke', last_name = 'skywalker',
                                 contact = 'call me maybe', send_notifications = False, timezone = 'Europe/London')
        otherUser.set_password('password');
        otherUser.save()

        response = self.client.get(reverse("otherprofile", args = [otherUser.id]))

        self.assertContains(response, "Luke Skywalker")
        self.assertNotContains(response, "someone@bbb.com")
        self.assertNotContains(response, "Yes")
        self.assertNotContains(response, "Europe/London")
        self.assertContains(response, "call me maybe")
        self.assertTemplateUsed(response, 'profile/otherprofile.html')

    def test_editprofile_change_user_fields_and_password(self):
        response = self.client.post(reverse("editprofile"),
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'send_notifications': '',
                                     'timezone': 'Europe/Rome',
                                     'email': 'test@aaa.com', 'bio': 'princess', 'contact': 'D2-R2',
                                     'old_password': 'test', 'new_password1': 'alderaan', 'new_password2': 'alderaan',
                                     'palette': MystradeUser.BLUISH_FIESTA},
                                    follow = True)

        self.assertEqual(200, response.status_code)
        modifiedUser = get_user_model().objects.get(pk = self.testUser.id)
        self.assertEqual("Leia Organa", modifiedUser.name)
        self.assertEqual("test@aaa.com", modifiedUser.email)
        self.assertEqual("Europe/Rome", modifiedUser.timezone)
        self.assertEqual("princess", modifiedUser.bio)
        self.assertEqual("D2-R2", modifiedUser.contact)
        self.assertEqual(MystradeUser.BLUISH_FIESTA, modifiedUser.palette)
        self.assertFalse(modifiedUser.send_notifications)
        self.assertTrue(check_password('alderaan', modifiedUser.password))

        self.assertTemplateUsed(response, 'profile/profile.html')

    def test_editprofile_bad_old_password(self):
        response = self.client.post(reverse("editprofile"),
                                    {'old_password': 'BAD', 'new_password1': 'alderaan', 'new_password2': 'alderaan'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'old_password', "Your old password was entered incorrectly. Please enter it again.")

        response = self.client.post(reverse("editprofile"),
                                    {'old_password': '', 'new_password1': 'alderaan', 'new_password2': 'alderaan'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'old_password', "This field is required.")

    def test_editprofile_bad_new_passwords(self):
        response = self.client.post(reverse("editprofile"),
                                    {'old_password': 'test', 'new_password1': 'pass1', 'new_password2': ''},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password2', "This field is required.")

        response = self.client.post(reverse("editprofile"),
                                    {'old_password': 'test', 'new_password1': '', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password1', "This field is required.")

        response = self.client.post(reverse("editprofile"),
                                    {'old_password': 'test', 'new_password1': 'pass1', 'new_password2': 'pass2'},
                                    follow = True)
        self.assertFormError(response, 'password_form', 'new_password2', "The two password fields didn't match.")

    def test_editprofile_password_fields_not_evaluated_when_new_password1_is_empty(self):
        response = self.client.post(reverse("editprofile"),
                                    {'username': 'test', 'first_name': 'Leia', 'last_name': 'Organa',
                                     'timezone': 'Europe/Paris', 'email': 'test@aaa.com',
                                     'old_password': 'bogus', 'new_password1': '', 'new_password2': 'alderaan',
                                     'palette': MystradeUser.DEFAULT_PALETTE},
                                    follow = True)
        self.assertNotContains(response, "Your old password was entered incorrectly. Please enter it again.")
        self.assertNotContains(response, "The two password fields didn&#39;t match.")

    def test_editprofile_timezone_is_validated_against_pytz_common_timezones(self):
        response = self.client.post(reverse("editprofile"),
                                    {'timezone': 'Alderaan/Aldera'},
                                    follow = True)

        self.assertFormError(response, 'user_form', 'timezone', "Select a valid choice. Alderaan/Aldera is not one of the available choices.")

class SignUpTest(TestCase):
    def test_view_sign_up_page(self):
        response = self.client.get(reverse("signup"))
        self.assertContains(response, "Create profile")
        self.assertNotContains(response, "Back")
        self.assertNotContains(response, "Change password")
        self.assertNotContains(response, "New password confirmation")
        self.assertContains(response, "Type your password")
        self.assertContains(response, "Please type your password again")
        self.assertTrue(response.context['user_form']['send_notifications'].field.initial)

    def test_register_fails_when_required_fields_are_not_specified(self):
        response = self.client.post(reverse("signup"),
            {
                'username':         '',
                'email':            '',
                'timezone':         '',
                'new_password1':    '',
                'new_password2':    '',
                'mystery':          ''
            })

        self.assertFormError(response, 'user_form', 'username', 'This field is required.')
        self.assertFormError(response, 'user_form', 'email', 'The email address is required.')
        self.assertFormError(response, 'user_form', 'timezone', 'This field is required.')
        self.assertFormError(response, 'password_form', 'new_password1', 'This field is required.')
        self.assertFormError(response, 'password_form', 'new_password2', 'This field is required.')
        self.assertFormError(response, 'user_form', 'mystery', 'Wrong answer.')

    def test_register_fails_when_email_is_not_valid(self):
        response = self.client.post(reverse("signup"),
            {
                'username':         'test',
                'email':            'abc',
                'timezone':         'Europe/Berlin',
                'new_password1':    'pwd',
                'new_password2':    'pwd',
                'mystery':          'mysTRADE'
            })

        self.assertFormError(response, 'user_form', 'email', 'Enter a valid email address.')

    def test_register_fails_when_timezone_does_not_exist(self):
        response = self.client.post(reverse("signup"),
            {
                'username':         'test',
                'email':            'test@aaa.com',
                'timezone':         'Moon/Moonbase_Alpha',
                'new_password1':    'pwd',
                'new_password2':    'pwd',
                'mystery':          'mysTrade'
            })

        self.assertFormError(response, 'user_form', 'timezone', 'Select a valid choice. Moon/Moonbase_Alpha is not one of the available choices.')

    def test_register_fails_when_antibot_verification_fails(self):
        response = self.client.post(reverse("signup"),
            {
                'username':             'test',
                'first_name':           'johnny',
                'last_name':            'cash',
                'email':                'j.cash@BaB.com',
                'send_notifications':   'on',
                'timezone':             'America/Chicago',
                'bio':                  'my bio',
                'contact':              'my contact',
                'palette':              MystradeUser.DEFAULT_PALETTE,
                'new_password1':        'pwd123',
                'new_password2':        'pwd123',
                'mystery':              'FAIL'
            })

        self.assertTemplateUsed(response, 'profile/editprofile.html')
        self.assertFormError(response, 'user_form', 'mystery', 'Wrong answer.')

    def test_register_keeps_timezone_and_other_fields_when_errors_are_detected(self):
        response = self.client.post(reverse("signup"),
            {
                'username':         'test',
                'first_name':       'johnny',
                'email':            '',
                'timezone':         'Pacific/Tahiti',
                'contact':          'my contact',
                'new_password1':    'pwd',
                'new_password2':    'pwd',
                'mystery':          'Mystrade'
            })

        self.assertFormError(response, 'user_form', 'email', 'The email address is required.')

        self.assertEqual("johnny", response.context['user_form']['first_name'].data)
        self.assertEqual("Pacific/Tahiti", response.context['user_form']['timezone'].data)
        self.assertEqual("my contact", response.context['user_form']['contact'].data)
        self.assertEqual("Mystrade", response.context['user_form']['mystery'].data)

    def test_register_username_and_email_must_be_unique(self):
        mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com')

        response = self.client.post(reverse("signup"),
            {
                'username':         'test',
                'email':            'test@aaa.com',
                'timezone':         'Europe/Madrid',
                'new_password1':    'pwd',
                'new_password2':    'pwd',
                'mystery':          'Mystrade'
            })

        self.assertFormError(response, 'user_form', 'username', 'User with this Username already exists.')
        self.assertFormError(response, 'user_form', 'email', 'User with this email address already exists.')

    def test_register_successful_creates_an_inactive_user_and_sends_an_activation_email(self):
        response = self.client.post(reverse("signup"),
            {
                'username':             'test',
                'first_name':           'johnny',
                'last_name':            'cash',
                'email':                'j.cash@BaB.com',
                'send_notifications':   'on',
                'timezone':             'America/Chicago',
                'bio':                  'my bio',
                'contact':              'my contact',
                'palette':              MystradeUser.DEFAULT_PALETTE,
                'new_password1':        'pwd123',
                'new_password2':        'pwd123',
                'mystery':              'MysTrade'
            })

        self.assertContains(response, "has been sent to the email address you supplied")

        try:
            created_user = get_user_model().objects.get(username = 'test')
            self.assertEqual('johnny', created_user.first_name)
            self.assertEqual('cash', created_user.last_name)
            self.assertEqual('j.cash@bab.com', created_user.email)
            self.assertTrue(created_user.send_notifications)
            self.assertEqual('America/Chicago', created_user.timezone)
            self.assertEqual('my bio', created_user.bio)
            self.assertEqual('my contact', created_user.contact)
            self.assertEqual('funky_orange', created_user.palette)
            self.assertFalse(created_user.is_active)
            self.assertFalse(created_user.is_staff)
            self.assertFalse(created_user.is_superuser)
            self.assertTrue(check_password('pwd123', created_user.password))
        except get_user_model().DoesNotExist:
            self.fail("A user should have been created")

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(['j.cash@bab.com'], email.to)
        self.assertEqual('[MysTrade] Registration activation on mystrade.com', email.subject)
        self.assertIn('please navigate to the link below', email.body)
        self.assertIn('/profile/activation/{0}/{1}'.format(created_user.id, _generate_activation_key(created_user)), email.body)

    def test_register_antibot_verification_field_accepts_dots(self):
        response = self.client.post(reverse("signup"),
            {
                'username':             'test',
                'first_name':           'johnny',
                'last_name':            'cash',
                'email':                'j.cash@BaB.com',
                'send_notifications':   'on',
                'timezone':             'America/Chicago',
                'bio':                  'my bio',
                'contact':              'my contact',
                'palette':              MystradeUser.DEFAULT_PALETTE,
                'new_password1':        'pwd123',
                'new_password2':        'pwd123',
                'mystery':              'mystra.de'
            })

        self.assertContains(response, "has been sent to the email address you supplied")

    def test_activation_of_an_invalid_key(self):
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com')

        response = self.client.get(reverse("activation", args = [user.id, '%invalid@']))
        self.assertEqual(403, response.status_code)

    def test_activation_of_an_unknown_user(self):
        response = self.client.get(reverse("activation", args = ['987654', 'a'*40]))
        self.assertEqual(403, response.status_code)

    @override_settings(ACCOUNT_ACTIVATION_DAYS = 2)
    def test_activation_with_expired_key_fails_and_deletes_the_user(self):
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', is_active = False,
                          date_joined = now() + datetime.timedelta(days = -3))

        response = self.client.get(reverse("activation", args = [user.id, _generate_activation_key(user)]), follow = True)
        self.assertEqual(200, response.status_code)
        try:
            user = get_user_model().objects.get(username = 'test')
            self.fail("User with expired key should have been deleted")
        except get_user_model().DoesNotExist:
            pass
        self.assertTemplateUsed(response, "profile/activation_expired.html")
        self.assertContains(response, "Your activation link has expired")

    @override_settings(ACCOUNT_ACTIVATION_DAYS = 2)
    def test_activation_of_an_already_active_user_with_an_expired_key_should_not_delete_the_user(self):
        game = mommy.make(Game)
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', is_active = True,
                          date_joined = now() + datetime.timedelta(days = -3))
        mommy.make(Message, game = game, sender = user, content = 'abc')
        mommy.make(GamePlayer, game = game, player = user)

        response = self.client.get(reverse("activation", args = [user.id, _generate_activation_key(user)]), follow = True)
        self.assertEqual(403, response.status_code)

        try:
            get_user_model().objects.get(username = 'test')
        except get_user_model().DoesNotExist:
            self.fail("User with expired key should have been deleted")

    def test_activation_with_the_bad_key_fails(self):
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', is_active = False)
        response = self.client.get(reverse("activation", args = [user.id, 'a'*40]), follow = True)
        self.assertEqual(403, response.status_code)
        user = get_user_model().objects.get(id = user.id)
        self.assertFalse(user.is_active)

    def test_activation_with_a_correct_key_makes_the_user_active(self):
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', is_active = False)
        user.set_password('pwd123')
        user.save()

        response = self.client.get(reverse("activation", args = [user.id, _generate_activation_key(user)]), follow = True)
        self.assertEqual(200, response.status_code)

        user = get_user_model().objects.get(id = user.id)
        self.assertTrue(user.is_active)

        self.assertTemplateUsed(response, "profile/activation_complete.html")

    def test_only_activated_users_can_log_in(self):
        user = mommy.make(get_user_model(), username = 'test', email = 'test@aaa.com', is_active = False)
        user.set_password('pwd123')
        user.save()

        response = self.client.post(reverse('login'),
            {
                'username': 'test',
                'password': 'pwd123'
            })
        self.assertContains(response, "Your username and password didn't match. Please try again.")

        user.is_active = True
        user.save()

        response = self.client.post(reverse('login'),
            {
                'username': 'test',
                'password': 'pwd123'
            })
        self.assertRedirects(response, reverse('nopath'))

class PaletteTest(MystradeTestCase):

    def test_when_no_one_is_authenticated_we_expect_the_default_palette(self):
        self.client.logout()

        response = self.client.get(reverse("rules"))
        self.assertNotContains(response, "css/palette")

    def test_when_authenticated_with_an_alternative_palette_the_css_should_be_added(self):
        self.loginUser.palette = MystradeUser.BLUISH_FIESTA
        self.loginUser.save()

        response = self.client.get(reverse("rules"))
        self.assertContains(response, "css/palette/{0}.css".format(MystradeUser.BLUISH_FIESTA))

    def test_when_authenticated_with_the_default_palette_the_css_should_not_be_added(self):
        self.loginUser.palette = MystradeUser.DEFAULT_PALETTE
        self.loginUser.save()

        response = self.client.get(reverse("rules"))
        self.assertNotContains(response, "css/palette")