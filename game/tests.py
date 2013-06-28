import datetime
from django.contrib.auth import get_user_model

from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Sum
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import get_default_timezone, now
from model_mommy import mommy

from game.deal import InappropriateDealingException, RuleCardDealer, deal_cards, \
    prepare_deck, dispatch_cards, CommodityCardDealer
from game.forms import validate_number_of_players, validate_dates
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer, Message
from ruleset.models import Ruleset, RuleCard, Commodity
from scoring.card_scoring import Scoresheet
from scoring.models import ScoreFromCommodity, ScoreFromRule
from trade.models import Offer, Trade
from utils.tests import MystradeTestCase

class WelcomePageViewTest(MystradeTestCase):

    def test_url_with_no_path_should_display_welcome_page_if_authenticated(self):
        """ ie http://host.com/ should actually display the same page as http://host.com/game/ """
        response = self.client.get("")
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "game/welcome.html")

        self.client.logout()
        response = self.client.get("")
        self.assertRedirects(response, "/login?next=/")

    def test_welcome_needs_login(self):
        response = self.client.get(reverse("welcome"))
        self.assertEqual(200, response.status_code)

        self.client.logout()
        response = self.client.get(reverse("welcome"))
        self.assertRedirects(response, "/login?next=/game/")

    def test_welcome_games_query(self):
        game_mastered = mommy.make(Game, master = self.loginUser,
                                       end_date = datetime.datetime(2022, 11, 1, 12, 0, 0, tzinfo = get_default_timezone()))
        mommy.make(GamePlayer, game = game_mastered, player = self.alternativeUser)
        other_game = mommy.make(Game, master = self.alternativeUser,
                               end_date = datetime.datetime(2022, 11, 5, 12, 0, 0, tzinfo = get_default_timezone()))

        response = self.client.get(reverse("welcome"))

        self.assertEqual(200, response.status_code)
        self.assertItemsEqual([self.game, game_mastered], list(response.context['games']))
        self.assertNotIn(other_game, response.context['games'])

