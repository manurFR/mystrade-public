import datetime
from django.contrib.auth import get_user_model
from django.core import mail
from django.template import Template
from django.test import TestCase
from django.test.utils import override_settings
from model_mommy import mommy
from game.models import Game, CommodityInHand
from ruleset.models import RuleCard, Commodity
from trade.models import Trade
from utils import roundTimeToMinute, _send_notification_email
from stats import record
from models import StatsScore


class MystradeTestCase(TestCase):
    """ Parent test case class with default element bootstrapped, to be inherited by other apps' test cases """
    fixtures = ['test_users.json', # from profile app
                'test_games.json']

    def setUp(self):
        self.game =             Game.objects.get(id = 1)
        self.master =           self.game.master
        self.loginUser =        get_user_model().objects.get(username = "test2")
        self.alternativeUser =  get_user_model().objects.get(username = 'test5')
        self.admin =            get_user_model().objects.get(username = 'admin')
        self.admin_player =     get_user_model().objects.get(username = 'admin_player')
        self.unrelated_user =   get_user_model().objects.get(username = 'unrelated_user')

        self.login_as(self.loginUser)

    def login_as(self, user):
        self.assertTrue(self.client.login(username = user.username, password = 'test'))

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
        return mommy.make(get_user_model(), email = email, send_notifications = send_notifications)

class StatsTest(MystradeTestCase):
    def test_record(self):
        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG10')) # 5 different colors => +10 points
        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG12')) # most red cards double their value
        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG13')) # 3 yellow cards doubles the value of 1 white card
        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG15')) # (random) more than 13 cards => removed

        y = Commodity.objects.get(ruleset = 1, name = 'Yellow')
        b = Commodity.objects.get(ruleset = 1, name = 'Blue')
        r = Commodity.objects.get(ruleset = 1, name = 'Red')
        o = Commodity.objects.get(ruleset = 1, name = 'Orange')
        w = Commodity.objects.get(ruleset = 1, name = 'White')

        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = y)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2, commodity = b)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = r)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2, commodity = o)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2, commodity = w)

        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 6, commodity = y)
        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 1, commodity = b)
        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 2, commodity = r)
        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 6, commodity = o)

        trade = mommy.make(Trade)

        record(self.game, trade)

        try:
            stats_loginUser = StatsScore.objects.get(game = self.game, player = self.loginUser)
            self.assertEqual(trade, stats_loginUser.trade)
            self.assertEqual(68, stats_loginUser.score)
            self.assertFalse(stats_loginUser.random)
            self.assertIsNotNone(stats_loginUser.dateScore)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for loginUser (test2)")

        try:
            stats_loginUser = StatsScore.objects.get(game = self.game, player = self.alternativeUser)
            self.assertEqual(trade, stats_loginUser.trade)
            self.assertTrue(stats_loginUser.random)
            self.assertIsNotNone(stats_loginUser.dateScore)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for alternativeUser (test5)")