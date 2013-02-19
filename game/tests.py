import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Sum
from django.forms.formsets import formset_factory
from django.test import TestCase, RequestFactory, Client, TransactionTestCase
from django.utils.timezone import get_default_timezone
from model_mommy import mommy

from game.deal import InappropriateDealingException, RuleCardDealer, deal_cards, \
    prepare_deck, dispatch_cards, CommodityCardDealer
from game.forms import validate_number_of_players, validate_dates, RuleCardFormParse, BaseRuleCardsFormSet, CommodityCardFormParse, BaseCommodityCardFormSet
from game.models import Game, RuleInHand, CommodityInHand, Trade, TradedCommodities, Offer
from game.views import _prepare_offer_forms
from scoring.models import Ruleset, RuleCard, Commodity

class GameAndWelcomeViewsTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.testUserCanCreate = User.objects.get(username = 'test1')
        self.testUsersNoCreate = User.objects.exclude(user_permissions__codename = "add_game")
        self.client.login(username = 'test1', password = 'test')

    def test_create_game_only_with_the_permission(self):
        # initially logged as testCanCreate
        response = self.client.get("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.assertTrue(self.client.login(username = 'test9', password = 'test'))
        response = self.client.get("/game/create/")
        self.assertEqual(302, response.status_code)
        self.client.logout()

    def test_create_game_without_dates_fails(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date': '', 'end_date': '11/13/2012 00:15'})
        self.assertFormError(response, 'form', 'start_date', 'This field is required.')

        response = self.client.post("/game/create/", {'ruleset': 1, 'start_date':'11/10/2012 15:30', 'end_date': ''})
        self.assertFormError(response, 'form', 'end_date', 'This field is required.')

    def test_create_game_without_enough_players(self):
        response = self.client.post("/game/create/", {'ruleset': 1, 
                                                      'start_date': '11/10/2012 18:30', 
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': self.testUsersNoCreate[0].id})
        self.assertFormError(response, 'form', None, 'Please select at least 3 players (as many as there are mandatory rule cards in this ruleset).')

    def test_create_game_first_page(self):
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate]})
        self.assertRedirects(response, "/game/rules/")
        self.assertEqual(1, self.client.session['ruleset'].id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), self.client.session['start_date'])
        self.assertEqual(datetime.datetime(2012, 11, 13, 00, 15, tzinfo = get_default_timezone()), self.client.session['end_date'])
        self.assertListEqual(list(self.testUsersNoCreate), self.client.session['players'])

    def test_access_rules_with_incomplete_session_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session.save()
        response = self.client.get("/game/rules/")
        self.assertRedirects(response, "/game/create/")
 
    def test_access_rules_without_enough_players_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = [self.testUsersNoCreate[0]]
        session.save()
        response = self.client.get("/game/rules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_rules_with_invalid_dates_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2011 00:15'
        session['players'] = [self.testUsersNoCreate[0]]
        session.save()
        response = self.client.get("/game/rules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_rules(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = self.testUsersNoCreate
        session.save()
        response = self.client.get("/game/rules/")
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'game/rules.html')

    def test_create_game_with_too_many_rulecards(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = [player.id for player in self.testUsersNoCreate][:4] # only 4 players
        session.save()
        response = self.client.post("/game/rules/",
                                    {'form-TOTAL_FORMS': 15, 'form-INITIAL_FORMS': 15,
                                     'form-0-card_id': 1, 'form-0-selected_rule': 'on',
                                     'form-1-card_id': 2, 'form-1-selected_rule': 'on',
                                     'form-2-card_id': 3, 'form-2-selected_rule': 'on',
                                     'form-3-card_id': 4,
                                     'form-4-card_id': 5,
                                     'form-5-card_id': 6,
                                     'form-6-card_id': 7,
                                     'form-7-card_id': 8,
                                     'form-8-card_id': 9,
                                     'form-9-card_id': 10, 'form-9-selected_rule': 'on',
                                     'form-10-card_id': 11,
                                     'form-11-card_id': 12,
                                     'form-12-card_id': 13, 'form-12-selected_rule': 'on',
                                     'form-13-card_id': 14,
                                     'form-14-card_id': 15
                                    })
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'game/rules.html')
        self.assertEqual("Please select at most 4 rule cards (including the mandatory ones)", response.context['error'])

    def test_create_game_complete_save_and_clean_session(self):
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate][:4]})
        self.assertRedirects(response, "/game/rules/")
        response = self.client.post("/game/rules/",
                                    {'form-TOTAL_FORMS': 15, 'form-INITIAL_FORMS': 15,
                                     'form-0-card_id': 1, 'form-0-selected_rule': 'on',
                                     'form-1-card_id': 2, 'form-1-selected_rule': 'on',
                                     'form-2-card_id': 3, 'form-2-selected_rule': 'on',
                                     'form-3-card_id': 4,
                                     'form-4-card_id': 5,
                                     'form-5-card_id': 6,
                                     'form-6-card_id': 7,
                                     'form-7-card_id': 8,
                                     'form-8-card_id': 9, 'form-8-selected_rule': 'on',
                                     'form-9-card_id': 10,
                                     'form-10-card_id': 11,
                                     'form-11-card_id': 12,
                                     'form-12-card_id': 13,
                                     'form-13-card_id': 14,
                                     'form-14-card_id': 15
                                    })
        self.assertRedirects(response, "/game/")

        created_game = Game.objects.get(master = self.testUserCanCreate.id)
        self.assertEqual(1, created_game.ruleset.id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), created_game.start_date)
        self.assertEqual(datetime.datetime(2012, 11, 13, 00, 15, tzinfo = get_default_timezone()), created_game.end_date)
        self.assertEqual(list(self.testUsersNoCreate)[:4], list(created_game.players.all()))
        self.assertListEqual([1, 2, 3, 9], [rule.id for rule in created_game.rules.all()])
        self.assertFalse('ruleset' in self.client.session)
        self.assertFalse('start_date' in self.client.session)
        self.assertFalse('end_date' in self.client.session)
        self.assertFalse('players' in self.client.session)
        self.assertFalse('profiles' in self.client.session)

    def test_welcome_needs_login(self):
        response = self.client.get(reverse("welcome"))
        self.assertEqual(200, response.status_code)

        self.client.logout()
        response = self.client.get(reverse("welcome"))
        self.assertEqual(302, response.status_code)

    def test_welcome_games_query(self):
        ruleset = Ruleset.objects.get(id = 1)
        game1 = Game.objects.create(ruleset = ruleset, master = self.testUserCanCreate,
                                    end_date = datetime.datetime(2022, 11, 1, 12, 0, 0, tzinfo = get_default_timezone()))
        for user in self.testUsersNoCreate: game1.players.add(user)
        game2 = Game.objects.create(ruleset = ruleset, master = self.testUsersNoCreate[0],
                                    end_date = datetime.datetime(2022, 11, 3, 12, 0, 0, tzinfo = get_default_timezone()))
        game2.players.add(self.testUserCanCreate)
        game2.players.add(self.testUsersNoCreate[1])
        game3 = Game.objects.create(ruleset = ruleset, master = self.testUsersNoCreate[0],
                                    end_date = datetime.datetime(2022, 11, 5, 12, 0, 0, tzinfo = get_default_timezone()))
        game3.players.add(self.testUsersNoCreate[1])
        game3.players.add(self.testUsersNoCreate[2])

        response = self.client.get(reverse("welcome"))
        self.assertEqual(200, response.status_code)
        self.assertListEqual([game2, game1], list(response.context['games']))
        self.assertNotIn(game3, response.context['games'])

class ShowHandViewTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'),
                                   players = User.objects.exclude(username = 'test1'))
        self.dummy_offer = mommy.make_one(Offer, rules = [], commodities = [])
        self.loginUser = User.objects.get(username = 'test2')
        self.test5 = User.objects.get(username = 'test5')
        self.client.login(username = 'test2', password = 'test')

    def test_show_hand_doesnt_show_commodities_with_no_cards(self):
        commodity1 = mommy.make_one(Commodity, name = 'Commodity#1')
        commodity2 = mommy.make_one(Commodity, name = 'Commodity#2')
        cih1 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 1)
        cih2 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 0)

        response = self.client.get("/game/{}/hand/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">Commodity#1</div>')
        self.assertNotContains(response, '<div class="card_name">Commodity#2</div>')

    def test_see_free_informations_from_ACCEPTED_trades_in_show_hand(self):
        offer1_from_me_as_initiator = mommy.make_one(Offer, rules = [], commodities = [], free_information = "I don't need to see that 1")
        offer1_from_other_as_responder = mommy.make_one(Offer, rules = [], commodities = [], free_information = "Show me this 1")
        trade1 = mommy.make_one(Trade, initiator = self.loginUser, responder = self.test5, status = 'ACCEPTED',
                                initiator_offer = offer1_from_me_as_initiator, responder_offer = offer1_from_other_as_responder)

        offer2_from_other_as_initiator = mommy.make_one(Offer, rules = [], commodities = [], free_information = "Show me this 2")
        trade2 = mommy.make_one(Trade, initiator = self.test5, responder = self.loginUser, status = 'ACCEPTED',
                                initiator_offer = offer2_from_other_as_initiator, responder_offer = self.dummy_offer)

        offer3_from_other_as_responder = mommy.make_one(Offer, rules = [], commodities = [], free_information = "I don't need to see that 3")
        trade3 = mommy.make_one(Trade, initiator = self.loginUser, responder = self.test5, status = 'DECLINED',
                                initiator_offer = self.dummy_offer, responder_offer = offer3_from_other_as_responder)

        response = self.client.get("/game/{}/hand/".format(self.game.id))

        self.assertContains(response, "Show me this 1")
        self.assertContains(response, "Show me this 2")
        self.assertNotContains(response, "I don't need to see that 1")
        self.assertNotContains(response, "I don't need to see that 3")

class TradeViewsTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'),
                                   players = User.objects.exclude(username = 'test1'))
        self.dummy_offer = mommy.make_one(Offer, rules = [], commodities = [])
        self.loginUser = User.objects.get(username = 'test2')
        self.test5 = User.objects.get(username = 'test5')
        self.client.login(username = 'test2', password = 'test')

    def test_create_trade_without_responder_fails(self):
        response = self.client.post("/game/{}/trade/create/".format(self.game.id),
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
        response = self.client.post("/game/{}/trade/create/".format(self.game.id),
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

    def test_create_trade_complete_save(self):
        ruleset = mommy.make_one(Ruleset)
        rulecard = mommy.make_one(RuleCard, ruleset = ruleset, ref_name = 'rulecard_1')
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = self.loginUser,
                                                 rulecard = rulecard, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        commodity = mommy.make_one(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = self.loginUser,
                                                           commodity = commodity, nb_cards = 2)
        response = self.client.post("/game/{}/trade/create/".format(self.game.id),
                                    {'responder': 4,
                                     'rulecards-TOTAL_FORMS': 1,               'rulecards-INITIAL_FORMS': 1,
                                     'rulecards-0-card_id': rule_in_hand.id,   'rulecards-0-selected_rule': 'on',
                                     'commodity-TOTAL_FORMS': 1,               'commodity-INITIAL_FORMS': 1,
                                     'commodity-0-commodity_id': commodity.id, 'commodity-0-nb_traded_cards': 1,
                                     'free_information': 'some "secret" info',
                                     'comment': 'a comment'
                                    })
        self.assertRedirects(response, "/game/{}/trades/".format(self.game.id))

        trade = Trade.objects.get(game = self.game, initiator__username = 'test2')
        self.assertEqual(4, trade.responder.id)
        self.assertEqual('INITIATED', trade.status)
        self.assertEqual('a comment', trade.initiator_offer.comment)
        self.assertEqual('some "secret" info', trade.initiator_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.initiator_offer.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.initiator_offer.commodities.all()))
        self.assertEqual(1, trade.initiator_offer.tradedcommodities_set.all()[0].nb_traded_cards)

    def test_create_trade_page_doesnt_show_commodities_with_no_cards(self):
        commodity1 = mommy.make_one(Commodity, name = 'Commodity#1')
        commodity2 = mommy.make_one(Commodity, name = 'Commodity#2')
        cih1 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 1)
        cih2 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 0)

        response = self.client.get("/game/{}/trade/create/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">Commodity#1</div>')
        self.assertNotContains(response, '<div class="card_name">Commodity#2</div>')

    #noinspection PyUnusedLocal
    def test_trade_list(self):
        right_now = datetime.datetime.now(tz = get_default_timezone())
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

        response = self.client.get("/game/{}/trades/".format(self.game.id))

        self.assertContains(response, "submitted 1 day ago")
        self.assertContains(response, "cancelled by <strong>you</strong> 2 days ago")
        self.assertContains(response, "accepted 3 days ago")
        self.assertContains(response, "declined by <strong>you</strong> 4 days ago")
        self.assertContains(response, "offered 5 days ago")
        self.assertContains(response, "response submitted by test5")

    def test_show_trade_only_allowed_for_authorized_players(self):
        """ Authorized players are : - the initiator
                                     - the responder
                                     - the game master
                                     - admins ("staff" in django terminology)
        """
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               status = 'INITIATED', initiator_offer = self.dummy_offer)

        # the initiator
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # the responder
        self.assertTrue(self.client.login(username = 'test5', password = 'test'))
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # the game master
        self.assertTrue(self.client.login(username = 'test1', password = 'test'))
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertEqual(200, response.status_code)

        # an admin
        self.assertTrue(self.client.login(username = 'admin', password = 'test'))
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id), follow = True)
        self.assertEqual(200, response.status_code)

        # anybody else
        self.assertTrue(self.client.login(username = 'test3', password = 'test'))
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertEqual(403, response.status_code)

    def test_buttons_in_show_trade_with_own_initiated_trade(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                               initiator_offer = self.dummy_offer)

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))

        self.assertContains(response, 'form action="/game/{}/trade/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/reply/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
                               responder = self.loginUser, status = 'INITIATED', initiator_offer = self.dummy_offer)

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, 'form action="/game/{}/trade/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertContains(response, '<form action="/game/{}/trade/{}/reply/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertContains(response, '<form action="/game/{}/trade/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_responder_when_REPLIED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
                               responder = self.loginUser, status = 'REPLIED', initiator_offer = self.dummy_offer)

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))

        self.assertContains(response, '<form action="/game/{}/trade/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/accept/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="reply">Reply with your offer</button>')
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/reply/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_for_the_initiator_when_REPLIED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser,
                               responder = self.test5, status = 'REPLIED', initiator_offer = self.dummy_offer)

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, '<form action="/game/{}/trade/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertContains(response, '<form action="/game/{}/trade/{}/accept/"'.format(self.game.id, trade.id))
        #self.assertContains(response, '<button type="button" id="decline">Decline</button>')
        #self.assertContains(response, '<form action="/game/{}/trade/{}/decline/"'.format(self.game.id, trade.id))

    def test_buttons_in_show_trade_with_trade_CANCELLED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'CANCELLED',
                               initiator_offer = self.dummy_offer)

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))

        self.assertNotContains(response, 'form action="/game/{}/trade/{}/cancel/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/accept/"'.format(self.game.id, trade.id))
        self.assertNotContains(response, '<button type="button" id="decline">Decline</button>')
        self.assertNotContains(response, '<form action="/game/{}/trade/{}/decline/"'.format(self.game.id, trade.id))

    def test_cancel_trade_not_allowed_in_GET(self):
        response = self.client.get("/game/{}/trade/{}/cancel/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_cancel_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_cancel(self):
        # trade INITIATED but we're not the initiator
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, status = 'INITIATED',
                               initiator_offer = self.dummy_offer)
        self._assertOperationNotAllowed(trade.id, 'cancel')

        # trade REPLIED but we're not the responder
        trade.responder = User.objects.get(username = 'test3')
        trade.status = 'REPLIED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'cancel')

    def test_cancel_trade_not_allowed_for_the_initiator_for_trades_not_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'REPLIED',
                               initiator_offer = self.dummy_offer)
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
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser,
                               status = 'INITIATED', initiator_offer = self.dummy_offer)
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

    def test_cancel_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                               initiator_offer = self.dummy_offer)

        response = self.client.post("/game/{}/trade/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

    def test_cancel_trade_allowed_and_effective_for_the_responder_for_a_trade_in_status_REPLIED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser,
                               status = 'REPLIED', initiator_offer = self.dummy_offer)

        response = self.client.post("/game/{}/trade/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertEqual(self.loginUser, trade.finalizer)
        self.assertIsNotNone(trade.closing_date)

    def test_reply_trade_not_allowed_in_GET(self):
        response = self.client.get("/game/{}/trade/{}/reply/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_reply_trade_not_allowed_when_one_is_not_the_responder(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
                                responder = User.objects.get(username = 'test6'),
                                status = 'INITIATED', initiator_offer = self.dummy_offer)

        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_not_allowed_for_trades_not_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
                                responder = self.loginUser, status = 'ACCEPTED', initiator_offer = self.dummy_offer)

        self._assertOperationNotAllowed(trade.id, 'reply')

    def test_reply_trade_without_selecting_cards_fails(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
                                responder = self.loginUser, status = 'INITIATED', initiator_offer = self.dummy_offer)
        response = self.client.post("/game/{}/trade/{}/reply/".format(self.game.id, trade.id),
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
            rulecard = rulecard, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        commodity = mommy.make_one(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = User.objects.get(username = 'test2'),
            commodity = commodity, nb_cards = 2)
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5,
            responder = self.loginUser, status = 'INITIATED', initiator_offer = self.dummy_offer)

        response = self.client.post("/game/{}/trade/{}/reply/".format(self.game.id, trade.id),
            {'rulecards-TOTAL_FORMS': 1,               'rulecards-INITIAL_FORMS': 1,
             'rulecards-0-card_id': rule_in_hand.id,   'rulecards-0-selected_rule': 'on',
             'commodity-TOTAL_FORMS': 1,               'commodity-INITIAL_FORMS': 1,
             'commodity-0-commodity_id': commodity.id, 'commodity-0-nb_traded_cards': 2,
             'free_information': 'some "secret" info',
             'comment': 'a comment'
            })
        self.assertRedirects(response, "/game/{}/trades/".format(self.game.id))

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual('REPLIED', trade.status)
        self.assertEqual('a comment', trade.responder_offer.comment)
        self.assertEqual('some "secret" info', trade.responder_offer.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.responder_offer.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.responder_offer.commodities.all()))
        self.assertEqual(2, trade.responder_offer.tradedcommodities_set.all()[0].nb_traded_cards)

    def test_accept_trade_not_allowed_in_GET(self):
        response = self.client.get("/game/{}/trade/{}/accept/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_accept_trade_not_allowed_when_you_re_not_the_initiator(self):
        # responder
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, status = 'REPLIED',
                               initiator_offer = self.dummy_offer)
        self._assertOperationNotAllowed(trade.id, 'accept')

        # someone else
        trade.initiator = User.objects.get(username = 'test3')
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'accept')

    def test_accept_trade_not_allowed_for_trades_not_in_status_REPLIED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                               initiator_offer = self.dummy_offer)
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

    def test_accept_trade_allowed_and_effective_for_the_initiator_for_a_trade_in_status_REPLIED(self):
        rulecard1, rulecard2 = mommy.make_many(RuleCard, 2)
        commodity1, commodity2, commodity3 = mommy.make_many(Commodity, 3)

        rih1 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                              ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        rih2 = mommy.make_one(RuleInHand, game = self.game, player = self.test5, rulecard = rulecard2,
                              ownership_date = datetime.datetime.now(tz = get_default_timezone()))

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
        tc1i = mommy.make_one(TradedCommodities, offer = offer_initiator, commodity = cih1i, nb_traded_cards = 2)
        offer_initiator.tradedcommodities_set.add(tc1i)
        tc2i = mommy.make_one(TradedCommodities, offer = offer_initiator, commodity = cih2i, nb_traded_cards = 1)
        offer_initiator.tradedcommodities_set.add(tc2i)

        # the responder offers rulecard2, 1 commodity1 and 2 commodity3
        offer_responder = mommy.make_one(Offer, rules = [rih2], commodities = [])
        tc1r = mommy.make_one(TradedCommodities, offer = offer_responder, commodity = cih1r, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc1r)
        tc3r = mommy.make_one(TradedCommodities, offer = offer_responder, commodity = cih3r, nb_traded_cards = 2)
        offer_responder.tradedcommodities_set.add(tc3r)

        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               status = 'REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/game/{}/trade/{}/accept/".format(self.game.id, trade.id), follow = True)

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
        response = self.client.get("/game/{}/trade/{}/decline/".format(self.game.id, 1))
        self.assertEqual(403, response.status_code)

    def test_decine_trade_not_allowed_for_trades_when_you_re_not_the_player_that_can_decline(self):
        # trade INITIATED but we're not the responder
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               status = 'INITIATED', initiator_offer = self.dummy_offer)
        self._assertOperationNotAllowed(trade.id, 'decline')

        # trade REPLIED but we're not the initiator
        trade.initiator = self.test5
        trade.responder = self.loginUser
        trade.status = 'REPLIED'
        trade.save()
        self._assertOperationNotAllowed(trade.id, 'decline')

    def test_decline_trade_not_allowed_for_the_responder_for_trades_not_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser,
                               status = 'REPLIED', initiator_offer = self.dummy_offer)
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

    def test_decline_trade_allowed_and_effective_for_the_responder_for_a_trade_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser,
                               status = 'INITIATED', initiator_offer = self.dummy_offer)

        response = self.client.post("/game/{}/trade/{}/decline/".format(self.game.id, trade.id),
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
                              ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        rih2 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                              ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        rih3 = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard3,
                              ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        cih1 = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity1,
                              nb_cards = 3)
        cih2 = mommy.make_one(CommodityInHand, game = self.game, player = self.loginUser, commodity = commodity2,
                              nb_cards = 2)

        # rulecard1 and 1 card of commodity1 are in the initator offer of a pending trade
        offer1 = mommy.make_one(Offer, rules = [rih1], commodities = [])
        tc1 = mommy.make_one(TradedCommodities, offer = offer1, commodity = cih1, nb_traded_cards = 1)
        offer1.tradedcommodities_set.add(tc1)
        trade1 = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                                initiator_offer = offer1, status = 'INITIATED')
        # rulecard2 and 1 card of commodity1 were in the initiator offer of a finalized trade
        offer2 = mommy.make_one(Offer, rules = [rih2], commodities = [])
        tc2 = mommy.make_one(TradedCommodities, offer = offer2, commodity = cih1, nb_traded_cards = 1)
        offer2.tradedcommodities_set.add(tc2)
        trade2 = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                                initiator_offer = offer2, status = 'CANCELLED', finalizer = self.loginUser)
        # rulecard3 and 1 card of commodity 2 are in the responder offer of a pending trade
        offer3 = mommy.make_one(Offer, rules = [rih3], commodities = [])
        tc3 = mommy.make_one(TradedCommodities, offer = offer3, commodity = cih2, nb_traded_cards = 1)
        offer3.tradedcommodities_set.add(tc3)
        trade3 = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser,
                                initiator_offer = self.dummy_offer, responder_offer = offer3, status = 'REPLIED')

        request = RequestFactory().get("/game/{}/trade/create/".format(self.game.id))
        request.user = self.loginUser
        offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(
                request, self.game, selected_rules = [rih2], selected_commodities = {cih1: 1})

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
                                  ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        rulecard_responder = mommy.make_one(RuleCard, public_name = '8', description = 'rule description 8')
        rih_responder = mommy.make_one(RuleInHand, game = self.game, player = self.test5, rulecard = rulecard_responder,
                                  ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        offer_initiator = mommy.make_one(Offer, rules = [rih_initiator], commodities = [], free_information = 'this is sensitive')
        offer_responder = mommy.make_one(Offer, rules = [rih_responder], commodities = [], free_information = 'these are sensitive')

        # INITIATED : the initiator should see the sensitive elements of his offer, the responder should not
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               initiator_offer = offer_initiator, status = 'INITIATED')
        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')

        response = clientTest5.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        # REPLIED : same as INITIATED for the initiator offer, plus the responder should see the sensitive elements of
        #  her offer, but not the initiator
        trade.responder_offer = offer_responder
        trade.status = 'REPLIED'
        trade.save()

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # CANCELLED : same as REPLIED
        trade.status = 'CANCELLED'
        trade.save()

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # DECLINED : same as REPLIED
        trade.status = 'CANCELLED'
        trade.save()

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, 'rule description 8')
        self.assertNotContains(response, 'these are sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertNotContains(response, 'rule description 7')
        self.assertNotContains(response, 'this is sensitive')
        self.assertContains(response, '(Hidden until trade accepted)')
        self.assertContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

        # ACCEPTED : both players should at least be able to see all sensitive information
        trade.status = 'ACCEPTED'
        trade.save()

        response = self.client.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')
        self.assertNotContains(response, '(Hidden until trade accepted)')
        self.assertNotContains(response, 'Some information(s), hidden until this trade is accepted by both players.')

        response = clientTest5.get("/game/{}/trade/{}/".format(self.game.id, trade.id))
        self.assertContains(response, 'rule description 7')
        self.assertContains(response, 'this is sensitive')
        self.assertNotContains(response, '(Hidden until trade accepted)')
        self.assertNotContains(response, 'Some information(s), hidden until this trade is accepted by both players.')
        self.assertContains(response, 'rule description 8')
        self.assertContains(response, 'these are sensitive')

    def _assertOperationNotAllowed(self, trade_id, operation):
        response = self.client.post("/game/{}/trade/{}/{}/".format(self.game.id, trade_id, operation), follow=True)
        self.assertEqual(403, response.status_code)

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'),
                                   players = User.objects.exclude(username = 'test1'))
        self.loginUser = User.objects.get(username = 'test2')
        self.test5 = User.objects.get(username = 'test5')
        self.client.login(username = 'test2', password = 'test')

    def test_accept_trade_cards_exchange_is_transactional(self):
        # let's make the responder offer 1 commodity for which he doesn't have any cards
        #  (because it's the last save() in the process, so we can assert that everything else has been rollbacked)
        rih = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser,
                             ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        offer_initiator = mommy.make_one(Offer, rules = [rih], commodities = [])

        offer_responder = mommy.make_one(Offer, rules = [], commodities = [])
        cih = mommy.make_one(CommodityInHand, game = self.game, player = self.test5, nb_cards = 0)
        tc = mommy.make_one(TradedCommodities, offer = offer_responder, commodity = cih, nb_traded_cards = 1)
        offer_responder.tradedcommodities_set.add(tc)

        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5,
                               status = 'REPLIED', initiator_offer = offer_initiator, responder_offer = offer_responder)

        response = self.client.post("/game/{}/trade/{}/accept/".format(self.game.id, trade.id), follow = True)

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
    def test_validate_number_of_players(self):
        chosen_ruleset = Ruleset.objects.get(id = 1)
        self.assertRaisesMessage(ValidationError, 'Please select at least 3 players (as many as there are mandatory rule cards in this ruleset).', 
                                 validate_number_of_players, ['user1', 'user2'], chosen_ruleset)
        try:
            validate_number_of_players(['user1', 'user2', 'user3'], chosen_ruleset)
        except ValidationError:
            self.fail("validate_number_of_players should not fail when there are as many players as mandatory rule cards")

    def test_validate_dates(self):
        self.assertRaisesMessage(ValidationError, 'End date must be strictly posterior to start date.',
                                 validate_dates,
                                 datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()),
                                 datetime.datetime(2011, 11, 10, 18, 30, tzinfo = get_default_timezone()))
        self.assertRaisesMessage(ValidationError, 'End date must be strictly posterior to start date.',
                                 validate_dates,
                                 datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()),
                                 datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()))
        try:
            validate_dates(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), datetime.datetime(2012, 11, 10, 18, 50, tzinfo = get_default_timezone()))
        except ValidationError:
            self.fail("validate_dates should not fail when end_date is strictly posterior to start_date")

    #noinspection PyUnusedLocal
    def test_a_rule_offered_by_the_initiator_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        rule_in_hand = mommy.make_one(RuleInHand, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        offer = mommy.make_one(Offer, rules = [rule_in_hand], commodities = [])
        pending_trade = mommy.make_one(Trade, status = 'INITIATED', initiator_offer = offer)

        RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
        rulecards_formset = RuleCardsFormSet({'rulecards-TOTAL_FORMS': 1, 'rulecards-INITIAL_FORMS': 1,
                                              'rulecards-0-card_id': rule_in_hand.id, 'rulecards-0-selected_rule': 'on'
                                             }, prefix = 'rulecards')

        self.assertFalse(rulecards_formset.is_valid())
        self.assertIn("A rule card in a pending trade can not be offered in another trade.", rulecards_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_a_rule_offered_by_the_responder_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        rule_in_hand = mommy.make_one(RuleInHand, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        offer = mommy.make_one(Offer, rules = [rule_in_hand], commodities = [])
        pending_trade = mommy.make_one(Trade, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make_one(Offer, rules = [], commodities = []))

        RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
        rulecards_formset = RuleCardsFormSet({'rulecards-TOTAL_FORMS': 1, 'rulecards-INITIAL_FORMS': 1,
                                              'rulecards-0-card_id': rule_in_hand.id, 'rulecards-0-selected_rule': 'on'
                                             }, prefix = 'rulecards')

        self.assertFalse(rulecards_formset.is_valid())
        self.assertIn("A rule card in a pending trade can not be offered in another trade.", rulecards_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_commodities_offered_by_the_initiator_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        commodity_in_hand = mommy.make_one(CommodityInHand, nb_cards = 1)
        # see https://github.com/vandersonmota/model_mommy/issues/25
        offer = mommy.make_one(Offer, rules = [], commodities = [])
        traded_commodities = mommy.make_one(TradedCommodities, nb_traded_cards = 1, commodity = commodity_in_hand, offer = offer)
        pending_trade = mommy.make_one(Trade, game = commodity_in_hand.game, status = 'INITIATED', initiator_offer = offer)

        CommodityCardsFormSet = formset_factory(CommodityCardFormParse, formset = BaseCommodityCardFormSet)
        commodities_formset = CommodityCardsFormSet({'commodity-TOTAL_FORMS': 1, 'commodity-INITIAL_FORMS': 1,
                                                     'commodity-0-commodity_id': commodity_in_hand.commodity.id, 'commodity-0-nb_traded_cards': 1,
                                                    }, prefix = 'commodity')
        commodities_formset.set_game(commodity_in_hand.game)
        commodities_formset.set_player(commodity_in_hand.player)

        self.assertFalse(commodities_formset.is_valid())
        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", commodities_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_commodities_offered_by_the_responder_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        commodity_in_hand = mommy.make_one(CommodityInHand, nb_cards = 2)
        # see https://github.com/vandersonmota/model_mommy/issues/25
        offer = mommy.make_one(Offer, rules = [], commodities = [])
        traded_commodities = mommy.make_one(TradedCommodities, nb_traded_cards = 1, commodity = commodity_in_hand, offer = offer)
        pending_trade = mommy.make_one(Trade, game = commodity_in_hand.game, status = 'INITIATED', responder_offer = offer,
                                       initiator_offer = mommy.make_one(Offer, rules = [], commodities = []))

        CommodityCardsFormSet = formset_factory(CommodityCardFormParse, formset = BaseCommodityCardFormSet)
        commodities_formset = CommodityCardsFormSet({'commodity-TOTAL_FORMS': 1, 'commodity-INITIAL_FORMS': 1,
                                                     'commodity-0-commodity_id': commodity_in_hand.commodity.id, 'commodity-0-nb_traded_cards': 2,
                                                     }, prefix = 'commodity')
        commodities_formset.set_game(commodity_in_hand.game)
        commodities_formset.set_player(commodity_in_hand.player)

        self.assertFalse(commodities_formset.is_valid())
        self.assertIn("A commodity card in a pending trade can not be offered in another trade.", commodities_formset._non_form_errors)

class DealTest(TestCase):
    def setUp(self):
        self.users = []
        self.rules = []
        self.commodities = []
        for i in range(6):
            self.users.append(mommy.make_one(User, username = i))
            self.rules.append(mommy.make_one(RuleCard, ref_name = i))
            self.commodities.append(mommy.make_one(Commodity, name = i))

    def test_prepare_deck(self):
        deck = prepare_deck(self.rules, nb_copies = 2)
        self.assertEqual(12, len(deck))
        for i in range(6):
            self.assertEqual(2, deck.count(self.rules[i]))

    def test_add_a_card_to_hand_last_rule_is_popped(self):
        hand = []
        expected_rule = self.rules[5]
        RuleCardDealer().add_a_card_to_hand(hand, self.rules)
        self.assertEqual(1, len(hand))
        self.assertEqual(5, len(self.rules))
        self.assertNotIn(expected_rule, self.rules)
        self.assertIn(expected_rule, hand)

    def test_add_a_card_to_hand_select_the_first_new_rule_from_end(self):
        hand = [self.rules[4], self.rules[5]]
        expected_rule = self.rules[3]
        RuleCardDealer().add_a_card_to_hand(hand, self.rules)
        self.assertEqual(3, len(hand))
        self.assertEqual(5, len(self.rules))
        self.assertIn(expected_rule, hand)

    def test_add_a_card_to_hand_inappropriate_dealing(self):
        with self.assertRaises(InappropriateDealingException):
            RuleCardDealer().add_a_card_to_hand(self.rules, self.rules)

    def test_add_a_card_to_hand_duplicates_allowed_for_commodities(self):
        expected_commodity = self.commodities[5]
        hand = [expected_commodity]
        CommodityCardDealer().add_a_card_to_hand(hand, self.commodities)
        self.assertEqual(2, hand.count(expected_commodity))

    def test_dispatch_rules_with_as_many_players_as_rules(self):
        hands = dispatch_cards(6, 2, self.rules, RuleCardDealer())
        for hand in hands:
            self.assertEqual(2, len(hand))
            self.assertNotEqual(hand[0], hand[1])

    def test_dispatch_rules_with_more_players_than_rules(self):
        hands = dispatch_cards(7, 2, self.rules, RuleCardDealer())
        for hand in hands:
            self.assertEqual(2, len(hand))
            self.assertNotEqual(hand[0], hand[1])

    def test_dispatch_rules_with_inappropriate_dealing_should_make_start_over(self):
        class MockCardDealer(RuleCardDealer):
            def __init__(self):
                self.raisedException = False
            def add_a_card_to_hand(self, hand, deck):
                if not self.raisedException:
                    self.raisedException = True
                    raise InappropriateDealingException
                else:
                    super(MockCardDealer, self).add_a_card_to_hand(hand, deck)
        mock = MockCardDealer()
        hands = dispatch_cards(6, 2, self.rules, mock)
        self.assertTrue(mock.raisedException)
        for hand in hands:
            self.assertEqual(2, len(hand))
            self.assertNotEqual(hand[0], hand[1])

    def test_deal_cards(self):
        ruleset = Ruleset.objects.get(id = 1)
        game = mommy.make_one(Game, ruleset = ruleset, players = self.users, rules = self.rules,
                 start_date = datetime.datetime(2012, 12, 17, 14, 29, 34, tzinfo = get_default_timezone()))
        deal_cards(game)
        for player in self.users:
            rules = RuleInHand.objects.filter(game = game, player = player)
            self.assertEqual(2, len(rules))
            for rule in rules:
                self.assertEqual(game.start_date, rule.ownership_date)
            commodities = CommodityInHand.objects.filter(game = game, player = player)
            nb_commodities = 0
            for commodity in commodities:
                nb_commodities += commodity.nb_cards
            self.assertEqual(10, nb_commodities)
        for rule in self.rules:
            nb_cards = RuleInHand.objects.filter(game = game, rulecard = rule).count()
            min_occurence = 2*6/len(self.rules)
            self.assertTrue(min_occurence <= nb_cards <= min_occurence+1)
        for commodity in Commodity.objects.filter(ruleset = ruleset):
            nb_cards = CommodityInHand.objects.filter(game = game, commodity = commodity).aggregate(Sum('nb_cards'))
            self.assertEqual(10*6/5, nb_cards['nb_cards__sum'])