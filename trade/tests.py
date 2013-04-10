import datetime
from django.contrib.auth.models import User
from django.core import mail
from django.forms.formsets import formset_factory
from django.test import RequestFactory, Client, TransactionTestCase
from django.utils.timezone import get_default_timezone, now
from django.test import TestCase
from model_mommy import mommy
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer
from ruleset.models import Ruleset, RuleCard, Commodity
from trade.forms import RuleCardFormParse, BaseRuleCardsFormSet, TradeCommodityCardFormParse, BaseCommodityCardFormSet, TradeForm
from trade.models import Offer, Trade, TradedCommodities
from trade.views import _prepare_offer_forms

def _common_setUp(self):
    self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'), players = [], end_date = now() + datetime.timedelta(days = 7))
    for player in User.objects.exclude(username = 'test1').exclude(username = 'admin'):
        mommy.make_one(GamePlayer, game = self.game, player = player)
    self.dummy_offer = mommy.make_one(Offer, rules = [], commodities = [])
    self.loginUser = User.objects.get(username = 'test2')
    self.test5 = User.objects.get(username = 'test5')
    self.client.login(username = 'test2', password = 'test')

class CreateTradeViewTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        _common_setUp(self)

    def test_create_trade_without_responder_fails(self):
        response = self.client.post("/trade/{}/create/".format(self.game.id),
                                    {'rulecards-TOTAL_FORMS': 2, 'rulecards-INITIAL_FORMS': 2,
                                     'rulecards-0-card_id': 1,
                                     'rulecards-1-card_id': 2,
                                     'commodity-TOTAL_FORMS': 5, 'commodity-INITIAL_FORMS': 5,
                                     'commodity-0-commodity_id': 1, 'commodity-0-nb_traded_cards': 0,
                                     'commodity-1-commodity_id': 2, 'commodity-1-nb_traded_cards': 1,
                                     'commodity-2-commodity_id': 3, 'commodity-2-nb_traded_cards': 0,
                                     'commodity-3-commodity_id': 4, 'commodity-3-nb_traded_cards': 0,
                                     'commodity-4-commodity_id': 5, 'commodity-4-nb_traded_cards': 0,
                                     'free_information': 'secret!',
                                     'comment': 'a comment'
                                    })
        self.assertFormError(response, 'trade_form', 'responder', 'This field is required.')

    def test_create_trade_without_selecting_cards_fails(self):
        response = self.client.post("/trade/{}/create/".format(self.game.id),
                                    {'responder': 4,
                                     'rulecards-TOTAL_FORMS': 2, 'rulecards-INITIAL_FORMS': 2,
                                     'rulecards-0-card_id': 1,
                                     'rulecards-1-card_id': 2,
                                     'commodity-TOTAL_FORMS': 5, 'commodity-INITIAL_FORMS': 5,
                                     'commodity-0-commodity_id': 1, 'commodity-0-nb_traded_cards': 0,
                                     'commodity-1-commodity_id': 2, 'commodity-1-nb_traded_cards': 0,
                                     'commodity-2-commodity_id': 3, 'commodity-2-nb_traded_cards': 0,
                                     'commodity-3-commodity_id': 4, 'commodity-3-nb_traded_cards': 0,
                                     'commodity-4-commodity_id': 5, 'commodity-4-nb_traded_cards': 0,
                                     'free_information': 'secret!',
                                     'comment': 'a comment'
                                    })
        self.assertFormError(response, 'offer_form', None, 'At least one card should be offered.')

    def test_create_trade_is_forbidden_if_you_have_submitted_your_hand(self):
        gameplayer = GamePlayer.objects.get(game = self.game, player = self.loginUser)
        gameplayer.submit_date = now()
        gameplayer.save()

        self._assertIsCreateTradeAllowed(self.game, False)

    def test_create_trade_only_allowed_for_the_game_players(self):
        # most notably: the game master, the admins (when not in the players' list) and the users not in this game are denied
        game = mommy.make_one(Game, master = self.loginUser, players = [], end_date = now() + datetime.timedelta(days = 7))
        self._assertIsCreateTradeAllowed(game, False)

        self.client.logout()
        self.assertTrue(self.client.login(username = 'test4', password = 'test'))
        self._assertIsCreateTradeAllowed(game, False, list_allowed = False) # a random non-player user can not even see the list of trades

        self.client.logout()
        self.assertTrue(self.client.login(username = 'admin', password = 'test'))
        self._assertIsCreateTradeAllowed(game, False)

        mommy.make_one(GamePlayer, game = game, player = User.objects.get(username = 'admin'))
        self._assertIsCreateTradeAllowed(game, True)

    def _assertIsCreateTradeAllowed(self, game, create_allowed, list_allowed = True):
        expected_status = 200 if create_allowed else 403

        response = self.client.get("/trade/{}/create/".format(game.id))
        self.assertEqual(expected_status, response.status_code)

        response = self.client.post("/trade/{}/create/".format(game.id),
                                    {'responder': 4,
                                     'rulecards-TOTAL_FORMS': 2, 'rulecards-INITIAL_FORMS': 2,
                                     'rulecards-0-card_id': 1,
                                     'rulecards-1-card_id': 2,
                                     'commodity-TOTAL_FORMS': 5, 'commodity-INITIAL_FORMS': 5,
                                     'commodity-0-commodity_id': 1, 'commodity-0-nb_traded_cards': 0,
                                     'commodity-1-commodity_id': 2, 'commodity-1-nb_traded_cards': 0,
                                     'commodity-2-commodity_id': 3, 'commodity-2-nb_traded_cards': 0,
                                     'commodity-3-commodity_id': 4, 'commodity-3-nb_traded_cards': 0,
                                     'commodity-4-commodity_id': 5, 'commodity-4-nb_traded_cards': 0,
                                     'free_information': 'secret!',
                                     'comment': 'a comment'
                                    })
        self.assertEqual(expected_status, response.status_code)

        response = self.client.get("/trade/{}/".format(game.id))
        if list_allowed:
            if create_allowed:
                self.assertContains(response, '<input type="submit" value="Set up trade proposal" />')
            else:
                self.assertNotContains(response, '<input type="submit" value="Set up trade proposal" />')
        else:
            self.assertEqual(403, response.status_code)

    def test_create_trade_complete_save(self):
        ruleset = mommy.make_one(Ruleset)
        rulecard = mommy.make_one(RuleCard, ruleset = ruleset, ref_name = 'rulecard_1')
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = self.loginUser,
                                                 rulecard = rulecard, ownership_date = now())
        commodity = mommy.make_one(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = self.loginUser,
                                                           commodity = commodity, nb_cards = 2)
        response = self.client.post("/trade/{}/create/".format(self.game.id),
                                    {'responder': 4,
                                     'rulecards-TOTAL_FORMS': 1,               'rulecards-INITIAL_FORMS': 1,
                                     'rulecards-0-card_id': rule_in_hand.id,   'rulecards-0-selected_rule': 'on',
                                     'commodity-TOTAL_FORMS': 1,               'commodity-INITIAL_FORMS': 1,
                                     'commodity-0-commodity_id': commodity.id, 'commodity-0-nb_traded_cards': 1,
                                     'free_information': 'some "secret" info',
                                     'comment': 'a comment'
                                    })
        self.assertRedirects(response, "/trade/{}/".format(self.game.id))

        trade = Trade.objects.get(game = self.game, initiator__username = 'test2')
        self.assertEqual(4, trade.responder.id)
        self.assertEqual('INITIATED', trade.status)
        self.assertEqual('a comment', trade.initiator_offer.comment)
        self.assertEqual('some "secret" info', trade.initiator_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.initiator_offer.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.initiator_offer.commodities.all()))
        self.assertEqual(1, trade.initiator_offer.tradedcommodities_set.all()[0].nb_traded_cards)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{}: You have been offered a trade by test2'.format(self.game.id), email.subject)
        self.assertIn('In game #{}, test2 has offered you a new trade'.format(self.game.id), email.body)
        self.assertIn('/trade/{}/{}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test4@test.com'], email.to)

    def test_create_trade_page_doesnt_show_commodities_with_no_cards(self):
        commodity1 = mommy.make_one(Commodity, name = 'Commodity#1')
        commodity2 = mommy.make_one(Commodity, name = 'Commodity#2')
        cih1 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 1)
        cih2 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 0)

        response = self.client.get("/trade/{}/create/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">Commodity#1</div>')
        self.assertNotContains(response, '<div class="card_name">Commodity#2</div>')

class ManageViewsTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        _common_setUp(self)

    def test_trade_list(self):
        right_now = now()
        trade_initiated = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                                         initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                         creation_date = right_now - datetime.timedelta(days = 1))
        trade_cancelled = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'CANCELLED',
                                         initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                         closing_date = right_now - datetime.timedelta(days = 2), finalizer = self.loginUser)
        trade_accepted = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'ACCEPTED',
                                        initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                        closing_date = right_now - datetime.timedelta(days = 3))
        trade_declined = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'DECLINED',
                                        initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                        closing_date = right_now - datetime.timedelta(days = 4), finalizer = self.loginUser)
        trade_offered = mommy.make_one(Trade, game = self.game, responder = self.loginUser, status = 'INITIATED',
                                       initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                       creation_date = right_now - datetime.timedelta(days = 5))
        trade_replied = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                                       status = 'REPLIED', initiator_offer = mommy.make_one(Offer, rules = [], commodities = []),
                                       creation_date = right_now - datetime.timedelta(days = 6))

        response = self.client.get("/trade/{}/".format(self.game.id))

        self.assertContains(response, "submitted 1 day ago")
        self.assertContains(response, "cancelled by <strong>you</strong> 2 days ago")
        self.assertContains(response, "done 3 days ago")
        self.assertContains(response, "declined by <strong>you</strong> 4 days ago")
        self.assertContains(response, "offered 5 days ago")
        self.assertContains(response, "response submitted by test5")

    def test_show_trade_only_allowed_for_authorized_players(self):
        """ Authorized players are : - the initiator
                                     - the responder
                                     - the game master
                                     - admins ("staff" in django terminology)
        """
        trade = self._prepare_trade('INITIATED')

        # the initiator
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # the responder
        self.assertTrue(self.client.login(username = 'test5', password = 'test'))
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # the game master
        self.assertTrue(self.client.login(username = 'test1', password = 'test'))
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # an admin
        self.assertTrue(self.client.login(username = 'admin', password = 'test'))
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id), follow = True)
        self.assertEqual(200, response.status_code)

        # anybody else
        self.assertTrue(self.client.login(username = 'test3', password = 'test'))
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertEqual(403, response.status_code)

    def test_buttons_in_show_trade_with_own_initiated_trade(self):
        trade = self._prepare_trade('INITIATED')

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertContains(response, 'form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertNotContains(response, '<form action="/trade/{}/{}/reply/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_INITIATED(self):
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, 'form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertContains(response, '<form action="/trade/{}/{}/reply/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertContains(response, '<form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_REPLIED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.test5, responder = self.loginUser,
                                    responder_offer = mommy.make_one(Offer, rules = [], commodities = []))

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertContains(response, '<form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<form action="/trade/{}/{}/accept/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertNotContains(response, '<form action="/trade/{}/{}/reply/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_initiator_when_REPLIED(self):
        trade = self._prepare_trade('REPLIED', responder_offer = mommy.make_one(Offer, rules = [], commodities = []))

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, '<form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<form action="/trade/{}/{}/accept/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertContains(response, '<form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_with_trade_CANCELLED(self):
        trade = self._prepare_trade('CANCELLED')

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, 'form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<form action="/trade/{}/{}/accept/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('INITIATED')
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))

        trade.responder = self.loginUser
        trade.save()
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, '<form action="/trade/{}/{}/reply/"'.format(self.game.id, trade.id))

        trade.status = 'REPLIED'
        trade.save()
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'form action="/trade/{}/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, 'form action="/trade/{}/{}/accept/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, 'form action="/trade/{}/{}/decline/"'.format(self.game.id, trade.id))

    def test_decline_reason_displayed_in_show_trade_when_DECLINED(self):
        trade = self._prepare_trade('DECLINED', finalizer = self.test5)
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertContains(response, "declined by test5")
        self.assertNotContains(response, "with the following reason given:")

        trade.decline_reason = "Because I do not need it"
        trade.save()

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))

        self.assertContains(response, "declined by test5")
        self.assertContains(response, "with the following reason given:")
        self.assertContains(response, "Because I do not need it")

    def test_cancel_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{}/{}/cancel/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_cancel_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_cancel(self):
        # trade INITIATED but we're not the initiator
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'cancel')

        # trade REPLIED but we're not the responder
        trade.responder = User.objects.get(username = 'test3')
        trade.status = 'REPLIED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

    def test_cancel_trade_not_allowed_for_the_initiator_for_trades_not_in_status_INITIATED(self):
        trade = self._prepare_trade('REPLIED')
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'ACCEPTED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'CANCELLED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'DECLINED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

    def test_cancel_trade_not_allowed_for_the_responder_for_trades_not_in_status_REPLIED(self):
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'ACCEPTED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'CANCELLED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

        trade.status = 'DECLINED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

    def test_cancel_trade_not_allowed_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('INITIATED')
        self._assertOperationNotAllowed(trade.id, 'cancel')

    def test_cancel_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_INITIATED(self):
        trade = self._prepare_trade('INITIATED')
        response = self.client.post("/trade/{}/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{}: test2 has cancelled the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has cancelled the trade including the following elements'.format(self.game.id), email.body)
        self.assertIn('/trade/{}/{}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_cancel_trade_allowed_and_effective_for_the_responder_for_a_trade_in_status_REPLIED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.test5, responder = self.loginUser)
        response = self.client.post("/trade/{}/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{}: test2 has cancelled the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has cancelled the trade including the following elements'.format(self.game.id), email.body)
        self.assertIn('/trade/{}/{}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_reply_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{}/{}/reply/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_reply_trade_not_allowed_when_one_is_not_the_responder(self):
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = User.objects.get(username = 'test6'))
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_not_allowed_for_trades_not_in_status_INITIATED(self):
        trade = self._prepare_trade('ACCEPTED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_not_allowed_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_without_selecting_cards_fails(self):
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)
        response = self.client.post("/trade/{}/{}/reply/".format(self.game.id, trade.id),
                                    {'rulecards-TOTAL_FORMS': 2, 'rulecards-INITIAL_FORMS': 2,
                                     'rulecards-0-card_id': 1,
                                     'rulecards-1-card_id': 2,
                                     'commodity-TOTAL_FORMS': 5, 'commodity-INITIAL_FORMS': 5,
                                     'commodity-0-commodity_id': 1, 'commodity-0-nb_traded_cards': 0,
                                     'commodity-1-commodity_id': 2, 'commodity-1-nb_traded_cards': 0,
                                     'commodity-2-commodity_id': 3, 'commodity-2-nb_traded_cards': 0,
                                     'commodity-3-commodity_id': 4, 'commodity-3-nb_traded_cards': 0,
                                     'commodity-4-commodity_id': 5, 'commodity-4-nb_traded_cards': 0,
                                     'free_information': 'secret!',
                                     'comment': 'a comment'
                                    })
        self.assertFormError(response, 'offer_form', None, 'At least one card should be offered.')

    def test_reply_trade_complete_save(self):
        ruleset = mommy.make_one(Ruleset)
        rulecard = mommy.make_one(RuleCard, ruleset = ruleset)
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = self.loginUser,
                                                 rulecard = rulecard, ownership_date = now())
        commodity = mommy.make_one(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = User.objects.get(username = 'test2'),
                                                           commodity = commodity, nb_cards = 2)

        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)

        response = self.client.post("/trade/{}/{}/reply/".format(self.game.id, trade.id),
                                    {'rulecards-TOTAL_FORMS': 1,               'rulecards-INITIAL_FORMS': 1,
                                     'rulecards-0-card_id': rule_in_hand.id,   'rulecards-0-selected_rule': 'on',
                                     'commodity-TOTAL_FORMS': 1,               'commodity-INITIAL_FORMS': 1,
                                     'commodity-0-commodity_id': commodity.id, 'commodity-0-nb_traded_cards': 2,
                                     'free_information': 'some "secret" info',
                                     'comment': 'a comment'
                                    })
        self.assertRedirects(response, "/trade/{}/".format(self.game.id))

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual('REPLIED', trade.status)
        self.assertEqual('a comment', trade.responder_offer.comment)
        self.assertEqual('some "secret" info', trade.responder_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.responder_offer.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.responder_offer.commodities.all()))
        self.assertEqual(2, trade.responder_offer.tradedcommodities_set.all()[0].nb_traded_cards)

    def test_accept_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{}/{}/accept/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_accept_trade_not_allowed_when_you_re_not_the_initiator(self):
        # responder
        trade = self._prepare_trade('REPLIED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'accept')

        # someone else
        trade.initiator = User.objects.get(username = 'test3')
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'accept')

    def test_accept_trade_not_allowed_for_trades_not_in_status_REPLIED(self):
        trade = self._prepare_trade('INITIATED')
        self._assertOperationNotAllowed(trade.id, 'accept')

        trade.status = 'ACCEPTED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'accept')

        trade.status = 'CANCELLED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'accept')

        trade.status = 'DECLINED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'accept')

    def test_accept_trade_not_allowed_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('REPLIED')
        self._assertOperationNotAllowed(trade.id, 'accept')

    def test_accept_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_REPLIED(self):
        rulecard1, rulecard2 = mommy.make_many(RuleCard, 2)
        commodity1, commodity2, commodity3 = mommy.make_many(Commodity, 3)

        rih1 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                              ownership_date = now())
        rih2 = mommy.make_one(RuleInHand, game = self.game, player = self.test5, rulecard = rulecard2,
                              ownership_date = now())

        cih1i = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1,
                               nb_cards = 3)
        cih1r = mommy.make_one(CommodityInHand, game = self.game, player = self.test5, commodity = commodity1,
                               nb_cards = 3)
        cih2i = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity2,
                               nb_cards = 2)
        cih3r = mommy.make_one(CommodityInHand, game = self.game, player = self.test5, commodity = commodity3,
                               nb_cards = 2)

        # the initiaor offers rulecard1, 2 commodity1 and 1 commodity2
        offer_initiator = mommy.make_one(Offer, rules = [rih1], commodities = [])
        tc1i = mommy.make_one(TradedCommodities, offer = offer_initiator, commodityinhand = cih1i, nb_traded_cards = 2)
        offer_initiator.tradedcommodities_set.add(tc1i)
        tc2i = mommy.make_one(TradedCommodities, offer = offer_initiator, commodityinhand = cih2i, nb_traded_cards = 1)
        offer_initiator.tradedcommodities_set.add(tc2i)

        # the responder offers rulecard2, 1 commodity1 and 2 commodity3
        offer_responder = mommy.make_one(Offer, rules = [rih2], commodities = [])
        tc1r = mommy.make_one(TradedCommodities, offer = offer_responder, commodityinhand = cih1r, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc1r)
        tc3r = mommy.make_one(TradedCommodities, offer = offer_responder, commodityinhand = cih3r, nb_traded_cards = 2)
        offer_responder.tradedcommodities_set.add(tc3r)

        trade = self._prepare_trade('REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/trade/{}/{}/accept/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        # trade
        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("ACCEPTED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

        # rule cards : should have been swapped
        self.assertIsNotNone(RuleInHand.objects.get(pk = rih1.id).abandon_date)
        hand_initiator = RuleInHand.objects.filter(game = self.game, player = self.loginUser, abandon_date__isnull = True)
        self.assertEqual(1, hand_initiator.count())
        self.assertEqual(rulecard2, hand_initiator[0].rulecard)

        self.assertIsNotNone(RuleInHand.objects.get(pk = rih2.id).abandon_date)
        hand_responder = RuleInHand.objects.filter(game = self.game, player = self.test5, abandon_date__isnull = True)
        self.assertEqual(1, hand_responder.count())
        self.assertEqual(rulecard1, hand_responder[0].rulecard)

        # commodity cards : the initiator should now own 2 commodity1, 1 commodity2 and 2 commodity3, wherea
        #  the responder should own 4 commodity1, 1 commodity2 and no commodity3
        self.assertEqual(2, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity1).nb_cards)
        self.assertEqual(1, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity2).nb_cards)
        self.assertEqual(2, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity3).nb_cards)

        self.assertEqual(4, CommodityInHand.objects.get(game = self.game, player = self.test5, commodity = commodity1).nb_cards)
        self.assertEqual(1, CommodityInHand.objects.get(game = self.game, player = self.test5, commodity = commodity2).nb_cards)
        self.assertEqual(0, CommodityInHand.objects.get(game = self.game, player = self.test5, commodity = commodity3).nb_cards)

    def test_decline_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{}/{}/decline/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_decine_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_decline(self):
        # trade INITIATED but we're not the responder
        trade = self._prepare_trade('INITIATED')
        self._assertOperationNotAllowed(trade.id, 'decline')

        # trade REPLIED but we're not the initiator
        trade.initiator = self.test5
        trade.responder = self.loginUser
        trade.status = 'REPLIED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

    def test_decline_trade_not_allowed_for_the_responder_for_trades_not_in_status_INITIATED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.test5, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'ACCEPTED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'CANCELLED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'DECLINED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')
