import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Sum
from django.forms.formsets import formset_factory
from django.test import TestCase
from django.utils.timezone import get_default_timezone
from django.utils.unittest.case import skip
from model_mommy import mommy

from game.deal import InappropriateDealingException, RuleCardDealer, deal_cards, \
    prepare_deck, dispatch_cards, CommodityCardDealer
from game.forms import validate_number_of_players, validate_dates, RuleCardFormParse, BaseRuleCardsFormSet, CommodityCardFormParse, BaseCommodityCardFormSet
from game.models import Game, RuleInHand, CommodityInHand, Trade, TradedCommodities
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

        self.client.login(username = 'testNoCreate0', password = 'test')
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

class TradeViewsTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'),
                                   players = User.objects.exclude(username = 'test1'))
        self.loginUser = User.objects.get(username = 'test2')
        self.client.login(username = 'test2', password = 'test')

    def test_create_trade_without_responder_fails(self):
        response = self.client.post("/game/{}/trades/create/".format(self.game.id),
            {'rulecards-TOTAL_FORMS': 2, 'rulecards-INITIAL_FORMS': 2,
             'rulecards-0-card_id': 1,
             'rulecards-1-card_id': 2,
             'commodity-TOTAL_FORMS': 5, 'commodity-INITIAL_FORMS': 5,
             'commodity-0-commodity_id': 1, 'commodity-0-nb_traded_cards': 0,
             'commodity-1-commodity_id': 2, 'commodity-1-nb_traded_cards': 1,
             'commodity-2-commodity_id': 3, 'commodity-2-nb_traded_cards': 0,
             'commodity-3-commodity_id': 4, 'commodity-3-nb_traded_cards': 0,
             'commodity-4-commodity_id': 5, 'commodity-4-nb_traded_cards': 0,
             'comment': 'a comment'
            })
        self.assertFormError(response, 'trade_form', 'responder', 'This field is required.')

    def test_create_trade_without_selecting_cards_fails(self):
        response = self.client.post("/game/{}/trades/create/".format(self.game.id),
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
                                     'comment': 'a comment'
                                    })
        self.assertFormError(response, 'trade_form', None, 'At least one card should be offered.')

    def test_create_trade_complete_save(self):
        ruleset = mommy.make_one(Ruleset)
        rulecard = mommy.make_one(RuleCard, ruleset = ruleset, ref_name = 'rulecard_1')
        rule_in_hand = RuleInHand.objects.create(game = self.game, player = User.objects.get(username = 'test2'),
                                                 rulecard = rulecard, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        commodity = mommy.make_one(Commodity, ruleset = ruleset, name = 'commodity_1')
        commodity_in_hand = CommodityInHand.objects.create(game = self.game, player = User.objects.get(username = 'test2'),
                                                           commodity = commodity, nb_cards = 2)
        response = self.client.post("/game/{}/trades/create/".format(self.game.id),
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
        self.assertEqual('a comment', trade.comment)
        self.assertEqual('some "secret" info', trade.free_information)
        self.assertIsNone(trade.closing_date)
        self.assertEqual([rule_in_hand], list(trade.rules.all()))
        self.assertEqual([commodity_in_hand], list(trade.commodities.all()))
        self.assertEqual(1, trade.tradedcommodities_set.all()[0].nb_traded_cards)

    #noinspection PyUnusedLocal,PyTypeChecker
    def test_trade_list(self):
        right_now = datetime.datetime.now(tz = get_default_timezone())
        trade_initiated = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                                         rules = [], commodities = [],
                                         creation_date = right_now - datetime.timedelta(days = 1))
        trade_cancelled = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'CANCELLED',
                                         rules = [], commodities = [],
                                         closing_date = right_now - datetime.timedelta(days = 2))
        trade_accepted = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'ACCEPTED',
                                        rules = [], commodities = [],
                                        closing_date = right_now - datetime.timedelta(days = 3))
        trade_declined = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'DECLINED',
                                        rules = [], commodities = [],
                                        closing_date = right_now - datetime.timedelta(days = 4))

        response = self.client.get("/game/{}/trades/".format(self.game.id))

        self.assertContains(response, "submitted 1 day ago")
        self.assertContains(response, "cancelled by <strong>you</strong> 2 days ago")
        self.assertContains(response, "accepted 3 days ago")
        self.assertContains(response, "declined 4 days ago")

    def test_cancel_trade_not_allowed_in_GET(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                               rules = [], commodities = [])

        response = self.client.get("/game/{}/trades/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(404, response.status_code)

    def test_cancel_trade_not_allowed_for_trades_you_didnt_create(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = User.objects.get(username = 'test5'), status = 'INITIATED',
                               rules = [], commodities = [])

        response = self.client.post("/game/{}/trades/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(404, response.status_code)

    def test_cancel_trade_not_allowed_for_trades_not_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'ACCEPTED',
                               rules = [], commodities = [])

        response = self.client.post("/game/{}/trades/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(404, response.status_code)

    def test_cancel_trade_allowed_and_effective_for_trades_you_created_and_still_in_status_INITIATED(self):
        trade = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, status = 'INITIATED',
                               rules = [], commodities = [])

        response = self.client.post("/game/{}/trades/{}/cancel/".format(self.game.id, trade.id), follow = True)

        self.assertEqual(200, response.status_code)

        trade = Trade.objects.get(pk = trade.id)
        self.assertEqual("CANCELLED", trade.status)
        self.assertIsNotNone(trade.closing_date)

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
    def test_a_rule_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        rule_in_hand = mommy.make_one(RuleInHand, ownership_date = datetime.datetime.now(tz = get_default_timezone()))
        pending_trade = mommy.make_one(Trade, status = 'INITIATED', rules = [rule_in_hand], commodities = [])

        RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
        rulecards_formset = RuleCardsFormSet({'rulecards-TOTAL_FORMS': 1, 'rulecards-INITIAL_FORMS': 1,
                                              'rulecards-0-card_id': rule_in_hand.id, 'rulecards-0-selected_rule': 'on'
                                             }, prefix = 'rulecards')

        self.assertFalse(rulecards_formset.is_valid())
        self.assertIn("A rule card in a pending trade can not be offered in another trade.", rulecards_formset._non_form_errors)

    #noinspection PyUnusedLocal
    def test_commodities_in_a_pending_trade_cannot_be_offered_in_another_trade(self):
        commodity_in_hand = mommy.make_one(CommodityInHand, nb_cards = 1)
        # see https://github.com/vandersonmota/model_mommy/issues/25
        pending_trade = mommy.make_one(Trade, game = commodity_in_hand.game, status = 'INITIATED', rules = [], commodities = [])
        traded_commodities = mommy.make_one(TradedCommodities, nb_traded_cards = 1, commodity = commodity_in_hand, trade = pending_trade)

        CommodityCardsFormSet = formset_factory(CommodityCardFormParse, formset = BaseCommodityCardFormSet)
        commodities_formset = CommodityCardsFormSet({'commodity-TOTAL_FORMS': 1, 'commodity-INITIAL_FORMS': 1,
                                                     'commodity-0-commodity_id': commodity_in_hand.commodity.id, 'commodity-0-nb_traded_cards': 1,
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