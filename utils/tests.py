import datetime
from django.contrib.auth.models import User
from django.core import mail
from django.template import Template
from django.test import TestCase
from django.test.utils import override_settings
from model_mommy import mommy
from game.models import Game
from utils import roundTimeToMinute, _send_notification_email

class UtilsTest(TestCase):
    def test_roundTimeToMinute(self):
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 45), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 51), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 45), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 43), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 15, 00), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 57), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 00, 0, 0), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 7, 18, 324), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 15), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 8), 15))

    @override_settings(EMAIL_SUBJECT_PREFIX = '[test] ', EMAIL_MYSTRADE = 'mystrade@test.com')
    def test_send_notification_email(self):
        template = Template('my subject\nFirst {{ stuff }}.\nSecond {{ stuff }}.')
        _send_notification_email(template, 'to1@test.com', data={'stuff': 'line'})

        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[test] my subject', email.subject)
        self.assertEqual('First line.\nSecond line.', email.body)
        self.assertEqual('mystrade@test.com', email.from_email)
        self.assertEqual(['to1@test.com'], email.to)
        self.assertEqual(['mystrade@test.com'], email.bcc)

    def test_send_notification_email_without_subject_or_recipients_doesnt_send_any_message(self):
        template = Template('\nFirst line.\nSecond line.')
        _send_notification_email(template, ['to1@test.com', 'to2@test.com'])
        self.assertEqual(0, len(mail.outbox))

        template = Template('my subject\nFirst line.\nSecond line.')
        _send_notification_email(template, None)
        self.assertEqual(0, len(mail.outbox))

        _send_notification_email(template, [])
        self.assertEqual(0, len(mail.outbox))

    @override_settings(EMAIL_SUBJECT_PREFIX = '[test] ')
    def test_send_notification_email_a_template_with_only_a_subject_and_no_body_is_sent(self):
        template = Template('my subject')
        _send_notification_email(template, ['to1@test.com', 'to2@test.com'])
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[test] my subject', email.subject)
        self.assertEqual('', email.body)
        self.assertEqual(['to1@test.com', 'to2@test.com'], email.to)

    def test_send_notification_email_can_include_a_mix_of_strings_and_Users_as_recipients(self):
        user1 = self._prepare_user('user1@test.com', send_notifications = True)

        template = Template('my subject\nmy body')
        _send_notification_email(template, recipients = [user1, 'user2@test.com'])

        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(['user1@test.com', 'user2@test.com'], email.to)

    def test_send_notification_email_with_Users_as_recipients_are_sent_if_they_have_accepted_notifications(self):
        user1 = self._prepare_user('user1@test.com', send_notifications = True)
        user2 = self._prepare_user('user2@test.com', send_notifications = False)

        template = Template('my subject\nmy body')
        _send_notification_email(template, recipients = [user1, user2])

        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(['user1@test.com'], email.to)

    def test_send_notification_email_with_no_User_who_accepts_notification_sends_nothing(self):
        user1 = self._prepare_user('user1@test.com', send_notifications = False)
        user2 = self._prepare_user('user2@test.com', send_notifications = False)

        template = Template('my subject\nmy body')
        _send_notification_email(template, recipients = [user1, user2])

        self.assertEqual(0, len(mail.outbox))

    def _prepare_user(self, email, send_notifications):
        user = mommy.make(User, email = email)
        profile = user.get_profile()
        profile.send_notifications = send_notifications
        profile.save()
        return user

class MystradeTestCase(TestCase):
    """ Parent test case class with default element bootstrapped, to be inherited by other apps' test cases """
    fixtures = ['test_users.json', # from userprofile app
                'test_games.json']

    def setUp(self):
        self.game =             Game.objects.get(id = 1)
        self.master =           self.game.master
        self.loginUser =        User.objects.get(username = "test2")
        self.alternativeUser =  User.objects.get(username = 'test5')
        self.admin =            User.objects.get(username = 'admin')
        self.admin_player =     User.objects.get(username = 'admin_player')
        self.unrelated_user =   User.objects.get(username = 'unrelated_user')

        self.login_as(self.loginUser)

    def login_as(self, user):
        self.assertTrue(self.client.login(username = user.username, password = 'test'))