# ----
    def test_decline_trade_not_allowed_for_the_initiator_for_trades_not_in_status_REPLIED(self):
        trade = self._prepare_trade('INITIATED')
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'ACCEPTED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'CANCELLED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

        trade.status = 'DECLINED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

    def test_decline_trade_not_allowed_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('REPLIED')
        self._assertOperationNotAllowed(trade.id, 'decline')

    def test_decline_trade_allowed_and_effective_for_the_responder_for_a_trade_in_status_INITIATED(self):
        trade = self._prepare_trade('INITIATED', initiator = self.test5, responder = self.loginUser)
        response = self.client.post("/trade/{}/{}/decline/".format(self.game.id, trade.id),
                                    {'decline_reason': "that's my reason"}, follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("DECLINED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)
        self.assertEqual("that's my reason", trade.decline_reason)

    def test_decline_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_REPLIED(self):
        trade = self._prepare_trade('REPLIED')
        response = self.client.post("/trade/{}/{}/decline/".format(self.game.id, trade.id),
                                    {'decline_reason': "that's my reason"}, follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("DECLINED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)
        self.assertEqual("that's my reason", trade.decline_reason)

    def test_prepare_offer_forms_sets_up_the_correct_cards_formset_with_cards_in_pending_trades_reserved(self):
        rulecard1, rulecard2, rulecard3 = mommy.make_many(RuleCard, 3)
        commodity1, commodity2 = mommy.make_many(Commodity, 2)

        rih1 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                              ownership_date = now())
        rih2 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                              ownership_date = now())
        rih3 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard3,
                              ownership_date = now())
        cih1 = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1,
                              nb_cards = 3)
        cih2 = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity2,
                              nb_cards = 2)

        # rulecard1 and 1 card of commodity1 are in the initator offer of a pending trade
        offer1 = mommy.make_one(Offer, rules = [rih1], commodities = [])
        tc1 = mommy.make_one(TradedCommodities, offer = offer1, commodityinhand = cih1, nb_traded_cards = 1)
        offer1.tradedcommodities_set.add(tc1)
        trade1 = self._prepare_trade('INITIATED', initiator_offer = offer1)
        # rulecard2 and 1 card of commodity1 were in the initiator offer of a finalized trade
        offer2 = mommy.make_one(Offer, rules = [rih2], commodities = [])
        tc2 = mommy.make_one(TradedCommodities, offer = offer2, commodityinhand = cih1, nb_traded_cards = 1)
        offer2.tradedcommodities_set.add(tc2)
        trade2 = self._prepare_trade('CANCELLED', initiator_offer = offer2, finalizer = self.loginUser)
        # rulecard3 and 1 card of commodity 2 are in the responder offer of a pending trade
        offer3 = mommy.make_one(Offer, rules = [rih3], commodities = [])
        tc3 = mommy.make_one(TradedCommodities, offer = offer3, commodityinhand = cih2, nb_traded_cards = 1)
        offer3.tradedcommodities_set.add(tc3)
        trade1 = self._prepare_trade('REPLIED', initiator = self.test5, responder = self.loginUser, responder_offer = offer3)

        request = RequestFactory().get("/trade/{}/create/".format(self.game.id))
        request.user = self.loginUser
        offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, self.game,
                                                                                  selected_rules = [rih2],
                                                                                  selected_commodities = {cih1: 1})

        self.assertIn({'card_id':       rih1.id,
                       'public_name':   rulecard1.public_name,
                       'description':   rulecard1.description,
                       'reserved':      True, # in a pending trade
                       'selected_rule': False}, rulecards_formset.initial)
        self.assertIn({'card_id':       rih2.id,
                       'public_name':   rulecard2.public_name,
                       'description':   rulecard2.description,
                       'reserved':      False, # the trade is finalized
                       'selected_rule': True}, rulecards_formset.initial)
        self.assertIn({'card_id':       rih3.id,
                       'public_name':   rulecard3.public_name,
                       'description':   rulecard3.description,
                       'reserved':      True, # in a pending trade
                       'selected_rule': False}, rulecards_formset.initial)

        self.assertIn({'commodity_id':      commodity1.id,
                       'name':              commodity1.name,
                       'color':             commodity1.color,
                       'nb_cards':          3,
                       'nb_tradable_cards': 2, # one card is in a pending trade
                       'nb_traded_cards':   1}, commodities_formset.initial)
        self.assertIn({'commodity_id':      commodity2.id,
                       'name':              commodity2.name,
                       'color':             commodity2.color,
                       'nb_cards':          2,
                       'nb_tradable_cards': 1, # one card is in a pending trade
                       'nb_traded_cards':   0}, commodities_formset.initial)

    def test_display_of_sensitive_trade_elements(self):
        """ The description of the rules and the free information should not be shown to the other player until/unless
             the trade has reached the status ACCEPTED """
        clientTest5 = Client()
        self.assertTrue(clientTest5.login(username = 'test5', password = 'test'))

        rulecard_initiator = mommy.make_one(RuleCard, public_name = '7', description = 'rule description 7')
        rih_initiator = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard_initiator,
                                       ownership_date = now())
        rulecard_responder = mommy.make_one(RuleCard, public_name = '8', description = 'rule description 8')
        rih_responder = mommy.make_one(RuleInHand, game = self.game, player = self.test5, rulecard = rulecard_responder,
                                       ownership_date = now())
        offer_initiator = mommy.make_one(Offer, rules = [rih_initiator], commodities = [], free_information = 'this is sensitive')
        offer_responder = mommy.make_one(Offer, rules = [rih_responder], commodities = [], free_information = 'these are sensitive')

        # INITIATED : the initiator should see the sensitive elements of his offer, the responder should not
        trade = self._prepare_trade('INITIATED', initiator_offer = offer_initiator)
        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')

        response = clientTest5.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        # REPLIED : same as INITIATED for the initiator offer, plus the responder should see the sensitive elements of
        #  her offer, but not the initiator
        trade.responder_offer = offer_responder
        trade.status = 'REPLIED'
        trade.save()

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # CANCELLED : same as REPLIED
        trade.status = 'CANCELLED'
        trade.save()

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # DECLINED : same as REPLIED
        trade.status = 'CANCELLED'
        trade.save()

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # ACCEPTED : both players should at least be able to see all sensitive information
        trade.status = 'ACCEPTED'
        trade.save()

        response = self.client.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')
        self.assertNotContains(response, '(Hidden until trade accepted)')
        self.assertNotContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/trade/{}/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, '(Hidden until trade accepted)')
        self.assertNotContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

    def _prepare_trade(self, status, initiator = None, responder = None, initiator_offer = None,
                       responder_offer = None, finalizer = None):
        if initiator is None: initiator = self.loginUser
        if responder is None: responder = self.test5
        if initiator_offer is None: initiator_offer = self.dummy_offer
        return mommy.make_one(Trade, game = self.game, initiator = initiator, responder = responder, finalizer = finalizer,
                              status = status, initiator_offer = initiator_offer, responder_offer = responder_offer)

    def _assertOperationNotAllowed(self, trade_id, operation):
        response = self.client.post("/trade/{}/{}/{}/".format(self.game.id, trade_id, operation), follow=True)
        self.assertEqual(403, response.status_code)

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        _common_setUp(self)

    def test_accept_trade_cards_exchange_is_transactional(self):
        # let's make the responder offer 1 commodity for which he doesn't have any cards
        #  (because it's the last save() in the process, so we can assert that everything else has been rollbacked)
        rih = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser,
                             ownership_date = now())
        offer_initiator = mommy.make_one(Offer, rules = [rih], commodities = [])

        offer_responder = mommy.make_one(Offer, rules = [], commodities = [])
        cih = mommy.make_one(CommodityInHand, game = self.game, player = self.test5, nb_cards = 0)
        tc = mommy.make_one(TradedCommodities, offer = offer_responder, commodityinhand = cih, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc)

        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               status = 'REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/trade/{}/{}/accept/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        # trade : no change
        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("REPLIED", trade.status)
        self.assertIsNone(trade.finalizer)
        self.assertIsNone(trade.closing_date)

        # rule cards : no swapping
        with self.assertRaises(RuleInHand.DoesNotExist):
            RuleInHand.objects.get(game = self.game, player = self.test5, rulecard = rih.rulecard)
        self.assertIsNone(RuleInHand.objects.get(pk = rih.id).abandon_date)

        # commodity cards : no change
        self.assertEqual(1, CommodityInHand.objects.filter(game = self.game, player = self.test5).count())
        self.assertEqual(0, CommodityInHand.objects.get(game = self.game, player = self.test5, commodity = cih.commodity).nb_cards)
        self.assertEqual(0, CommodityInHand.objects.filter(game = self.game, player = self.loginUser).count())

