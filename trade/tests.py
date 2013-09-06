import datetime
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, Client, TransactionTestCase
from django.utils.timezone import now
from model_mommy import mommy
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer
from ruleset.models import Ruleset, RuleCard, Commodity
from trade.forms import TradeForm, OfferForm
from trade.models import Offer, Trade, TradedCommodities
from trade.views import _prepare_offer_form, _parse_offer_form, FormInvalidException
from utils.tests import MystradeTestCase

class CreateTradeViewTest(MystradeTestCase):

    def test_create_trade_without_responder_fails_but_keeps_text_fields_and_cards(self):
        cih = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = mommy.make(Commodity), nb_cards = 3)
        rih = RuleInHand.objects.create(game = self.game, player = self.loginUser, rulecard = mommy.make(RuleCard), ownership_date = now())

        response = self._postCreateTrade({'free_information': 'secret!',
                                          'comment': 'a comment',
                                          'commodity_{0}'.format(cih.commodity_id): 2,
                                          'rulecard_{0}'.format(rih.id): 'True'
                                         })
        self.assertEqual(422, response.status_code)
        self.assertFormError(response, 'trade_form', 'responder', 'This field is required.')
        self.assertContains(response, "secret!", status_code = 422)
        self.assertContains(response, "a comment", status_code = 422)
        self.assertContains(response, '<input id="id_rulecard_{0}" name="rulecard_{0}" type="hidden" value="True"'.format(rih.id), status_code = 422)
        self.assertContains(response, '<input id="id_commodity_{0}" name="commodity_{0}" type="hidden" value="2"'.format(cih.commodity_id), status_code = 422)

    def test_create_trade_without_selecting_cards_or_giving_a_free_information_fails_and_keeps_text_fields(self):
        cih = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = mommy.make(Commodity), nb_cards = 3)
        rih = RuleInHand.objects.create(game = self.game, player = self.loginUser, rulecard = mommy.make(RuleCard), ownership_date = now())

        response = self._postCreateTrade({'responder': 4,
                                          'free_information': '',
                                          'comment': 'a comment',
                                          'commodity_{0}'.format(cih.commodity_id): 0,
                                          'rulecard_{0}'.format(rih.id): 'False',
                                         })
        self.assertEqual(422, response.status_code)
        self.assertFormError(response, 'offer_form', None, 'At least one card or one free information should be offered.')
        self.assertContains(response, "a comment", status_code = 422)

    def test_create_trade_is_forbidden_if_you_have_submitted_your_hand(self):
        gameplayer = GamePlayer.objects.get(game = self.game, player = self.loginUser)
        gameplayer.submit_date = now()
        gameplayer.save()

        self._assertIsCreateTradeAllowed(False)

    def test_create_trade_is_forbidden_if_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -1)
        self.game.save()

        self._assertIsCreateTradeAllowed(False)

    def test_create_trade_only_allowed_for_the_game_players(self):
        # most notably: the game master, the admins (when not in the players' list) and the users not in this game are denied
        self._assertIsCreateTradeAllowed(True)

        self.login_as(self.master)
        self._assertIsCreateTradeAllowed(False)

        self.login_as(self.unrelated_user)
        self._assertIsCreateTradeAllowed(False)

        self.login_as(self.admin)
        self._assertIsCreateTradeAllowed(False)

        self.login_as(self.admin_player)
        self._assertIsCreateTradeAllowed(True)

    def _assertIsCreateTradeAllowed(self, create_allowed):
        expected_status = 200 if create_allowed else 403

        response = self.client.get("/trade/{0}/create/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(expected_status, response.status_code)

        cih = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = mommy.make(Commodity), nb_cards = 3)
        rih = RuleInHand.objects.create(game = self.game, player = self.loginUser, rulecard = mommy.make(RuleCard), ownership_date = now())

        response = self._postCreateTrade({'responder': 4,
                                          'free_information': 'secret!',
                                          'comment': 'a comment',
                                          'commodity_{0}'.format(cih.commodity_id): 2,
                                          'rulecard_{0}'.format(rih.id): 'True',
                                         })
        self.assertEqual(expected_status, response.status_code)

    def test_create_trade_complete_save(self):
        ruleset = mommy.make(Ruleset)
        rulecard = mommy.make(RuleCard, ruleset = ruleset, ref_name = 'rulecard_1', public_name = 'rulecard_1')
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = self.loginUser,
                                                 rulecard = rulecard, ownership_date = now())
        commodity = mommy.make(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = self.loginUser,
                                                           commodity = commodity, nb_cards = 2)
        response = self._postCreateTrade({'responder': 4,
                                          'free_information': 'some "secret" info',
                                          'comment': 'a comment',
                                          'rulecard_{0}'.format(rule_in_hand.id): 'True',
                                          'commodity_{0}'.format(commodity.id): 1
                                         })
        self.assertEquals(200, response.status_code)

        trade = Trade.objects.get(game = self.game, initiator__username = 'test2')
        self.assertEqual(4, trade.responder.id)
        self.assertEqual('INITIATED', trade.status)
        self.assertEqual('a comment', trade.initiator_offer.comment)
        self.assertEqual('some "secret" info', trade.initiator_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.initiator_offer.rulecards))
        self.assertEqual([commodity_in_hand], list(trade.initiator_offer.commodities.all()))
        self.assertEqual(1, trade.initiator_offer.tradedcommodities[0].nb_traded_cards)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: You have been offered a trade by test2'.format(self.game.id), email.subject)
        self.assertIn('In game #{0}, test2 has offered you a new trade'.format(self.game.id), email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertIn('- 1 commodity_1 card', email.body)
        self.assertIn('Rule: rulecard_1', email.body)
        self.assertEqual(['test4@test.com'], email.to)

    def test_create_trade_with_reserved_elements_fails(self):
        cih = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = mommy.make(Commodity), nb_cards = 3)
        rih = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = mommy.make(RuleCard))
        # reserving the cards for another trade
        offer = mommy.make(Offer, rules = [rih])
        tc = mommy.make(TradedCommodities, offer = offer, commodityinhand = cih, nb_traded_cards = 2)
        offer.tradedcommodities_set.add(tc)
        other_trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED', initiator_offer = offer)

        response = self._postCreateTrade({'responder': 4,
                                          'rulecard_{0}'.format(rih.id): 'True',
                                          'commodity_{0}'.format(cih.commodity_id): 2,
                                         })
        self.assertFormError(response, 'offer_form', None, 'A rule card in a pending trade can not be offered in another trade.')
        self.assertFormError(response, 'offer_form', None, 'A commodity card in a pending trade can not be offered in another trade.')
        self.assertContains(response, 'A rule card in a pending trade can not be offered in another trade.', status_code = 422)
        self.assertContains(response, 'A commodity card in a pending trade can not be offered in another trade.', status_code = 422)

    def _postCreateTrade(self, data):
        return self.client.post("/trade/{0}/create/".format(self.game.id),
                                data, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # simulate AJAX

class ShowTradeViewTest(MystradeTestCase):

    def test_trade_list_order(self):
        right_now = now()
        trade_accepted = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'ACCEPTED',
                                        initiator_offer = mommy.make(Offer),
                                        creation_date = right_now - datetime.timedelta(days = 1))
        trade_initiated = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                                     initiator_offer = mommy.make(Offer),
                                     creation_date = right_now - datetime.timedelta(days = 2))
        trade_declined = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'DECLINED',
                                        initiator_offer = mommy.make(Offer),
                                        creation_date = right_now - datetime.timedelta(days = 3), finalizer = self.loginUser)
        trade_replied = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'REPLIED',
                                       responder = self.alternativeUser, initiator_offer = mommy.make(Offer),
                                       creation_date = right_now - datetime.timedelta(days = 4))
        trade_cancelled = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'CANCELLED',
                                     initiator_offer = mommy.make(Offer),
                                     creation_date = right_now - datetime.timedelta(days = 5), finalizer = self.loginUser)

        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        trade_list = response.context["trade_list"]
        # ordered by status : pending first, finalized second, and inside both groups, by decreasing creation date
        self._assert_in_trade_list(trade_initiated, trade_list[0])
        self._assert_in_trade_list(trade_replied, trade_list[1])
        self._assert_in_trade_list(trade_accepted, trade_list[2])
        self._assert_in_trade_list(trade_declined, trade_list[3])
        self._assert_in_trade_list(trade_cancelled, trade_list[4])

    def test_trade_list_content_of_a_line(self):
        rulecard1, rulecard2, rulecard3 = mommy.make(RuleCard, _quantity = 3)
        commodity1, commodity2 = mommy.make(Commodity, _quantity = 2)

        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2)
        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 3)

        offer_initiator = mommy.make(Offer, rules = [rih1, rih2], free_information = "secret")
        tc1i = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = cih1, nb_traded_cards = 2)
        offer_initiator.tradedcommodities_set.add(tc1i)

        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'INITIATED', initiator_offer = offer_initiator)

        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertContains(response, "waiting offer from")
        self.assertContains(response, "mini_commodity_card", count = 2)
        self.assertContains(response, 'data-commodity-id="{0}"'.format(cih1.commodity.id), count = 2)
        self.assertContains(response, "rulecard_thumbnail", count = 2)
        self.assertContains(response, 'data-rih-id="{0}"'.format(rih1.id), count = 1)
        self.assertContains(response, 'data-rih-id="{0}"'.format(rih2.id), count = 1)
        self.assertContains(response, "info.png", count = 1)
        self.assertContains(response, "arrow_simple.png", count = 1)
        self.assertContains(response, "(no offer submitted)", count = 1)
        self.assertContains(response, '<a class="list_link_trade" data-trade-id="{0}">Show</a>'.format(trade.id), count = 1)

        trade.status = "REPLIED"
        rih3 = mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = rulecard3)
        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, commodity = commodity2, nb_cards = 1)

        offer_responder = mommy.make(Offer, rules = [rih3])
        tc1r = mommy.make(TradedCommodities, offer = offer_responder, commodityinhand = cih2, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc1r)
        trade.responder_offer = offer_responder
        trade.save()

        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertContains(response, "waiting decision from")
        self.assertContains(response, "mini_commodity_card", count = 3)
        self.assertContains(response, 'data-commodity-id="{0}"'.format(cih2.commodity.id), count = 1)
        self.assertContains(response, "rulecard_thumbnail", count = 3)
        self.assertContains(response, 'data-rih-id="{0}"'.format(rih3.id), count = 1)
        self.assertContains(response, "info.png", count = 1)
        self.assertContains(response, "arrow_simple.png", count = 0)
        self.assertContains(response, "arrow_double.png", count = 1)
        self.assertContains(response, "(no offer submitted)", count = 0)
        self.assertContains(response, '<a class="list_link_trade" data-trade-id="{0}">Show</a>'.format(trade.id), count = 1)

        trade.status = "CANCELLED"
        trade.finalizer = self.loginUser
        trade.save()
        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, "cancelled by")

        trade.status = "DECLINED"
        trade.save()
        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, "declined by")

        trade.status = "ACCEPTED"
        trade.save()
        response = self.client.get("/trade/{0}/list/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertContains(response, "accepted and done")

    def _assert_in_trade_list(self, expected_trade, actual_trade):
        self.assertEqual(expected_trade, actual_trade, msg = "Expected: {0}, found: {1}".format(expected_trade.status, actual_trade.status))

    def test_show_trade_only_allowed_for_authorized_players(self):
        """ Authorized players are : - the initiator
                                     - the responder
                                     - the game master
                                     - admins ("staff" in django terminology)
        """
        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                          status = 'INITIATED', initiator_offer = mommy.make(Offer))

        # the initiator
        response = self._getShowTrade(trade)
        self.assertEqual(200, response.status_code)

        # the responder
        self.login_as(self.alternativeUser)
        response = self._getShowTrade(trade)
        self.assertEqual(200, response.status_code)

        # the game master
        self.login_as(self.master)
        response = self._getShowTrade(trade)
        self.assertEqual(200, response.status_code)

        # an admin
        self.login_as(self.admin)
        response = self._getShowTrade(trade)
        self.assertEqual(200, response.status_code)

        # anybody else
        self.login_as(self.admin_player)
        response = self._getShowTrade(trade)
        self.assertEqual(403, response.status_code)

    def test_buttons_in_show_trade_with_own_initiated_trade(self):
        trade = self._prepare_trade('INITIATED')

        response = self._getShowTrade(trade)
        self.assertContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Reply with your offer</button>')
        self.assertNotContains(response, '<form id="new_offer" data-trade-action="reply" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Decline...</button>')
        self.assertNotContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_INITIATED(self):
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)

        response = self._getShowTrade(trade)

        self.assertNotContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertContains(response, 'Reply with your offer</button>')
        self.assertContains(response, '<form id="new_offer" data-trade-action="reply" data-trade-id="{0}">'.format(trade.id))
        self.assertContains(response, 'Decline...</button>')
        self.assertContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_REPLIED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.alternativeUser, responder = self.loginUser,
                                    responder_offer = mommy.make(Offer))

        response = self._getShowTrade(trade)

        self.assertContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, '<form id="accept_trade" data-trade-action="accept" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Reply with your offer</button>')
        self.assertNotContains(response, '<form id="new_offer" data-trade-action="reply" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Decline...</button>')
        self.assertNotContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_buttons_in_show_trade_for_the_initiator_when_REPLIED(self):
        trade = self._prepare_trade('REPLIED', responder_offer = mommy.make(Offer))

        response = self._getShowTrade(trade)

        self.assertNotContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertContains(response, '<form id="accept_trade" data-trade-action="accept" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Reply with your offer</button>')
        self.assertNotContains(response, '<form id="new_offer" data-trade-action="reply" data-trade-id="{0}">'.format(trade.id))
        self.assertContains(response, 'Decline...</button>')
        self.assertContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_buttons_in_show_trade_with_trade_CANCELLED(self):
        trade = self._prepare_trade('CANCELLED', finalizer = self.alternativeUser)

        response = self._getShowTrade(trade)

        self.assertNotContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, '<form id="accept_trade" data-trade-action="accept" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, 'Decline...</button>')
        self.assertNotContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_buttons_in_show_trade_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('INITIATED')
        response = self._getShowTrade(trade)
        self.assertNotContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))

        trade.responder = self.loginUser
        trade.save()
        response = self._getShowTrade(trade)
        self.assertNotContains(response, '<form id="new_offer" data-trade-action="reply" data-trade-id="{0}">'.format(trade.id))

        trade.status = 'REPLIED'
        trade.save()
        response = self._getShowTrade(trade)
        self.assertNotContains(response, '<form id="cancel_trade" data-trade-action="cancel" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, '<form id="accept_trade" data-trade-action="accept" data-trade-id="{0}">'.format(trade.id))
        self.assertNotContains(response, '<form id="decline_trade" data-trade-action="decline" data-trade-id="{0}">'.format(trade.id))

    def test_decline_reason_displayed_in_show_trade_when_DECLINED(self):
        trade = self._prepare_trade('DECLINED', finalizer = self.alternativeUser)
        response = self._getShowTrade(trade)

        self.assertRegexpMatches(response.content, "declined by <div class=\"game-player\"><a href=\".*\">test5</a>")
        self.assertNotContains(response, "with the following reason given:")

        trade.decline_reason = "Because I do not need it"
        trade.save()

        response = self._getShowTrade(trade)

        self.assertRegexpMatches(response.content, "declined by <div class=\"game-player\"><a href=\".*\">test5</a>")
        self.assertContains(response, "gave the following reason to decline:")
        self.assertContains(response, "Because I do not need it")

    def _prepare_trade(self, status, initiator = None, responder = None, initiator_offer = None,
                       responder_offer = None, finalizer = None):
        if initiator is None: initiator = self.loginUser
        if responder is None: responder = self.alternativeUser
        if initiator_offer is None: initiator_offer = mommy.make(Offer)
        return mommy.make(Trade, game = self.game, initiator = initiator, responder = responder, finalizer = finalizer,
                          status = status, initiator_offer = initiator_offer, responder_offer = responder_offer)

    def _getShowTrade(self, trade):
        return self.client.get("/trade/{0}/{1}/".format(self.game.id, trade.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

class ModifyTradeViewsTest(MystradeTestCase):

    def test_cancel_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{0}/{1}/cancel/".format(self.game.id, 1), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(403, response.status_code)

    def test_cancel_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_cancel(self):
        # trade INITIATED but we're not the initiator
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'cancel')

        # trade REPLIED but we're not the responder
        trade.responder = self.admin_player
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
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)
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
        response = self._assertOperationAllowed(trade.id, "cancel")

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has cancelled the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has cancelled the trade including the following elements', email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_cancel_trade_allowed_and_effective_for_the_responder_for_a_trade_in_status_REPLIED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.alternativeUser, responder = self.loginUser)
        response = self._assertOperationAllowed(trade.id, "cancel")

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has cancelled the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has cancelled the trade including the following elements', email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_reply_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{0}/{1}/reply/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_reply_trade_not_allowed_when_one_is_not_the_responder(self):
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = get_user_model().objects.get(username = 'test6'))
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_not_allowed_for_trades_not_in_status_INITIATED(self):
        trade = self._prepare_trade('ACCEPTED', initiator = self.alternativeUser, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_not_allowed_when_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(days = -5)
        self.game.save()

        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_without_selecting_cards_or_typing_a_free_information_fails(self):
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)
        response = self.client.post("/trade/{0}/{1}/reply/".format(self.game.id, trade.id),
                                    {'rulecard_0': 'False',
                                     'rulecard_1': 'False',
                                     'commodity_0': 0,
                                     'commodity_1': 0,
                                     'commodity_2': 0,
                                     'commodity_3': 0,
                                     'commodity_4': 0,
                                     'free_information': '',
                                     'comment': 'a comment'
                                    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(422, response.status_code)
        self.assertFormError(response, 'offer_form', None, 'At least one card or one free information should be offered.')
        self.assertContains(response, 'At least one card or one free information should be offered.', status_code = 422)

    def test_reply_trade_with_reserved_elements_fails_gracefully(self):
        commodity = mommy.make(Commodity, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = self.loginUser,
                                                           commodity = commodity, nb_cards = 1)
        # reserving the commodity in hand for another trade
        offer_initiator = mommy.make(Offer)
        tc = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = commodity_in_hand, nb_traded_cards = 1)
        offer_initiator.tradedcommodities_set.add(tc)

        other_trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                                 initiator_offer = offer_initiator)

        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)

        response = self.client.post("/trade/{0}/{1}/reply/".format(self.game.id, trade.id),
                                    {'commodity_{0}'.format(commodity.id): 1,
                                     'comment': 'a comment'
                                    }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(422, response.status_code)
        self.assertContains(response, 'a comment</textarea>', status_code = 422)
        self.assertContains(response, 'A commodity card in a pending trade can not be offered in another trade.', status_code = 422)
        self.assertFormError(response, 'offer_form', None, 'A commodity card in a pending trade can not be offered in another trade.')

    def test_reply_trade_complete_save(self):
        ruleset = mommy.make(Ruleset)
        rulecard = mommy.make(RuleCard, ruleset = ruleset)
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = self.loginUser,
                                                 rulecard = rulecard, ownership_date = now())
        commodity = mommy.make(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = self.loginUser,
                                                           commodity = commodity, nb_cards = 2)

        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)

        response = self._assertOperationAllowed(trade.id, "reply",
                                                {'rulecard_{0}'.format(rule_in_hand.id): 'True',
                                                 'commodity_{0}'.format(commodity.id): 2,
                                                 'free_information': 'some "secret" info',
                                                 'comment': 'a comment'
                                                })

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual('REPLIED', trade.status)
        self.assertEqual('a comment', trade.responder_offer.comment)
        self.assertEqual('some "secret" info', trade.responder_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.responder_offer.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.responder_offer.commodities.all()))
        self.assertEqual(2, trade.responder_offer.tradedcommodities[0].nb_traded_cards)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has replied to your trade proposal'.format(self.game.id), email.subject)
        self.assertIn('In game #{0}, test2 has replied to your proposal, with the following offer:'.format(self.game.id), email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_accept_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{0}/{1}/accept/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_accept_trade_not_allowed_when_you_re_not_the_initiator(self):
        # responder
        trade = self._prepare_trade('REPLIED', initiator = self.alternativeUser, responder = self.loginUser)
        self._assertOperationNotAllowed(trade.id, 'accept')

        # someone else
        trade.initiator = get_user_model().objects.get(username = 'test3')
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
        rulecard1, rulecard2 = mommy.make(RuleCard, _quantity = 2)
        commodity1, commodity2, commodity3 = mommy.make(Commodity, _quantity = 3, value = 1)

        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = rulecard2)

        cih1i = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1,
                               nb_cards = 3)
        cih1r = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, commodity = commodity1,
                               nb_cards = 3)
        cih2i = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity2,
                               nb_cards = 2)
        cih3r = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, commodity = commodity3,
                               nb_cards = 2)

        # the initiaor offers rulecard1, 2 commodity1 and 1 commodity2
        offer_initiator = mommy.make(Offer, rules = [rih1])
        tc1i = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = cih1i, nb_traded_cards = 2)
        offer_initiator.tradedcommodities_set.add(tc1i)
        tc2i = mommy.make(TradedCommodities, offer = offer_initiator, commodityinhand = cih2i, nb_traded_cards = 1)
        offer_initiator.tradedcommodities_set.add(tc2i)

        # the responder offers rulecard2, 1 commodity1 and 2 commodity3
        offer_responder = mommy.make(Offer, rules = [rih2])
        tc1r = mommy.make(TradedCommodities, offer = offer_responder, commodityinhand = cih1r, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc1r)
        tc3r = mommy.make(TradedCommodities, offer = offer_responder, commodityinhand = cih3r, nb_traded_cards = 2)
        offer_responder.tradedcommodities_set.add(tc3r)

        trade = self._prepare_trade('REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self._assertOperationAllowed(trade.id, "accept")

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
        hand_responder = RuleInHand.objects.filter(game = self.game, player = self.alternativeUser, abandon_date__isnull = True)
        self.assertEqual(1, hand_responder.count())
        self.assertEqual(rulecard1, hand_responder[0].rulecard)

        # commodity cards : the initiator should now own 2 commodity1, 1 commodity2 and 2 commodity3, wherea
        #  the responder should own 4 commodity1, 1 commodity2 and no commodity3
        self.assertEqual(2, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity1).nb_cards)
        self.assertEqual(1, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity2).nb_cards)
        self.assertEqual(2, CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity3).nb_cards)

        self.assertEqual(4, CommodityInHand.objects.get(game = self.game, player = self.alternativeUser, commodity = commodity1).nb_cards)
        self.assertEqual(1, CommodityInHand.objects.get(game = self.game, player = self.alternativeUser, commodity = commodity2).nb_cards)
        self.assertEqual(0, CommodityInHand.objects.get(game = self.game, player = self.alternativeUser, commodity = commodity3).nb_cards)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has accepted the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has accepted your offer.'.format(self.game.id), email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_decline_trade_not_allowed_in_GET(self):
        response = self.client.get("/trade/{0}/{1}/decline/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_decline_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_decline(self):
        # trade INITIATED but we're not the responder
        trade = self._prepare_trade('INITIATED')
        self._assertOperationNotAllowed(trade.id, 'decline')

        # trade REPLIED but we're not the initiator
        trade.initiator = self.alternativeUser
        trade.responder = self.loginUser
        trade.status = 'REPLIED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

    def test_decline_trade_not_allowed_for_the_responder_for_trades_not_in_status_INITIATED(self):
        trade = self._prepare_trade('REPLIED', initiator = self.alternativeUser, responder = self.loginUser)
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
        trade = self._prepare_trade('INITIATED', initiator = self.alternativeUser, responder = self.loginUser)
        response = self._assertOperationAllowed(trade.id, "decline", {'decline_reason': "this is my reason"})

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("DECLINED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)
        self.assertEqual("this is my reason", trade.decline_reason)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has declined the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has declined your offer.'.format(self.game.id), email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertIn("this is my reason", email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def test_decline_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_REPLIED(self):
        trade = self._prepare_trade('REPLIED')
        response = self._assertOperationAllowed(trade.id, "decline", {'decline_reason': "this is my reason"})

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("DECLINED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)
        self.assertEqual("this is my reason", trade.decline_reason)

        # notification email sent
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[MysTrade] Game #{0}: test2 has declined the trade'.format(self.game.id), email.subject)
        self.assertIn('test2 has declined your offer.'.format(self.game.id), email.body)
        self.assertIn('/trade/{0}/{1}/'.format(self.game.id, trade.id), email.body)
        self.assertIn("this is my reason", email.body)
        self.assertEqual(['test5@test.com'], email.to)

    def _prepare_trade(self, status, initiator = None, responder = None, initiator_offer = None,
                       responder_offer = None, finalizer = None):
        if initiator is None: initiator = self.loginUser
        if responder is None: responder = self.alternativeUser
        if initiator_offer is None: initiator_offer = mommy.make(Offer)
        return mommy.make(Trade, game = self.game, initiator = initiator, responder = responder, finalizer = finalizer,
                              status = status, initiator_offer = initiator_offer, responder_offer = responder_offer)

    def _assertOperationNotAllowed(self, trade_id, operation):
        response = self.client.post("/trade/{0}/{1}/{2}/".format(self.game.id, trade_id, operation), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(403, response.status_code)

    def _assertOperationAllowed(self, trade_id, operation, data = {}):
        response = self.client.post("/trade/{0}/{1}/{2}/".format(self.game.id, trade_id, operation),
                                    data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(200, response.status_code)
        return response

class SensitiveTradeElementsTest(MystradeTestCase):
    """ The free information should not be shown to the other player until/unless the trade has reached the status ACCEPTED.
        The game master can always see them though. """

    def setUp(self):
        super(SensitiveTradeElementsTest, self).setUp()

        self.clientInitiator = self.client
        self.clientResponder = Client()
        self.assertTrue(self.clientResponder.login(username = self.alternativeUser.username, password = 'test'))
        self.clientMaster = Client()
        self.assertTrue(self.clientMaster.login(username = self.master.username, password = 'test'))

        rih_initiator = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = mommy.make(RuleCard))
        rih_responder = mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = mommy.make(RuleCard))
        self.offer_initiator = mommy.make(Offer, rules = [rih_initiator], free_information = 'this is sensitive')
        self.offer_responder = mommy.make(Offer, rules = [rih_responder], free_information = 'these are sensitive')

    def test_display_of_sensitive_trade_elements_in_status_INITIATED(self):
        """ the initiator should see the sensitive elements of his offer, the responder should not """
        self._prepare_trade('INITIATED')

        self._assert_sensitive_elements(client = self.clientInitiator, initiator_elements = True)
        self._assert_sensitive_elements(client = self.clientResponder, initiator_elements = False)
        self._assert_sensitive_elements(client = self.clientMaster, initiator_elements = True)

    def test_display_of_sensitive_trade_elements_in_status_REPLIED(self):
        """same as INITIATED for the initiator offer, plus the responder should see the sensitive elements of
           her offer, but not the initiator
        """
        self._prepare_trade('REPLIED')

        self._assert_sensitive_elements(client = self.clientInitiator, initiator_elements = True, responder_elements = False)
        self._assert_sensitive_elements(client = self.clientResponder, initiator_elements = False, responder_elements = True)
        self._assert_sensitive_elements(client = self.clientMaster, initiator_elements = True, responder_elements = True)

    def test_display_of_sensitive_trade_elements_in_status_CANCELLED(self):
        """ CANCELLED : same as REPLIED """
        self._prepare_trade('CANCELLED')

        self._assert_sensitive_elements(client = self.clientInitiator, initiator_elements = True, responder_elements = False)
        self._assert_sensitive_elements(client = self.clientResponder, initiator_elements = False, responder_elements = True)
        self._assert_sensitive_elements(client = self.clientMaster, initiator_elements = True, responder_elements = True)

    def test_display_of_sensitive_trade_elements_in_status_DECLINED(self):
        """ DECLINED : same as REPLIED """
        self._prepare_trade('DECLINED')

        self._assert_sensitive_elements(client = self.clientInitiator, initiator_elements = True, responder_elements = False)
        self._assert_sensitive_elements(client = self.clientResponder, initiator_elements = False, responder_elements = True)
        self._assert_sensitive_elements(client = self.clientMaster, initiator_elements = True, responder_elements = True)

    def test_display_of_sensitive_trade_elements_in_status_ACCEPTED(self):
        """ ACCEPTED : both players should at least be able to see all sensitive information """
        self._prepare_trade('ACCEPTED')

        self._assert_sensitive_elements(client = self.clientInitiator, initiator_elements = True, responder_elements = True)
        self._assert_sensitive_elements(client = self.clientResponder, initiator_elements = True, responder_elements = True)
        self._assert_sensitive_elements(client = self.clientMaster, initiator_elements = True, responder_elements = True)

    def _prepare_trade(self, status):
        self.trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = status, initiator_offer = self.offer_initiator,
                                responder_offer = self.offer_responder if status <> 'INITIATED' else None,
                                finalizer = self.loginUser if status in ['CANCELLED', 'DECLINED', 'ACCEPTED'] else None)

    def _assert_sensitive_elements(self, client, initiator_elements = None, responder_elements = None):
        response = client.get("/trade/{0}/{1}/".format(self.game.id, self.trade.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        if initiator_elements is not None:
            if initiator_elements:
                self.assertContains(response, 'this is sensitive')
            else:
                self.assertNotContains(response, 'this is sensitive')
        if responder_elements is not None:
            if responder_elements:
                self.assertContains(response, 'these are sensitive')
            else:
                self.assertNotContains(response, 'these are sensitive')
        if initiator_elements == False or responder_elements == False:
            self.assertContains(response, 'Some information(s), hidden until trade accepted by both players.')
        else:
            self.assertNotContains(response, 'Some information(s), hidden until trade accepted by both players.')

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['test_users.json', # from profile app
                'test_games.json']

    def setUp(self):
        self.game =             Game.objects.get(id = 1)
        self.master =           self.game.master
        self.loginUser =        get_user_model().objects.get(username = "test2")
        self.alternativeUser =  get_user_model().objects.get(username = 'test5')

        self.client.login(username = self.loginUser.username, password = 'test')

    def test_accept_trade_cards_exchange_is_transactional(self):
        # let's make the responder offer 1 commodity for which he doesn't have any cards
        #  (because it's the last save() in the process, so we can assert that everything else has been rollbacked)
        rih = mommy.make(RuleInHand, game = self.game, player = self.loginUser)
        offer_initiator = mommy.make(Offer, rules = [rih])

        offer_responder = mommy.make(Offer)
        cih = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, nb_cards = 0)
        tc = mommy.make(TradedCommodities, offer = offer_responder, commodityinhand = cih, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc)

        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                               status = 'REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/trade/{0}/{1}/accept/".format(self.game.id, trade.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(200, response.status_code)

        # trade : no change
        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("REPLIED", trade.status)
        self.assertIsNone(trade.finalizer)
        self.assertIsNone(trade.closing_date)

        # rule cards : no swapping
        with self.assertRaises(RuleInHand.DoesNotExist):
            RuleInHand.objects.get(game = self.game, player = self.alternativeUser, rulecard = rih.rulecard)
        self.assertIsNone(RuleInHand.objects.get(pk = rih.id).abandon_date)

        # commodity cards : no change
        self.assertEqual(1, CommodityInHand.objects.filter(game = self.game, player = self.alternativeUser).count())
        self.assertEqual(0, CommodityInHand.objects.get(game = self.game, player = self.alternativeUser, commodity = cih.commodity).nb_cards)
        self.assertEqual(0, CommodityInHand.objects.filter(game = self.game, player = self.loginUser).count())

class FormsTest(MystradeTestCase):

    def test_prepare_offer_form_sets_up_the_correct_cards_excluding_those_in_pending_trades(self):
        rulecard1, rulecard2, rulecard3 = mommy.make(RuleCard, _quantity = 3)
        commodity1, commodity2 = mommy.make(Commodity, _quantity = 2)

        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2)
        rih3 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard3)
        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 3)
        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 2)

        # rulecard1 and 1 card of commodity1 are in the initiator offer of a pending trade
        offer1 = mommy.make(Offer, rules = [rih1])
        tc1 = mommy.make(TradedCommodities, offer = offer1, commodityinhand = cih1, nb_traded_cards = 1)
        offer1.tradedcommodities_set.add(tc1)
        trade1 = self._prepare_trade('INITIATED', initiator_offer = offer1)
        # rulecard2 and 1 card of commodity1 were in the initiator offer of a finalized trade
        offer2 = mommy.make(Offer, rules = [rih2])
        tc2 = mommy.make(TradedCommodities, offer = offer2, commodityinhand = cih1, nb_traded_cards = 1)
        offer2.tradedcommodities_set.add(tc2)
        trade2 = self._prepare_trade('CANCELLED', initiator_offer = offer2, finalizer = self.loginUser)
        # rulecard3 and 1 card of commodity 2 are in the responder offer of a pending trade
        offer3 = mommy.make(Offer, rules = [rih3])
        tc3 = mommy.make(TradedCommodities, offer = offer3, commodityinhand = cih2, nb_traded_cards = 1)
        offer3.tradedcommodities_set.add(tc3)
        trade1 = self._prepare_trade('REPLIED', initiator = self.alternativeUser, responder = self.loginUser, responder_offer = offer3)

        request = RequestFactory().get("/trade/{0}/create/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.loginUser
        offer_form = _prepare_offer_form(request, self.game, selected_rulecards= [rih1, rih2], selected_commodities = {cih1: 1})

        self.assertNotIn('rulecard_{0}'.format(rih1.id), offer_form.initial.keys()) # in a pending trade, so not in the prepared form
        self.assertEqual(True, offer_form.initial.get('rulecard_{0}'.format(rih2.id))) # in a finalized trade, so included in the form
        self.assertNotIn('rulecard_{0}'.format(rih3.id), offer_form.initial.keys()) # in a pending trade, so not in the prepared form

        self.assertEqual(1, offer_form.initial.get('commodity_{0}'.format(commodity1.id)))
        self.assertEqual(0, offer_form.initial.get('commodity_{0}'.format(commodity2.id)))

    def test_parse_offer_form_detects_rule_selected_but_in_a_pending_trade_in_initiator_offer(self):
        rule_in_hand = mommy.make(RuleInHand, game = self.game, player = self.loginUser)
        offer = mommy.make(Offer, rules = [rule_in_hand])
        pending_trade = mommy.make(Trade, game = self.game, status = 'INITIATED', initiator_offer = offer)

        request = RequestFactory().post("/trade/{0}/create/".format(self.game.id),
                                        {'rulecard_{0}'.format(rule_in_hand.id): "True"},
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.loginUser
        with self.assertRaises(FormInvalidException) as context_manager:
            offer_form = _parse_offer_form(request, self.game)

        self.assertIn("A rule card in a pending trade can not be offered in another trade.", context_manager.exception.formdata['offer_errors'])

    def test_parse_offer_form_detects_rule_selected_but_in_a_pending_trade_in_responder_offer(self):
        rule_in_hand = mommy.make(RuleInHand, game = self.game, player = self.loginUser)
        offer = mommy.make(Offer, rules = [rule_in_hand])
        pending_trade = mommy.make(Trade, game = self.game, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make(Offer))

        request = RequestFactory().post("/trade/{0}/create/".format(self.game.id),
                                        {'rulecard_{0}'.format(rule_in_hand.id): "True"},
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.loginUser
        with self.assertRaises(FormInvalidException) as context_manager:
            offer_form = _parse_offer_form(request, self.game)

        self.assertIn("A rule card in a pending trade can not be offered in another trade.", context_manager.exception.formdata['offer_errors'])

    def test_parse_offer_form_detects_commodity_selected_but_in_a_pending_trade_in_initiator_offer(self):
        commodity_in_hand = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 1)
        offer = mommy.make(Offer)
        traded_commodities = mommy.make(TradedCommodities, nb_traded_cards = 1, commodityinhand = commodity_in_hand, offer = offer)
        pending_trade = mommy.make(Trade, game = commodity_in_hand.game, status = 'INITIATED', initiator_offer = offer)

        request = RequestFactory().post("/trade/{0}/create/".format(self.game.id),
                                        {'commodity_{0}'.format(commodity_in_hand.commodity.id): 1},
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.loginUser
        with self.assertRaises(FormInvalidException) as context_manager:
            offer_form = _parse_offer_form(request, self.game)

        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", context_manager.exception.formdata['offer_errors'])

    def test_parse_offer_form_detects_commodity_selected_but_in_a_pending_trade_in_responder_offer(self):
        commodity_in_hand = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, nb_cards = 2)
        offer = mommy.make(Offer)
        traded_commodities = mommy.make(TradedCommodities, nb_traded_cards = 1, commodityinhand = commodity_in_hand, offer = offer)
        pending_trade = mommy.make(Trade, game = commodity_in_hand.game, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make(Offer))

        request = RequestFactory().post("/trade/{0}/create/".format(self.game.id),
                                        {'commodity_{0}'.format(commodity_in_hand.commodity.id): 2},
                                        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.loginUser
        with self.assertRaises(FormInvalidException) as context_manager:
            offer_form = _parse_offer_form(request, self.game)

        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", context_manager.exception.formdata['offer_errors'])

    def test_a_trade_with_a_responder_who_has_already_submitted_his_hand_is_forbidden(self):
        ihavesubmitted = mommy.make(get_user_model(), username = 'ihavesubmitted')
        ihavent = mommy.make(get_user_model(), username = 'ihavent')
        mommy.make(GamePlayer, game = self.game, player = ihavesubmitted, submit_date = now())
        mommy.make(GamePlayer, game = self.game, player = ihavent, submit_date = None)

        form = TradeForm(ihavent, self.game, {'responder': ihavesubmitted.id})
        self.assertFalse(form.is_valid())
        self.assertIn("This player doesn't participate to this game or has already submitted his hand to the game master",
                      form.errors['responder'])

    def test_an_offer_with_only_a_free_information_is_accepted(self):
        form = OfferForm(data = { 'free_information': 'hello world' }, commodities = {}, rulecards = [])
        self.assertTrue(form.is_valid())

    def test_an_offer_with_no_cards_and_no_free_information_is_forbidden(self):
        form = OfferForm(data = {}, commodities = {}, rulecards = [])
        self.assertFalse(form.is_valid())
        self.assertIn("At least one card or one free information should be offered.", form.errors['__all__'])

    def _prepare_trade(self, status, initiator = None, responder = None, initiator_offer = None,
                       responder_offer = None, finalizer = None):
        if initiator is None: initiator = self.loginUser
        if responder is None: responder = self.alternativeUser
        if initiator_offer is None: initiator_offer = mommy.make(Offer)
        return mommy.make(Trade, game = self.game, initiator = initiator, responder = responder, finalizer = finalizer,
                          status = status, initiator_offer = initiator_offer, responder_offer = responder_offer)

class TradeModelsTest(MystradeTestCase):

    def test_trade_is_pending(self):
        self.assertTrue(Trade(status = 'INITIATED').is_pending())
        self.assertTrue(Trade(status = 'REPLIED').is_pending())
        self.assertFalse(Trade(status = 'ACCEPTED').is_pending())
        self.assertFalse(Trade(status = 'DECLINED').is_pending())
        self.assertFalse(Trade(status = 'CANCELLED').is_pending())

    def test_trade_abort(self):
        self._test_trade_abort_for_status_and_finalizer("INITIATED", "CANCELLED", self.loginUser)
        self._test_trade_abort_for_status_and_finalizer("REPLIED", "DECLINED", self.loginUser)
        self._test_trade_abort_for_status_and_finalizer("INITIATED", "DECLINED", self.alternativeUser)
        self._test_trade_abort_for_status_and_finalizer("REPLIED", "CANCELLED", self.alternativeUser)

    def _test_trade_abort_for_status_and_finalizer(self, current_status, expected_status, finalizer):
        closing_date = now()
        trade = mommy.prepare(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                              status = current_status, finalizer = None, closing_date = None)
        trade.abort(finalizer, closing_date)
        try:
            trade_db = Trade.objects.get(pk = trade.id)
            self.assertEqual(expected_status, trade_db.status)
            self.assertEqual(finalizer, trade_db.finalizer)
            self.assertEqual(closing_date, trade_db.closing_date)
        except Trade.DoesNotExist:
            self.fail("Trade should have been saved")
