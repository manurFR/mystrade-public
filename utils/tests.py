#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
from django.contrib.auth import get_user_model
from django.core import mail
from django.template import Template
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now
from model_mommy import mommy
from game.models import Game, CommodityInHand
from ruleset.models import RuleCard, Commodity
from trade.models import Trade, Offer, TradedCommodities
from utils import roundTimeToMinute, _send_notification_email, send_notification_email, _limit_line_breaks
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

    @override_settings(EMAIL_SUBJECT_PREFIX = '[test] ')
    def test_send_notification_email_should_accept_accented_characters_in_subject(self):
        template = Template(u'my name is André\nHello.')
        try:
            _send_notification_email(template, 'to1@test.com')
        except UnicodeEncodeError:
            self.fail("Notification email should accept accented characters in subject")
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual(u'[test] my name is André', email.subject)

    def test_notification_email_should_not_escape_special_characters(self):
        user = mommy.make(get_user_model(), first_name = 'John "<html>" Peter' ,last_name = "O'Neal & Yo")
        game = mommy.make(Game, master = user)
        trade = mommy.make(Trade, initiator = user, responder = user, finalizer = user)

        data = {'game': game, 'trade': trade, 'player_timezone': 'Africa/Abidjan'}

        for template in ['game_close', 'game_close_admin', 'game_create', 'game_create_admin',
                         'trade_accept', 'trade_cancel', 'trade_decline', 'trade_offer', 'trade_reply']:
            send_notification_email(template, 'recipient@dummy.com', data)

            self.assertEqual(1, len(mail.outbox))
            email = mail.outbox.pop()

            self.assertNotIn('&lt;', email.subject,     "Escaped character '&lt;' found in notification template {0}.txt :\n{1}".format(template, email.subject))
            self.assertNotIn('&lt;', email.body,        "Escaped character '&lt;' found in notification template {0}.txt :\n{1}".format(template, email.body))
            self.assertNotIn('&gt;', email.subject,     "Escaped character '&gt;' found in notification template {0}.txt :\n{1}".format(template, email.subject))
            self.assertNotIn('&gt;', email.body,        "Escaped character '&gt;' found in notification template {0}.txt :\n{1}".format(template, email.body))
            self.assertNotIn('&#39;', email.subject,    "Escaped character '&#39;' found in notification template {0}.txt :\n{1}".format(template, email.subject))
            self.assertNotIn('&#39;', email.body,       "Escaped character '&#39;' found in notification template {0}.txt :\n{1}".format(template, email.body))
            self.assertNotIn('&quot;', email.subject,   "Escaped character '&quot;' found in notification template {0}.txt :\n{1}".format(template, email.subject))
            self.assertNotIn('&quot;', email.body,      "Escaped character '&quot;' found in notification template {0}.txt :\n{1}".format(template, email.body))
            self.assertNotIn('&amp;', email.subject,    "Escaped character '&amp;' found in notification template {0}.txt :\n{1}".format(template, email.subject))
            self.assertNotIn('&amp;', email.body,       "Escaped character '&amp;' found in notification template {0}.txt :\n{1}".format(template, email.body))

    def test_limit_line_breaks(self):
        self.assertEqual("hello\nworld!",   _limit_line_breaks("hello\nworld!"))
        self.assertEqual("hello\n\nworld!", _limit_line_breaks("hello\n\nworld!"))
        self.assertEqual("hello\n\nworld!", _limit_line_breaks("hello\n\n\nworld!"))
        self.assertEqual("hello\n\nworld!", _limit_line_breaks("hello\n\n\n\nworld!"))

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

        record(self.game, trade = trade)

        try:
            stats_loginUser = StatsScore.objects.get(game = self.game, player = self.loginUser)
            self.assertEqual(trade, stats_loginUser.trade)
            self.assertEqual(68, stats_loginUser.score)
            self.assertFalse(stats_loginUser.random)
            self.assertIsNotNone(stats_loginUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for loginUser (test2)")

        try:
            stats_alternativeUser = StatsScore.objects.get(game = self.game, player = self.alternativeUser)
            self.assertEqual(trade, stats_alternativeUser.trade)
            self.assertTrue(stats_alternativeUser.random)
            self.assertIsNotNone(stats_alternativeUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for alternativeUser (test5)")

        self.assertEqual(stats_loginUser.date_score, stats_alternativeUser.date_score)

    def test_record_scores_at_game_creation(self):
        self.game.delete()
        self.client.logout()
        self.login_as(self.master)
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2037 00:15',
                                                      'players': [self.loginUser.id, self.alternativeUser.id, self.admin_player.id]})
        self.assertRedirects(response, "/game/selectrules/")
        response = self.client.post("/game/selectrules/",
                                    {'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG01').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG02').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG03').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG04').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG05').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG06').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG07').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG08').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG09').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG10').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG11').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG12').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG13').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG14').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset_id = 1, ref_name = 'HAG15').id): 'False'
                                    })

        created_game = Game.objects.get(master = self.master)
        self.assertRedirects(response, "/game/{0}/".format(created_game.id))
        stats = list(StatsScore.objects.filter(game = created_game))
        self.assertEqual(3, len(stats))
        self.assertGreater(stats[0].score, 0)
        self.assertGreater(stats[1].score, 0)
        self.assertGreater(stats[2].score, 0)

    def test_record_scores_when_trades_are_performed(self):
        y = Commodity.objects.get(ruleset = 1, name = 'Yellow')
        b = Commodity.objects.get(ruleset = 1, name = 'Blue')
        r = Commodity.objects.get(ruleset = 1, name = 'Red')

        cih_i1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = y)
        cih_i2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2, commodity = b)
        cih_i3 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = r)

        cih_r1 = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 6, commodity = y)
        cih_r2 = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 1, commodity = b)
        cih_r3 = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 2, commodity = r)

        offer_initiator = mommy.make(Offer)
        tc1 = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = cih_i1, nb_traded_cards = 1)
        tc2 = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = cih_i3, nb_traded_cards = 2)
        offer_initiator.tradedcommodities_set.add(tc1)
        offer_initiator.tradedcommodities_set.add(tc2)

        offer_responder = mommy.make(Offer)
        tc3 = mommy.make(TradedCommodities, offer = offer_responder, commodityinhand = cih_r2, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc3)

        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                   status = 'REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/trade/{0}/{1}/accept/".format(self.game.id, trade.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(200, response.status_code)

        try:
            stats_loginUser = StatsScore.objects.get(game = self.game, player = self.loginUser)
            self.assertEqual(trade, stats_loginUser.trade)
            self.assertEqual(11, stats_loginUser.score)
            self.assertIsNotNone(stats_loginUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for loginUser (test2)")

        try:
            stats_alternativeUser = StatsScore.objects.get(game = self.game, player = self.alternativeUser)
            self.assertEqual(trade, stats_alternativeUser.trade)
            self.assertEqual(19, stats_alternativeUser.score)
            self.assertIsNotNone(stats_alternativeUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for alternativeUser (test5)")

    def test_record_scores_when_game_is_closed(self):
        self.client.logout()
        self.login_as(self.master)

        self.game.end_date = now() + datetime.timedelta(days = -2)
        self.game.save()

        y = Commodity.objects.get(ruleset = 1, name = 'Yellow')
        b = Commodity.objects.get(ruleset = 1, name = 'Blue')
        r = Commodity.objects.get(ruleset = 1, name = 'Red')

        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = y)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2, commodity = b)
        mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 3, commodity = r)

        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 6, commodity = y)
        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 1, commodity = b)
        mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 2, commodity = r)

        response = self.client.post("/game/{0}/close/".format(self.game.id), HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')
        self.assertEqual(200, response.status_code)

        try:
            stats_loginUser = StatsScore.objects.get(game = self.game, player = self.loginUser)
            self.assertIsNone(stats_loginUser.trade)
            self.assertEqual(16, stats_loginUser.score)
            self.assertIsNotNone(stats_loginUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for loginUser (test2)")

        try:
            stats_alternativeUser = StatsScore.objects.get(game = self.game, player = self.alternativeUser)
            self.assertIsNone(stats_alternativeUser.trade)
            self.assertEqual(14, stats_alternativeUser.score)
            self.assertIsNotNone(stats_alternativeUser.date_score)
        except StatsScore.DoesNotExist:
            self.fail("StatsScore does not contain record for alternativeUser (test5)")