class FormsTest(TestCase):

    def setUp(self):
        self.game = mommy.make_one(Game, players = [], end_date = now() + datetime.timedelta(days = 7))

    #noinspection PyUnusedLocal
    def test_a_rule_offered_by_the_initiator_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        rule_in_hand = mommy.make_one(RuleInHand, game = self.game, ownership_date = now())
        offer = mommy.make_one(Offer, rules = [rule_in_hand], commodities = [])
        pending_trade = mommy.make_one(Trade, game = self.game, status = 'INITIATED', initiator_offer = offer)

        RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
        rulecards_formset = RuleCardsFormSet({'rulecards-TOTAL_FORMS': 1, 'rulecards-INITIAL_FORMS': 1,
                                              'rulecards-0-card_id': rule_in_hand.id, 'rulecards-0-selected_rule': 'on'
                                             }, prefix = 'rulecards')

        self.assertFalse(rulecards_formset.is_valid())
        self.assertIn("A rule card in a pending trade can not be offered in another trade.", rulecards_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_a_rule_offered_by_the_responder_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        rule_in_hand = mommy.make_one(RuleInHand, game = self.game, ownership_date = now())
        offer = mommy.make_one(Offer, rules = [rule_in_hand], commodities = [])
        pending_trade = mommy.make_one(Trade, game = self.game, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make_one(Offer, rules = [], commodities = []))

        RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
        rulecards_formset = RuleCardsFormSet({'rulecards-TOTAL_FORMS': 1, 'rulecards-INITIAL_FORMS': 1,
                                              'rulecards-0-card_id': rule_in_hand.id, 'rulecards-0-selected_rule': 'on'
                                             }, prefix = 'rulecards')

        self.assertFalse(rulecards_formset.is_valid())
        self.assertIn("A rule card in a pending trade can not be offered in another trade.", rulecards_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_commodities_offered_by_the_initiator_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        commodity_in_hand = mommy.make_one(CommodityInHand, game = self.game, nb_cards = 1)
        # see https://github.com/vandersonmota/model_mommy/issues/25
        offer = mommy.make_one(Offer, rules = [], commodities = [])
        traded_commodities = mommy.make_one(TradedCommodities, nb_traded_cards = 1, commodityinhand = commodity_in_hand, offer = offer)
        pending_trade = mommy.make_one(Trade, game = commodity_in_hand.game, status = 'INITIATED', initiator_offer = offer)

        CommodityCardsFormSet = formset_factory(TradeCommodityCardFormParse, formset = BaseCommodityCardFormSet)
        commodities_formset = CommodityCardsFormSet({'commodity-TOTAL_FORMS': 1, 'commodity-INITIAL_FORMS': 1,
                                                     'commodity-0-commodity_id': commodity_in_hand.commodity.id, 'commodity-0-nb_traded_cards': 1,
                                                     }, prefix = 'commodity')
        commodities_formset.set_game(commodity_in_hand.game)
        commodities_formset.set_player(commodity_in_hand.player)

        self.assertFalse(commodities_formset.is_valid())
        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", commodities_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_commodities_offered_by_the_responder_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        commodity_in_hand = mommy.make_one(CommodityInHand, game = self.game, nb_cards = 2)
        # see https://github.com/vandersonmota/model_mommy/issues/25
        offer = mommy.make_one(Offer, rules = [], commodities = [])
        traded_commodities = mommy.make_one(TradedCommodities, nb_traded_cards = 1, commodityinhand = commodity_in_hand, offer = offer)
        pending_trade = mommy.make_one(Trade, game = commodity_in_hand.game, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make_one(Offer, rules = [], commodities = []))

        CommodityCardsFormSet = formset_factory(TradeCommodityCardFormParse, formset = BaseCommodityCardFormSet)
        commodities_formset = CommodityCardsFormSet({'commodity-TOTAL_FORMS': 1, 'commodity-INITIAL_FORMS': 1,
                                                     'commodity-0-commodity_id': commodity_in_hand.commodity.id, 'commodity-0-nb_traded_cards': 2,
                                                     }, prefix = 'commodity')
        commodities_formset.set_game(commodity_in_hand.game)
        commodities_formset.set_player(commodity_in_hand.player)

        self.assertFalse(commodities_formset.is_valid())
        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", commodities_formset._non_form_errors)

    def test_a_trade_with_a_responder_who_has_already_submitted_his_hand_is_forbidden(self):
        ihavesubmitted = mommy.make_one(User, username = 'ihavesubmitted')
        ihavent = mommy.make_one(User, username = 'ihavent')
        mommy.make_one(GamePlayer, game = self.game, player = ihavesubmitted, submit_date = now())
        mommy.make_one(GamePlayer, game = self.game, player = ihavent, submit_date = None)

        form = TradeForm(ihavent, self.game, {'responder': ihavesubmitted.id})
        self.assertFalse(form.is_valid())
        self.assertIn("This player doesn't participate to this game or has already submitted his hand to the game master",
                      form.errors['responder'])