class GameCreationViewsTest(TestCase):
    fixtures = ['test_users.json'] # from profile app

    def setUp(self):
        self.testUserCanCreate = get_user_model().objects.get(username = 'test1')
        self.testUsersNoCreate = get_user_model().objects.exclude(user_permissions__codename = "add_game")
        self.client.login(username = 'test1', password = 'test')

    def test_create_game_only_with_the_permission(self):
        # initially logged as testCanCreate
        response = self.client.get("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.assertTrue(self.client.login(username = 'test9', password = 'test'))
        response = self.client.get("/game/create/")
        self.assertEqual(302, response.status_code)

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

    @override_settings(TIME_ZONE = 'UTC')
    def test_create_game_first_page(self):
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate]})
        self.assertRedirects(response, "/game/selectrules/")
        self.assertEqual(1, self.client.session['ruleset'].id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), self.client.session['start_date'])
        self.assertEqual(datetime.datetime(2012, 11, 13, 00, 15, tzinfo = get_default_timezone()), self.client.session['end_date'])
        self.assertItemsEqual(list(self.testUsersNoCreate), self.client.session['players'])

    def test_access_select_rules_with_incomplete_session_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")
 
    def test_access_select_rules_without_enough_players_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = [self.testUsersNoCreate[0]]
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_select_rules_with_invalid_dates_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2011 00:15'
        session['players'] = [self.testUsersNoCreate[0]]
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_select_rules(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = self.testUsersNoCreate
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'game/select_rules.html')

    def test_create_game_with_too_many_rulecards(self):
        session = self.client.session
        session['ruleset'] = 1
        session['start_date'] = '11/10/2012 18:30'
        session['end_date'] = '11/13/2012 00:15'
        session['players'] = self.testUsersNoCreate[:4] # only 4 players
        session.save()
        response = self.client.post("/game/selectrules/",
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
        self.assertTemplateUsed(response, 'game/select_rules.html')
        self.assertEqual("Please select at most 4 rule cards (including the mandatory ones)", response.context['error'])

    @override_settings(ADMINS = (('admin', 'admin@mystrade.com'),), TIME_ZONE = 'UTC')
    def test_create_game_complete_save_and_clean_session(self):
        response = self.client.post("/game/create/", {'ruleset': 1,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2037 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate][:4]})
        self.assertRedirects(response, "/game/selectrules/")
        response = self.client.post("/game/selectrules/",
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

        created_game = Game.objects.get(master = self.testUserCanCreate.id)
        self.assertRedirects(response, "/game/{0}/".format(created_game.id))

        self.assertEqual(1, created_game.ruleset_id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), created_game.start_date)
        self.assertEqual(datetime.datetime(2037, 11, 13, 00, 15, tzinfo = get_default_timezone()), created_game.end_date)
        self.assertItemsEqual(list(self.testUsersNoCreate)[:4], list(created_game.players.all()))
        self.assertListEqual([1, 2, 3, 9], [rule.id for rule in created_game.rules.all()])
        self.assertFalse('ruleset' in self.client.session)
        self.assertFalse('start_date' in self.client.session)
        self.assertFalse('end_date' in self.client.session)
        self.assertFalse('players' in self.client.session)
        self.assertFalse('profiles' in self.client.session)

        # notification emails sent
        self.assertEqual(5, len(mail.outbox))
        list_recipients = [msg.to[0] for msg in mail.outbox]

        self.assertEqual(1, list_recipients.count('test2@test.com'))
        emailTest2 = mail.outbox[list_recipients.index('test2@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been created by test1'.format(created_game.id), emailTest2.subject)
        self.assertIn('Test1 has just created game #{0}, and you\'ve been selected to join it !'.format(created_game.id), emailTest2.body)
        self.assertEqual(2, emailTest2.body.count('- Rule'))
        self.assertIn("The game has already started ! Start trading here:", emailTest2.body)
        self.assertIn('/trade/{0}'.format(created_game.id), emailTest2.body)

        self.assertEqual(1, list_recipients.count('admin@mystrade.com'))
        emailAdmin = mail.outbox[list_recipients.index('admin@mystrade.com')]
        self.assertEqual('[MysTrade] Game #{0} has been created by test1'.format(created_game.id), emailAdmin.subject)
        self.assertIn('Test1 has just created game #{0}.'.format(created_game.id), emailAdmin.body)
        self.assertIn("The ruleset is: {0}".format(created_game.ruleset.name), emailAdmin.body)
        self.assertEqual(4, emailAdmin.body.count('- Rule'))

class GameModelsTest(MystradeTestCase):

    def test_game_is_active_if_start_and_end_date_enclose_now(self):
        start_date = now() + datetime.timedelta(days = -10)
        end_date = now() + datetime.timedelta(days = 10)
        game = mommy.make(Game, start_date = start_date, end_date = end_date)

        self.assertTrue(game.is_active())

    def test_game_is_not_active_if_start_date_has_not_yet_happened(self):
        start_date = now() + datetime.timedelta(days = 2)
        end_date = now() + datetime.timedelta(days = 10)
        game = mommy.make(Game, start_date = start_date, end_date = end_date)

        self.assertFalse(game.is_active())

    def test_game_is_not_active_if_end_date_is_over(self):
        start_date = now() + datetime.timedelta(days = -10)
        end_date = now() + datetime.timedelta(days = -3)
        game = mommy.make(Game, start_date = start_date, end_date = end_date)

        self.assertFalse(game.is_active())

    def test_game_has_super_access(self):
        self.assertFalse(self.game.has_super_access(self.loginUser))
        self.assertTrue(self.game.has_super_access(self.master))
        self.assertTrue(self.game.has_super_access(self.admin))
        self.assertFalse(self.game.has_super_access(self.admin_player))

class GamePageViewTest(MystradeTestCase):

    def test_returns_a_404_if_the_game_id_doesnt_exist(self):
        response = self.client.get("/game/999999999/")
        self.assertEqual(404, response.status_code)

    def test_access_to_game_page_forbidden_for_users_not_related_to_the_game_except_admins(self):
        self._assertGetGamePage()

        self.login_as(self.admin)
        self._assertGetGamePage()

        self.login_as(self.master)
        self._assertGetGamePage()

        self.login_as(self.unrelated_user)
        self._assertGetGamePage(status_code = 403)

    def test_game_page_shows_starting_and_finishing_dates(self):
        # Note: we add a couple of seconds to each date in the future because otherwise the timeuntil filter would sadly go
        #  from "2 days" to "1 day, 23 hours" between the instant the games' models are created and the few milliseconds it
        #  takes to call the template rendering. Sed fugit interea tempus fugit irreparabile, singula dum capti circumvectamur amore.

        # before start_date
        game1 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = 2, seconds = 2),
                               end_date = now() + datetime.timedelta(days = 4, seconds = 2))

        response = self.client.get("/game/{0}/".format(game1.id))
        self.assertContains(response, "(starting in 2 days, ending in 4 days)")

        # during the game
        game2 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -2),
                               end_date = now() + datetime.timedelta(days = 4, seconds = 2))

        response = self.client.get("/game/{0}/".format(game2.id))
        self.assertContains(response, "(started 2 days ago, ending in 4 days)")

        # after end_date
        game3 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -4),
                               end_date = now() + datetime.timedelta(days = -2))

        response = self.client.get("/game/{0}/".format(game3.id))
        self.assertContains(response, "(started 4 days ago, ended 2 days ago)")

        # after closing_date
        game4 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -4),
                               end_date = now() + datetime.timedelta(days = -2), closing_date = now() + datetime.timedelta(days = -1))

        response = self.client.get("/game/{0}/".format(game4.id))
        self.assertContains(response, "(started 4 days ago, closed 1 day ago)")

    def test_game_show_shows_a_link_to_control_board_to_game_master_and_admins_that_are_not_players(self):
        # logged as a simple player
        response = self._assertGetGamePage()
        self.assertNotContains(response, "<a href=\"/game/{0}/control/\">&gt; Access to control board</a>".format(self.game.id))

        # game master
        self.login_as(self.master)
        response = self._assertGetGamePage()
        self.assertContains(response, "<a href=\"/game/{0}/control/\">&gt; Access to control board</a>".format(self.game.id))

        # admin not player
        self.login_as(self.admin)
        response = self._assertGetGamePage()
        self.assertContains(response, "<a href=\"/game/{0}/control/\">&gt; Access to control board</a>".format(self.game.id))

        # admin but player in this game
        self.login_as(self.admin_player)
        response = self._assertGetGamePage()
        self.assertNotContains(response, "<a href=\"/game/{0}/control/\">&gt; Access to control board</a>".format(self.game.id))

    def test_game_page_shows_nb_of_rule_cards_owned_to_players(self):
        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.loginUser)
        rih3 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, abandon_date = now())

        response = self._assertGetGamePage()
        self.assertContains(response, "You own 2 rule cards")

    def test_game_page_doesnt_show_nb_of_rule_cards_nor_of_commodities_to_game_master(self):
        self.login_as(self.master)

        response = self._assertGetGamePage()
        self.assertNotContains(response, "You own 0 rule cards")
        self.assertNotContains(response, "and 0 commodities")
        self.assertNotContains(response, "<span class=\"minicard\"")

    def test_game_page_show_commodities_owned_to_players(self):
        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = Commodity.objects.get(ruleset = 1, name = "Blue"),
                              nb_cards = 1)

        response = self._assertGetGamePage()
        self.assertContains(response, "You own 0 rule cards")
        self.assertContains(response, "1 commodity")
        self.assertContains(response, "<span class=\"minicard\" data-tip=\"Blue\" style=\"background-color: blue\">&nbsp;</span>", count = 1)

        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = Commodity.objects.get(ruleset = 1, name = "Red"),
                              nb_cards = 4, nb_submitted_cards = 2)

        response = self._assertGetGamePage()
        self.assertContains(response, "5 commodities")
        self.assertContains(response, "<span class=\"minicard\" data-tip=\"Blue\" style=\"background-color: blue\">&nbsp;</span>", count = 1)
        self.assertContains(response, "<span class=\"minicard\" data-tip=\"Red\" style=\"background-color: red\">&nbsp;</span>", count = 4)

    def test_game_page_show_only_submitted_commodities_to_players_who_have_submitted_their_hand(self):
        gameplayer = GamePlayer.objects.get(game = self.game, player = self.loginUser)
        gameplayer.submit_date = now() +  datetime.timedelta(days = -2)
        gameplayer.save()

        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = Commodity.objects.get(ruleset = 1, name = "Blue"),
                              nb_cards = 3, nb_submitted_cards = 1)
        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = Commodity.objects.get(ruleset = 1, name = "Red"),
                              nb_cards = 2, nb_submitted_cards = 2)
        cih3 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser, commodity = Commodity.objects.get(ruleset = 1, name = "Orange"),
                              nb_cards = 1, nb_submitted_cards = 0)

        response = self._assertGetGamePage()
        self.assertContains(response, "you have submitted")
        self.assertContains(response, "3 commodities")

        self.assertContains(response, "<span class=\"minicard\" data-tip=\"Blue\" style=\"background-color: blue\">&nbsp;</span>", count = 1)
        self.assertContains(response, "<span class=\"minicard\" data-tip=\"Red\" style=\"background-color: red\">&nbsp;</span>", count = 2)
        self.assertNotContains(response, "<span class=\"minicard\" data-tip=\"Orange\" style=\"background-color: orange\">&nbsp;</span>")

    def test_game_page_show_pending_trades_with_less_than_3_pending_trades(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -1),
                                initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'REPLIED',   creation_date = now() + datetime.timedelta(days = -2),
                                initiator_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'DECLINED',  creation_date = now() + datetime.timedelta(days = -3),
                                initiator_offer = mommy.make(Offer)) # not pending

        response = self._assertGetGamePage()
        self.assertContains(response, "Pending trades")
        self.assertContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade1.id))
        self.assertContains(response, "trade/{0}/{1}/\"><span class=\"new\">Decide".format(self.game.id, trade2.id))
        self.assertNotContains(response, "trade/{0}/{1}/\">".format(self.game.id, trade3.id))

    def test_game_page_show_last_3_pending_trades_when_more_than_three_are_pending(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -1),
                                initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -2),
                                initiator_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -3),
                                initiator_offer = mommy.make(Offer))
        trade4 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -4),
                                initiator_offer = mommy.make(Offer))

        response = self._assertGetGamePage()
        self.assertContains(response, "Last 3 pending trades")
        self.assertContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade1.id))
        self.assertContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade2.id))
        self.assertContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade3.id))
        self.assertNotContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade4.id))

    def test_game_page_doesnt_show_pending_trades_to_game_master(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                status = 'INITIATED', creation_date = now() + datetime.timedelta(days = -1),
                                initiator_offer = mommy.make(Offer))

        self.login_as(self.master)

        response = self._assertGetGamePage()
        self.assertNotContains(response, "Pending trades")
        self.assertNotContains(response, "trade/{0}/{1}/\">Show".format(self.game.id, trade1.id))

    def test_game_page_post_a_message_works_and_redirect_as_a_GET_request(self):
        self.assertEqual(0, Message.objects.count())

        response = self.client.post("/game/{0}/".format(self.game.id), {'message': 'test message represents'}, follow = True)
        self.assertEqual(200, response.status_code)
        self.assertEqual('GET', response.request['REQUEST_METHOD'])

        self.assertEqual(1, Message.objects.count())
        try:
            msg = Message.objects.get(game = self.game, sender = self.loginUser)
            self.assertEqual('test message represents', msg.content)
        except Message.DoesNotExist:
            self.fail("Message was not created for expected game and sender")

    def test_game_page_posting_a_message_fails_for_more_than_255_characters(self):
        response = self.client.post("/game/{0}/".format(self.game.id), {'message': 'A'*300})
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, Message.objects.count())
        self.assertContains(response, '<span class="errors">* Ensure this value has at most 255 characters (it has 300).</span>')

    def test_game_page_message_with_markdown_are_interpreted(self):
        response = self.client.post("/game/{0}/".format(self.game.id),
                                    {'message': 'Hi *this* is __a test__ and [a link](http://example.net/)'},
                                    follow = True)
        self.assertEqual(200, response.status_code)

        self.assertEqual('Hi <em>this</em> is <strong>a test</strong> and <a href=\"http://example.net/\">a link</a>',
                         Message.objects.get(game = self.game, sender = self.loginUser).content)

    def test_game_page_bleach_strips_unwanted_tags_and_attributes(self):
        response = self.client.post("/game/{0}/".format(self.game.id),
                                    {'message': '<script>var i=3;</script>Hi an <em class="test">image</em><img src="http://blah.jpg"/>'},
                                    follow = True)
        self.assertEqual(200, response.status_code)

        self.assertEqual('var i=3;\n\nHi an <em>image</em>', Message.objects.get(game = self.game, sender = self.loginUser).content)

    def test_game_page_displays_messages_for_the_game(self):
        mommy.make(Message, game = self.game, sender = self.loginUser, content = 'Show me maybe')
        mommy.make(Message, game = mommy.make(Game, end_date = now() + datetime.timedelta(days = 2)),
                       sender = self.loginUser, content = 'Do not display')

        response = self._assertGetGamePage()
        self.assertContains(response, "<div class=\"message_content\">Show me maybe</div>")
        self.assertNotContains(response, "<div class=\"message_content\">Do not display</div>")

    def test_game_page_messages_are_paginated(self):
        # 10 messages per page, extensible to 13 to accomodate 1 to 3 last messages we don't want alone on a last page
        mommy.make(Message, _quantity = 13, game = self.game, sender = self.loginUser, content = 'my test msg')

        response = self._assertGetGamePage()
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = 13)

        mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg')

        response = self._assertGetGamePage()
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = 10)

        response = self.client.get("/game/{0}/?page=2".format(self.game.id), follow = True)
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = 4)

    def test_game_page_messages_from_the_game_master_stand_out(self):
        msg = mommy.make(Message, game = self.game, sender = self.master, content = 'some message')

        response = self._assertGetGamePage()
        self.assertContains(response, "(<strong>game master</strong>)")
        self.assertContains(response, "<div class=\"message_content admin\">")

    def test_delete_message_forbidden_when_you_are_not_the_original_sender(self):
        msg = mommy.make(Message, game = self.game, sender = self.master)

        response = self.client.post("/game/{0}/deletemessage/{1}/".format(self.game.id, msg.id), follow = True)
        self.assertEqual(403, response.status_code)

    def test_delete_message_forbidden_when_not_in_POST(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser)

        response = self.client.get("/game/{0}/deletemessage/{1}/".format(self.game.id, msg.id), follow = True)
        self.assertEqual(403, response.status_code)

    def test_delete_message_returns_404_when_the_message_doesnt_exists(self):
        response = self.client.post("/game/{0}/deletemessage/987654321/".format(self.game.id), follow = True)
        self.assertEqual(404, response.status_code)

    def test_delete_message_forbidden_when_grace_period_has_expired(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser, posting_date = now() + datetime.timedelta(minutes = -120))

        response = self.client.post("/game/{0}/deletemessage/{1}/".format(self.game.id, msg.id))
        self.assertEqual(403, response.status_code)

    def test_delete_message_works_for_the_sender_during_the_grace_period(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser, posting_date = now() + datetime.timedelta(minutes = -10))

        response = self.client.post("/game/{0}/deletemessage/{1}/".format(self.game.id, msg.id), follow = True)
        self.assertEqual(200, response.status_code)

        try:
            Message.objects.get(id = msg.id)
            self.fail("Message should have been deleted")
        except Message.DoesNotExist:
            pass

    def _assertGetGamePage(self, game = None, status_code = 200):
        if game is None:
            game = self.game
        response = self.client.get("/game/{0}/".format(game.id), follow = True)
        self.assertEqual(status_code, response.status_code)
        return response

