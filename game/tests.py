import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Sum
from django.test import TestCase, TransactionTestCase
from django.utils.timezone import get_default_timezone
from model_mommy import mommy

from game.deal import InappropriateDealingException, RuleCardDealer, deal_cards, \
    prepare_deck, dispatch_cards, CommodityCardDealer
from game.forms import validate_number_of_players, validate_dates
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer
from scoring.models import Ruleset, RuleCard, Commodity
from trade.models import Offer, Trade

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
        for user in self.testUsersNoCreate: GamePlayer.objects.create(game = game1, player = user)
        game2 = Game.objects.create(ruleset = ruleset, master = self.testUsersNoCreate[0],
                                    end_date = datetime.datetime(2022, 11, 3, 12, 0, 0, tzinfo = get_default_timezone()))
        GamePlayer.objects.create(game = game2, player = self.testUserCanCreate)
        GamePlayer.objects.create(game = game2, player = self.testUsersNoCreate[1])
        game3 = Game.objects.create(ruleset = ruleset, master = self.testUsersNoCreate[0],
                                    end_date = datetime.datetime(2022, 11, 5, 12, 0, 0, tzinfo = get_default_timezone()))
        GamePlayer.objects.create(game = game3, player = self.testUsersNoCreate[1])
        GamePlayer.objects.create(game = game3, player = self.testUsersNoCreate[2])

        response = self.client.get(reverse("welcome"))
        self.assertEqual(200, response.status_code)
        self.assertListEqual([game2, game1], list(response.context['games']))
        self.assertNotIn(game3, response.context['games'])

class HandViewTest(TestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'), players = [])
        for player in User.objects.exclude(username = 'test1'): mommy.make_one(GamePlayer, game = self.game, player = player)
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

    def test_show_hand_displays_free_informations_from_ACCEPTED_trades(self):
        offer1_from_me_as_initiator = mommy.make_one(Offer, rules = [], commodities = [], free_information = "I don't need to see that 1")
        offer1_from_other_as_responder = mommy.make_one(Offer, rules = [], commodities = [], free_information = "Show me this 1")
        trade1 = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5, status = 'ACCEPTED',
                                initiator_offer = offer1_from_me_as_initiator, responder_offer = offer1_from_other_as_responder)

        offer2_from_other_as_initiator = mommy.make_one(Offer, rules = [], commodities = [], free_information = "Show me this 2")
        trade2 = mommy.make_one(Trade, game = self.game, initiator = self.test5, responder = self.loginUser, status = 'ACCEPTED',
                                initiator_offer = offer2_from_other_as_initiator, responder_offer = self.dummy_offer)

        offer3_from_other_as_responder = mommy.make_one(Offer, rules = [], commodities = [], free_information = "I don't need to see that 3")
        trade3 = mommy.make_one(Trade, game = self.game, initiator = self.loginUser, responder = self.test5, status = 'DECLINED',
                                initiator_offer = self.dummy_offer, responder_offer = offer3_from_other_as_responder)

        response = self.client.get("/game/{}/hand/".format(self.game.id))

        self.assertContains(response, "Show me this 1")
        self.assertContains(response, "Show me this 2")
        self.assertNotContains(response, "I don't need to see that 1")
        self.assertNotContains(response, "I don't need to see that 3")

    def test_show_hand_doesnt_display_free_informations_from_ACCEPTED_trades_of_other_games(self):
        other_game = mommy.make_one(Game, master = User.objects.get(username = 'test1'), players = [])
        for player in User.objects.exclude(username = 'test1'): mommy.make_one(GamePlayer, game = other_game, player = player)

        initiator_offer1 = mommy.make_one(Offer, rules = [], commodities = [])
        responder_offer1 = mommy.make_one(Offer, rules = [], commodities = [], free_information = "There is no point showing this")
        trade = mommy.make_one(Trade, game = other_game, initiator = self.loginUser, responder = self.test5,
                               status = 'ACCEPTED', initiator_offer = initiator_offer1, responder_offer = responder_offer1)

        initiator_offer2 = mommy.make_one(Offer, rules = [], commodities = [], free_information = "There is no point showing that")
        responder_offer2 = mommy.make_one(Offer, rules = [], commodities = [])
        trade = mommy.make_one(Trade, game = other_game, initiator = self.test5, responder = self.loginUser,
                               status = 'ACCEPTED', initiator_offer = initiator_offer2, responder_offer = responder_offer2)

        response = self.client.get("/game/{}/hand/".format(self.game.id))

        self.assertNotContains(response, "There is no point showing this")
        self.assertNotContains(response, "There is no point showing that")

    def test_show_hand_displays_former_rulecards_given_in_trades(self):
        rulecard1 = mommy.make_one(RuleCard, public_name = 'C1', description = 'Desc1')
        rulecard2 = mommy.make_one(RuleCard, public_name = 'C2', description = 'Desc2')
        rih1_former = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                     ownership_date = datetime.datetime(2013, 01, 10, 18, 30, tzinfo = get_default_timezone()),
                                     abandon_date = datetime.datetime(2012, 01, 11, 10, 45, tzinfo = get_default_timezone()))
        rih1_former_duplicate = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                               ownership_date = datetime.datetime(2013, 01, 12, 16, 00, tzinfo = get_default_timezone()),
                                               abandon_date = datetime.datetime(2012, 01, 13, 18, 00, tzinfo = get_default_timezone()))
        rih2_current = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                      ownership_date = datetime.datetime(2013, 01, 15, 15, 25, tzinfo = get_default_timezone()),
                                      abandon_date = None)
        rih2_former_but_copy_of_current = mommy.make_one(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                                         ownership_date = datetime.datetime(2013, 01, 12, 12, 00, tzinfo = get_default_timezone()),
                                                         abandon_date = datetime.datetime(2013, 01, 13, 8, 5, tzinfo = get_default_timezone()))

        # one should see one rulecard 2 in rules currently owned and only one rulecard 1 in former rules
        #  (no duplicates and no copies of cards currently in hand)
        response = self.client.get("/game/{}/hand/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">C2</div>', count = 1)
        self.assertEqual([rulecard2], [rih.rulecard for rih in response.context['rule_hand']])

        self.assertContains(response, '<div class="card_name">C1</div>', count = 1)
        self.assertEqual([{'public_name': 'C1', 'description': 'Desc1'}], response.context['former_rules'])

    def test_submit_hand_displays_the_commodities(self):
        commodity1 = mommy.make_one(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make_one(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make_one(Commodity, name = 'c3', color = 'colC')

        cih1 = mommy.make_one(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                              nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make_one(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                              nb_cards = 2, nb_submitted_cards = None)
        cih3 = mommy.make_one(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                              nb_cards = 3, nb_submitted_cards = None)

        response = self.client.get("/game/{}/hand/submit/".format(self.game.id))
        self.assertEqual(200, response.status_code)

        self.assertEqual(3, len(response.context['commodities_formset'].initial))
        self.assertIn({'commodity_id': commodity1.id, 'name': 'c1', 'color': 'colA', 'nb_cards': 1, 'nb_submitted_cards': 1},
                      response.context['commodities_formset'].initial)
        self.assertIn({'commodity_id': commodity2.id, 'name': 'c2', 'color': 'colB', 'nb_cards': 2, 'nb_submitted_cards': 2},
                      response.context['commodities_formset'].initial)
        self.assertIn({'commodity_id': commodity3.id, 'name': 'c3', 'color': 'colC', 'nb_cards': 3, 'nb_submitted_cards': 3},
                      response.context['commodities_formset'].initial)

    def test_submit_hand_save_submitted_commodities_and_submit_date(self):
        self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

        commodity1 = mommy.make_one(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make_one(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make_one(Commodity, name = 'c3', color = 'colC')

        cih1 = mommy.make_one(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                              nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make_one(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                              nb_cards = 2, nb_submitted_cards = None)
        cih3 = mommy.make_one(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                              nb_cards = 3, nb_submitted_cards = None)

        response = self.client.post("/game/{}/hand/submit/".format(self.game.id),
                                    {'commodity-TOTAL_FORMS': 2, 'commodity-INITIAL_FORMS': 2,
                                     'commodity-0-commodity_id': commodity1.id, 'commodity-0-nb_submitted_cards': 0,
                                     'commodity-1-commodity_id': commodity3.id, 'commodity-1-nb_submitted_cards': 2 }, follow = True)
        self.assertEqual(200, response.status_code)

        cih1 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity1)
        self.assertEqual(0, cih1.nb_submitted_cards)
        cih2 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity2)
        self.assertEqual(2, cih2.nb_submitted_cards)
        cih3 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity3)
        self.assertEqual(2, cih3.nb_submitted_cards)

        self.assertIsNotNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['test_users.json']

    def setUp(self):
        self.game = mommy.make_one(Game, master = User.objects.get(username = 'test1'), players = [])
        for player in User.objects.exclude(username = 'test1'): mommy.make_one(GamePlayer, game = self.game, player = player)
        self.loginUser = User.objects.get(username = 'test2')
        self.test5 = User.objects.get(username = 'test5')
        self.client.login(username = 'test2', password = 'test')

    def test_submit_hand_is_transactional(self):
        commodity1 = mommy.make_one(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make_one(Commodity, name = 'c2', color = 'colB')

        cih1 = mommy.make_one(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
            nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make_one(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
            nb_cards = 2, nb_submitted_cards = None)

        # set a nb_submitted_cards < 0 on the last form to make the view fail on the last iteration
        response = self.client.post("/game/{}/hand/submit/".format(self.game.id),
            {'commodity-TOTAL_FORMS': 2, 'commodity-INITIAL_FORMS': 2,
             'commodity-0-commodity_id': commodity1.id, 'commodity-0-nb_submitted_cards': 1,
             'commodity-1-commodity_id': commodity2.id, 'commodity-1-nb_submitted_cards': -3 }, follow = True)

        self.assertEqual(200, response.status_code)

        self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

        for commodity in CommodityInHand.objects.filter(game = self.game, player = self.loginUser):
            self.assertIsNone(commodity.nb_submitted_cards)

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
        game = mommy.make_one(Game, ruleset = ruleset, players = [], rules = self.rules,
                              start_date = datetime.datetime(2012, 12, 17, 14, 29, 34, tzinfo = get_default_timezone()))
        for player in self.users:
            GamePlayer.objects.create(game = game, player = player)
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