class HandViewTest(MystradeTestCase):

    def test_show_hand_doesnt_show_commodities_with_no_cards(self):
        commodity1 = mommy.make(Commodity, name = 'Commodity#1')
        commodity2 = mommy.make(Commodity, name = 'Commodity#2')
        cih1 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 1)
        cih2 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 0)

        response = self.client.get("/game/{0}/hand/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">Commodity#1</div>')
        self.assertNotContains(response, '<div class="card_name">Commodity#2</div>')

    def test_show_hand_displays_free_informations_from_ACCEPTED_trades(self):
        offer1_from_me_as_initiator = mommy.make(Offer, free_information = "I don't need to see that 1")
        offer1_from_other_as_responder = mommy.make(Offer, free_information = "Show me this 1")
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser, status = 'ACCEPTED',
                                initiator_offer = offer1_from_me_as_initiator, responder_offer = offer1_from_other_as_responder)

        offer2_from_other_as_initiator = mommy.make(Offer, free_information = "Show me this 2")
        trade2 = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser, status = 'ACCEPTED',
                                initiator_offer = offer2_from_other_as_initiator, responder_offer = mommy.make(Offer))

        offer3_from_other_as_responder = mommy.make(Offer, free_information = "I don't need to see that 3")
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser, status = 'DECLINED',
                                initiator_offer = mommy.make(Offer), responder_offer = offer3_from_other_as_responder)

        response = self.client.get("/game/{0}/hand/".format(self.game.id))

        self.assertContains(response, "Show me this 1")
        self.assertContains(response, "Show me this 2")
        self.assertNotContains(response, "I don't need to see that 1")
        self.assertNotContains(response, "I don't need to see that 3")

    def test_show_hand_doesnt_display_free_informations_from_ACCEPTED_trades_of_other_games(self):
        other_game = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = 7))
        for player in get_user_model().objects.exclude(username = 'test1'): mommy.make(GamePlayer, game = other_game, player = player)

        initiator_offer1 = mommy.make(Offer)
        responder_offer1 = mommy.make(Offer, free_information = "There is no point showing this")
        trade = mommy.make(Trade, game = other_game, initiator = self.loginUser, responder = self.alternativeUser,
                               status = 'ACCEPTED', initiator_offer = initiator_offer1, responder_offer = responder_offer1)

        initiator_offer2 = mommy.make(Offer, free_information = "There is no point showing that")
        responder_offer2 = mommy.make(Offer)
        trade = mommy.make(Trade, game = other_game, initiator = self.alternativeUser, responder = self.alternativeUser,
                               status = 'ACCEPTED', initiator_offer = initiator_offer2, responder_offer = responder_offer2)

        response = self.client.get("/game/{0}/hand/".format(self.game.id))

        self.assertNotContains(response, "There is no point showing this")
        self.assertNotContains(response, "There is no point showing that")

    def test_show_hand_displays_former_rulecards_given_in_trades(self):
        rulecard1 = mommy.make(RuleCard, public_name = 'C1', description = 'Desc1')
        rulecard2 = mommy.make(RuleCard, public_name = 'C2', description = 'Desc2')
        rih1_former = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                     ownership_date = datetime.datetime(2013, 01, 10, 18, 30, tzinfo = get_default_timezone()),
                                     abandon_date = datetime.datetime(2012, 01, 11, 10, 45, tzinfo = get_default_timezone()))
        rih1_former_duplicate = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                               ownership_date = datetime.datetime(2013, 01, 12, 16, 00, tzinfo = get_default_timezone()),
                                               abandon_date = datetime.datetime(2012, 01, 13, 18, 00, tzinfo = get_default_timezone()))
        rih2_current = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                      ownership_date = datetime.datetime(2013, 01, 15, 15, 25, tzinfo = get_default_timezone()),
                                      abandon_date = None)
        rih2_former_but_copy_of_current = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                                         ownership_date = datetime.datetime(2013, 01, 12, 12, 00, tzinfo = get_default_timezone()),
                                                         abandon_date = datetime.datetime(2013, 01, 13, 8, 5, tzinfo = get_default_timezone()))

        # one should see one rulecard 2 in rules currently owned and only one rulecard 1 in former rules
        #  (no duplicates and no copies of cards currently in hand)
        response = self.client.get("/game/{0}/hand/".format(self.game.id))

        self.assertContains(response, '<div class="card_name">C2</div>', count = 1)
        self.assertEqual([rulecard2], [rih.rulecard for rih in response.context['rule_hand']])

        self.assertContains(response, '<div class="card_name">C1</div>', count = 1)
        self.assertEqual([{'public_name': 'C1', 'description': 'Desc1'}], response.context['former_rules'])

    def test_submit_hand_displays_the_commodities(self):
        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make(Commodity, name = 'c3', color = 'colC')

        cih1 = mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                              nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                              nb_cards = 2, nb_submitted_cards = None)
        cih3 = mommy.make(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                              nb_cards = 3, nb_submitted_cards = None)

        response = self.client.get("/game/{0}/hand/submit/".format(self.game.id))
        self.assertEqual(200, response.status_code)

        self.assertEqual(3, len(response.context['commodities_formset'].initial))
        self.assertIn({'commodity_id': commodity1.id, 'name': 'c1', 'color': 'colA', 'nb_cards': 1, 'nb_submitted_cards': 1},
                      response.context['commodities_formset'].initial)
        self.assertIn({'commodity_id': commodity2.id, 'name': 'c2', 'color': 'colB', 'nb_cards': 2, 'nb_submitted_cards': 2},
                      response.context['commodities_formset'].initial)
        self.assertIn({'commodity_id': commodity3.id, 'name': 'c3', 'color': 'colC', 'nb_cards': 3, 'nb_submitted_cards': 3},
                      response.context['commodities_formset'].initial)

    def test_submit_hand_is_not_allowed_when_you_re_not_a_player_in_this_game(self):
        self.game.gameplayer_set.get(player = self.loginUser).delete() # make me not a player in this game

        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id))
        self.assertEqual(403, response.status_code)

        self.login_as(self.admin)
        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id))
        self.assertEqual(403, response.status_code)

        self.login_as(self.master)
        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id))
        self.assertEqual(403, response.status_code)

    def test_submit_hand_is_not_allowed_if_it_has_already_been_submitted(self):
        gameplayer = self.game.gameplayer_set.get(player = self.loginUser)
        gameplayer.submit_date = now()
        gameplayer.save()

        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id))
        self.assertEqual(403, response.status_code)

    def test_submit_hand_save_submitted_commodities_and_submit_date(self):
        self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make(Commodity, name = 'c3', color = 'colC')

        cih1 = mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                              nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                              nb_cards = 2, nb_submitted_cards = None)
        cih3 = mommy.make(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                              nb_cards = 3, nb_submitted_cards = None)

        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id),
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

    def test_submit_hand_cancels_or_declines_pending_trades(self):
        trade_initiated_by_me = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                               initiator_offer = mommy.make(Offer), status = 'INITIATED')
        trade_initiated_by_other_player = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                                                         initiator_offer = mommy.make(Offer),
                                                         status = 'INITIATED')
        trade_replied_by_me = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                                             initiator_offer = mommy.make(Offer),
                                             status = 'REPLIED')
        trade_replied_by_other_player = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                                                       initiator_offer = mommy.make(Offer),
                                                       status = 'REPLIED')

        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id),
                                    {'commodity-TOTAL_FORMS': 0, 'commodity-INITIAL_FORMS': 0}, follow = True)
        self.assertEqual(200, response.status_code)

        trade_initiated_by_me = Trade.objects.get(pk = trade_initiated_by_me.id)
        self.assertEqual('CANCELLED', trade_initiated_by_me.status)
        self.assertEqual(self.loginUser, trade_initiated_by_me.finalizer)
        self.assertIsNotNone(trade_initiated_by_me.closing_date)

        trade_initiated_by_other_player = Trade.objects.get(pk = trade_initiated_by_other_player.id)
        self.assertEqual('DECLINED', trade_initiated_by_other_player.status)
        self.assertEqual(self.loginUser, trade_initiated_by_other_player.finalizer)
        self.assertIsNotNone(trade_initiated_by_other_player.closing_date)

        trade_replied_by_me = Trade.objects.get(pk = trade_replied_by_me.id)
        self.assertEqual('CANCELLED', trade_replied_by_me.status)
        self.assertEqual(self.loginUser, trade_replied_by_me.finalizer)
        self.assertIsNotNone(trade_replied_by_me.closing_date)

        trade_replied_by_other_player = Trade.objects.get(pk = trade_replied_by_other_player.id)
        self.assertEqual('DECLINED', trade_replied_by_other_player.status)
        self.assertEqual(self.loginUser, trade_replied_by_other_player.finalizer)
        self.assertIsNotNone(trade_replied_by_other_player.closing_date)

class ControlBoardViewTest(MystradeTestCase):

    def setUp(self):
        super(ControlBoardViewTest, self).setUp()
        self.game_ended = mommy.make(Game, master = self.loginUser, end_date = now() + datetime.timedelta(days = -2))
        self.game_closed = mommy.make(Game, master = self.loginUser, end_date = now() + datetime.timedelta(days = -2),
                                          closing_date = now() + datetime.timedelta(days = -1))
        mommy.make(GamePlayer, game = self.game_closed, player = self.loginUser)

    def test_access_to_score_page_allowed_only_to_game_players(self):
        self._assertOperation_get(self.game_closed, "score")

        self.login_as(self.admin)
        self._assertOperation_get(self.game_closed, "score", 403)

        self.login_as(self.master)
        self._assertOperation_get(self.game_closed, "score", 403)

    def test_access_to_score_page_allowed_only_to_closed_games(self):
        self._assertOperation_get(self.game_ended, "score", 403)

    def test_access_to_control_board_allowed_only_to_game_master_and_admins_that_are_not_players(self):
        # simple player
        self._assertOperation_get(self.game, "control", 403)

        # game master
        self.login_as(self.master)
        self._assertOperation_get(self.game, "control")

        # admin not player
        self.login_as(self.admin)
        self._assertOperation_get(self.game, "control")

        # admin that is player
        self.login_as(self.admin_player)
        self._assertOperation_get(self.game, "control", 403)

    def test_close_game_allowed_only_to_game_master_and_admins_that_are_not_players(self):
        # game master
        self._assertOperation_post(self.game_ended, "close")
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNotNone(self.game_ended.closing_date)

        # admin not player
        self.game_ended.closing_date = None
        self.game_ended.save()
        self.login_as(self.admin)
        self._assertOperation_post(self.game_ended, "close")
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNotNone(self.game_ended.closing_date)

        # admin that is player
        self.game_ended.closing_date = None
        self.game_ended.save()
        mommy.make(GamePlayer, game = self.game_ended, player = get_user_model().objects.get(username = 'admin_player'))
        self.login_as(self.admin_player)
        self._assertOperation_post(self.game_ended, "close", 403)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNone(self.game_ended.closing_date)

        # simple player
        self.game_ended.closing_date = None
        self.game_ended.save()
        mommy.make(GamePlayer, game = self.game_ended, player = get_user_model().objects.get(username='test3'))
        self.login_as(get_user_model().objects.get(username='test3'))
        self._assertOperation_post(self.game_ended, "close", 403)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNone(self.game_ended.closing_date)

    def test_close_game_not_allowed_in_GET(self):
        self._assertOperation_get(self.game_ended, "close", 403)

    def test_close_game_allowed_only_on_games_ended_but_not_already_closed(self):
        game_not_ended = mommy.make(Game, master = self.loginUser, end_date = now() + datetime.timedelta(days = 2))
        self._assertOperation_post(game_not_ended, "close", 403)

        game_closed = mommy.make(Game, master = self.loginUser, end_date = now() + datetime.timedelta(days = -3),
                                     closing_date = now() + datetime.timedelta(days = -2))
        self._assertOperation_post(game_closed, "close", 403)

        self._assertOperation_post(self.game_ended, "close")

    def test_close_game_sets_the_game_closing_date(self):
        self.assertIsNone(self.game_ended.closing_date)

        self._assertOperation_post(self.game_ended, "close")

        game = Game.objects.get(pk = self.game_ended.id)
        self.assertIsNotNone(game.closing_date)

    def test_close_game_aborts_all_pending_trades(self):
        trade1 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, status = 'INITIATED',
                                initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, status = 'REPLIED',
                                initiator_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, finalizer = self.alternativeUser,
                                status = 'CANCELLED', initiator_offer = mommy.make(Offer),
                                closing_date = datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()))

        self._assertOperation_post(self.game_ended, "close")

        game = Game.objects.get(pk = self.game_ended.id)
        trade1 = Trade.objects.get(pk = trade1.id)
        trade2 = Trade.objects.get(pk = trade2.id)
        trade3 = Trade.objects.get(pk = trade3.id)

        self.assertEqual('CANCELLED', trade1.status)
        self.assertEqual(self.loginUser, trade1.finalizer)
        self.assertEqual(game.closing_date, trade1.closing_date)

        self.assertEqual('CANCELLED', trade2.status)
        self.assertEqual(self.loginUser, trade2.finalizer)
        self.assertIsNotNone(game.closing_date, trade2.closing_date)

        self.assertEqual(self.alternativeUser, trade3.finalizer)
        self.assertEqual(datetime.datetime(2012, 11, 10, 18, 30, tzinfo = get_default_timezone()), trade3.closing_date)

    def test_close_game_submits_the_commodity_cards_of_players_who_havent_manually_submitted(self):
        gp1 = mommy.make(GamePlayer, game = self.game_ended, player = self.alternativeUser)
        test6 = get_user_model().objects.get(username='test6')
        gp2_submit_date = now() + datetime.timedelta(days = -1)
        gp2 = mommy.make(GamePlayer, game = self.game_ended, player = test6, submit_date = gp2_submit_date)

        cih1 = mommy.make(CommodityInHand, game = self.game_ended, player = self.alternativeUser, nb_cards = 6, commodity__value = 1)
        cih2 = mommy.make(CommodityInHand, game = self.game_ended, player = test6, nb_cards = 4, nb_submitted_cards = 3, commodity__value = 1)

        self._assertOperation_post(self.game_ended, "close")

        gp1 = GamePlayer.objects.get(pk = gp1.id)
        gp2 = GamePlayer.objects.get(pk = gp2.id)
        cih1 = CommodityInHand.objects.get(pk = cih1.id)
        cih2 = CommodityInHand.objects.get(pk = cih2.id)

        self.assertIsNotNone(gp1.submit_date)
        self.assertEqual(gp2_submit_date, gp2.submit_date)
        self.assertEqual(6, cih1.nb_submitted_cards)
        self.assertEqual(3, cih2.nb_submitted_cards)

    @override_settings(ADMINS = (('admin', 'admin@mystrade.com'),))
    def test_close_game_calculates_and_persists_the_final_score(self):
        self._prepare_game_for_scoring(self.game_ended)

        test6 = get_user_model().objects.get(username='test6')
        test7 = get_user_model().objects.get(username='test7')
        test8 = get_user_model().objects.get(username='test8')
        mommy.make(GamePlayer, game = self.game_ended, player = self.alternativeUser)
        mommy.make(GamePlayer, game = self.game_ended, player = test6)
        mommy.make(GamePlayer, game = self.game_ended, player = test7)
        mommy.make(GamePlayer, game = self.game_ended, player = test8)

        cih7blue   = mommy.make(CommodityInHand, game = self.game_ended, player = test7,
                                    nb_cards = 3, commodity = Commodity.objects.get(ruleset = 1, name = 'Blue'))
        cih8yellow = mommy.make(CommodityInHand, game = self.game_ended, player = test8,
                                    nb_cards = 4, commodity = Commodity.objects.get(ruleset = 1, name = 'Yellow'))

        self._assertOperation_post(self.game_ended, "close")

        self.assertEqual(8, ScoreFromCommodity.objects.get(game = self.game_ended, player = self.alternativeUser, commodity__name = 'Orange').score)
        self.assertEqual(4, ScoreFromCommodity.objects.get(game = self.game_ended, player = self.alternativeUser, commodity__name = 'Blue').score)
        self.assertEqual(5, ScoreFromCommodity.objects.get(game = self.game_ended, player = self.alternativeUser, commodity__name = 'White').score)

        sfr1 = ScoreFromRule.objects.filter(game = self.game_ended, player = self.alternativeUser)
        self.assertEqual(1, len(sfr1))
        self.assertEqual('HAG05', sfr1[0].rulecard.ref_name)

        self.assertEqual(12, ScoreFromCommodity.objects.get(game = self.game_ended, player = test6, commodity__name = 'Orange').score)
        self.assertEqual(6, ScoreFromCommodity.objects.get(game = self.game_ended, player = test6, commodity__name = 'Blue').score)
        self.assertEqual(0, ScoreFromCommodity.objects.get(game = self.game_ended, player = test6, commodity__name = 'White').score)

        sfr2 = ScoreFromRule.objects.filter(game = self.game_ended, player = test6)
        self.assertEqual(1, len(sfr2))
        self.assertEqual('HAG04', sfr2[0].rulecard.ref_name)

        # notification emails sent
        self.assertEqual(5, len(mail.outbox))
        list_recipients = [msg.to[0] for msg in mail.outbox]

        self.assertEqual(1, list_recipients.count('test6@test.com'))
        emailTest6 = mail.outbox[list_recipients.index('test6@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test2'.format(self.game_ended.id), emailTest6.subject)
        self.assertIn('Test2 has closed game #{0}'.format(self.game_ended.id), emailTest6.body)
        self.assertIn('Congratulations, you are the winner !', emailTest6.body)
        self.assertIn('You scored 18 points, divided as:', emailTest6.body)
        self.assertIn('- 3 scored Orange cards x 4 = 12 points', emailTest6.body)
        self.assertIn('- 3 scored Blue cards x 2 = 6 points', emailTest6.body)
        self.assertIn('- 4 scored White cards x 0 = 0 points', emailTest6.body)
        self.assertIn('- Rule : (4) Since there are 4 white cards (more than three), their value is set to zero.', emailTest6.body)
        self.assertIn('/game/{0}/score/'.format(self.game_ended.id), emailTest6.body)

        self.assertEqual(1, list_recipients.count('test5@test.com'))
        emailTest5 = mail.outbox[list_recipients.index('test5@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test2'.format(self.game_ended.id), emailTest5.subject)
        self.assertIn('Test2 has closed game #{0}'.format(self.game_ended.id), emailTest5.body)
        self.assertIn('Congratulations, you are in the second place !', emailTest5.body)
        self.assertIn('You scored 17 points, divided as:', emailTest5.body)
        self.assertIn('- 2 scored Orange cards x 4 = 8 points', emailTest5.body)
        self.assertIn('- 2 scored Blue cards x 2 = 4 points', emailTest5.body)
        self.assertIn('- 1 scored White card x 5 = 5 points', emailTest5.body)
        self.assertIn('- Rule : (5) Since there are 2 blue card(s), only 2 orange card(s) score.', emailTest5.body)
        self.assertIn('/game/{0}/score/'.format(self.game_ended.id), emailTest5.body)

        self.assertEqual(1, list_recipients.count('test7@test.com'))
        emailTest7 = mail.outbox[list_recipients.index('test7@test.com')]
        self.assertIn('Congratulations, you are in the third place !', emailTest7.body)
        self.assertIn('You scored 6 points', emailTest7.body)

        self.assertEqual(1, list_recipients.count('test8@test.com'))
        emailTest8 = mail.outbox[list_recipients.index('test8@test.com')]
        self.assertIn('You\'re 4th of 4 players.', emailTest8.body)
        self.assertIn('You scored 4 points', emailTest8.body)

        self.assertEqual(1, list_recipients.count('admin@mystrade.com'))
        emailAdmin = mail.outbox[list_recipients.index('admin@mystrade.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test2'.format(self.game_ended.id), emailAdmin.subject)
        self.assertIn('Test2 has closed game #{0}'.format(self.game_ended.id), emailAdmin.body)
        self.assertIn('Final Scores:', emailAdmin.body)
        self.assertIn('1st. test6 : 18 points', emailAdmin.body)
        self.assertIn('2nd. test5 : 17 points', emailAdmin.body)
        self.assertIn('3rd. test7 : 6 points', emailAdmin.body)
        self.assertIn('4th. test8 : 4 points', emailAdmin.body)
        self.assertIn('/game/{0}/control/'.format(self.game_ended.id), emailAdmin.body)

    def test_control_board_shows_current_scoring_during_game(self):
        self._prepare_game_for_scoring(self.game)

        test6 = get_user_model().objects.get(username='test6')

        # a trap we shouldn't fall in
        mommy.make(ScoreFromCommodity, game = self.game, player = self.alternativeUser, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange'),
                       nb_submitted_cards = 3, nb_scored_cards = 3, actual_value = 4, score = 12)
        mommy.make(ScoreFromCommodity, game = self.game, player = test6, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange'),
                       nb_submitted_cards = 1, nb_scored_cards = 1, actual_value = 4, score = 4)

        self.login_as(self.master)
        response = self.client.get("/game/{0}/{1}/".format(self.game.id, "control"), follow = True)
        self.assertEqual(200, response.status_code)

        scoresheets = response.context['scoresheets']
        self.assertEqual(9, len(scoresheets))
        self.assertEqual('test6', scoresheets[0].player_name)
        self.assertEqual(18, scoresheets[0].total_score)
        self.assertEqual('test5', scoresheets[1].player_name)
        self.assertEqual(17, scoresheets[1].total_score) # only two orange cards scored because of HAG05

    def test_control_board_warns_when_the_current_scoring_contains_random_scores(self):
        self._prepare_game_for_scoring(self.game)

        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG15')) # rule that leads to random scores when a hand has > 13 commodity cards
        cih1red = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser,
                                 nb_cards = 10, commodity = Commodity.objects.get(ruleset = 1, name = 'Red'))

        self.login_as(self.master)
        response = self.client.get("/game/{0}/{1}/".format(self.game.id, "control"), follow = True)
        self.assertEqual(200, response.status_code)

        self.assertTrue(response.context['random_scoring']) # the whole game scoring is tagged
        for scoresheet in response.context['scoresheets']:
            if scoresheet.player_name == 'test5':
                self.assertTrue(getattr(scoresheet, 'is_random', False)) # the player's scoresheet is tagged
                random_rule = False
                for sfr in scoresheet.scores_from_rule:
                    if getattr(sfr, 'is_random', False) and sfr.rulecard.ref_name == 'HAG15':
                        random_rule = True
                self.assertTrue(random_rule) # the score_from_rule line than introduces the randomization is tagged

    def _prepare_game_for_scoring(self, game):
        game.rules.add(RuleCard.objects.get(ref_name = 'HAG04'))
        game.rules.add(RuleCard.objects.get(ref_name = 'HAG05'))

        cih1orange = mommy.make(CommodityInHand, game = game, player = self.alternativeUser,
                                    nb_cards = 3, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange')) # value = 4
        cih1blue   = mommy.make(CommodityInHand, game = game, player = self.alternativeUser,
                                    nb_cards = 2, commodity = Commodity.objects.get(ruleset = 1, name = 'Blue')) # value = 2
        cih1white  = mommy.make(CommodityInHand, game = game, player = self.alternativeUser,
                                    nb_cards = 1, commodity = Commodity.objects.get(ruleset = 1, name = 'White')) # value = 5 or 0

        test6 = get_user_model().objects.get(username='test6')
        cih2orange = mommy.make(CommodityInHand, game = game, player = test6,
                                    nb_cards = 3, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange'))
        cih2blue   = mommy.make(CommodityInHand, game = game, player = test6,
                                    nb_cards = 3, commodity = Commodity.objects.get(ruleset = 1, name = 'Blue'))
        cih2white  = mommy.make(CommodityInHand, game = game, player = test6,
                                    nb_cards = 4, commodity = Commodity.objects.get(ruleset = 1, name = 'White'))

    def _assertOperation_get(self, game, operation, status_code = 200):
        response = self.client.get("/game/{0}/{1}/".format(game.id, operation), follow = True)
        self.assertEqual(status_code, response.status_code)

    def _assertOperation_post(self, game, operation, status_code = 200):
        response = self.client.post("/game/{0}/{1}/".format(game.id, operation), follow = True)
        self.assertEqual(status_code, response.status_code)

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['test_users.json', # from profile app
                'test_games.json']

    def setUp(self):
        self.game =             Game.objects.get(id = 1)
        self.master =           self.game.master
        self.loginUser =        get_user_model().objects.get(username = "test2")
        self.alternativeUser =  get_user_model().objects.get(username = 'test5')

        self.client.login(username = self.loginUser.username, password = 'test')

    def test_submit_hand_is_transactional(self):
        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make(Commodity, name = 'c2', color = 'colB')

        cih1 = mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                              nb_cards = 1, nb_submitted_cards = None)
        cih2 = mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                              nb_cards = 2, nb_submitted_cards = None)

        # set a nb_submitted_cards < 0 on the last form to make the view fail on the last iteration
        response = self.client.post("/game/{0}/hand/submit/".format(self.game.id),
            {'commodity-TOTAL_FORMS': 2, 'commodity-INITIAL_FORMS': 2,
             'commodity-0-commodity_id': commodity1.id, 'commodity-0-nb_submitted_cards': 1,
             'commodity-1-commodity_id': commodity2.id, 'commodity-1-nb_submitted_cards': -3 }, follow = True)

        self.assertEqual(200, response.status_code)

        self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

        for commodity in CommodityInHand.objects.filter(game = self.game, player = self.loginUser):
            self.assertIsNone(commodity.nb_submitted_cards)

    def test_close_game_is_transactional(self):
        def mock_persist(self):
            mommy.make(ScoreFromCommodity, game = self.gameplayer.game, player = self.gameplayer.player)
            mommy.make(ScoreFromRule, game = self.gameplayer.game, player = self.gameplayer.player)
            raise RuntimeError
        Scoresheet.persist = mock_persist

        self.client.logout()
        self.assertTrue(self.client.login(username = self.master.username, password = 'test'))

        self.game.end_date = now() + datetime.timedelta(days = -1)
        self.game.save()

        cih = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, commodity__value = 1, nb_cards = 1)

        trade = mommy.make(Trade, game = self.game, status = 'INITIATED', initiator = self.alternativeUser,
                               responder = get_user_model().objects.get(username = 'test6'),
                               initiator_offer = mommy.make(Offer), finalizer = None)

        response = self.client.post("/game/{0}/close/".format(self.game.id), follow = True)

        self.assertEqual(200, response.status_code)

        game = Game.objects.get(pk = self.game.id)
        self.assertIsNone(game.closing_date)

        trade = Trade.objects.get(pk = trade.id)
        self.assertIsNone(trade.closing_date)

        cih = CommodityInHand.objects.get(pk = cih.id)
        self.assertIsNone(cih.nb_submitted_cards)

        gameplayer = GamePlayer.objects.get(game = self.game, player = self.alternativeUser)
        self.assertIsNone(gameplayer.submit_date)

        self.assertEqual(0, ScoreFromCommodity.objects.filter(game = self.game).count())
        self.assertEqual(0, ScoreFromRule.objects.filter(game = self.game).count())

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
            self.users.append(mommy.make(get_user_model(), username = i))
            self.rules.append(mommy.make(RuleCard, ref_name = i))
            self.commodities.append(mommy.make(Commodity, name = i))

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
        game = mommy.make(Game, ruleset = ruleset, rules = self.rules, end_date = now() + datetime.timedelta(days = 7))
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