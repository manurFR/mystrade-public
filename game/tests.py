import ast
import datetime
from django.contrib.auth import get_user_model

from django.core import mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.aggregates import Sum
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.datetime_safe import strftime
from django.utils.formats import date_format
from django.utils.timezone import now, utc, localtime
from model_mommy import mommy
from game import views

from game.deal import InappropriateDealingException, RuleCardDealer, deal_cards, \
    prepare_deck, dispatch_cards, CommodityCardDealer
from game.forms import validate_number_of_players, validate_dates
from game.helpers import rules_in_hand, rules_formerly_in_hand, commodities_in_hand, known_rules, free_informations_until_now
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer, Message
from game.views import SECONDS_BEFORE_OFFLINE
from ruleset.models import Ruleset, RuleCard, Commodity
from scoring.card_scoring import Scoresheet
from scoring.models import ScoreFromCommodity, ScoreFromRule
from trade.models import Offer, Trade, TradedCommodities
from utils.tests import MystradeTestCase

class EntryPageViewTest(MystradeTestCase):

    def test_url_with_no_path_should_display_game_list_page_if_authenticated_and_the_cookie_is_not_set(self):
        """ ie http://host.com/ should actually display the same page as http://host.com/game/ """
        response = self.client.get("")
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "game/game_list.html")

        self.client.logout()
        response = self.client.get("")
        self.assertRedirects(response, "/login?next=/")

    def test_url_with_no_path_should_redirect_to_game_board_if_cookie_is_set(self):
        # preparation : set a cookie
        self.client.get(reverse('game', args = [self.game.id]))
        self.assertTrue(self.client.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual(str(self.game.id), self.client.cookies['mystrade-lastVisitedGame-id'].value)

        # test
        response = self.client.get("")
        self.assertRedirects(response, reverse('game', args = [self.game.id]))

    def test_url_with_no_path_doesnt_redirect_when_cookie_is_set_to_unknown_game(self):
        # preparation : set a cookie
        self.client.cookies['mystrade-lastVisitedGame-id'] = '123456'

        # test
        response = self.client.get("", follow = True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "game/game_list.html")
        self.assertTemplateNotUsed(response, "game/board.html")

    def test_url_with_no_path_doesnt_redirect_when_cookie_is_set_to_a_game_for_which_the_user_doesnt_have_access_rights(self):
        # preparation : set a cookie
        other_game = mommy.make(Game)
        self.client.cookies['mystrade-lastVisitedGame-id'] = str(other_game.id)

        # test
        response = self.client.get("", follow = True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "game/game_list.html")
        self.assertTemplateNotUsed(response, "game/board.html")

    def test_game_list_never_redirects_to_game_board_even_if_a_cookie_is_set(self):
        # preparation : set a cookie
        self.client.get(reverse('game', args = [self.game.id]))
        self.assertTrue(self.client.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual(str(self.game.id), self.client.cookies['mystrade-lastVisitedGame-id'].value)

        # test
        response = self.client.get(reverse("game_list"))
        self.assertTemplateUsed(response, "game/game_list.html")

    def test_game_list_needs_login(self):
        response = self.client.get(reverse("game_list"))
        self.assertEqual(200, response.status_code)

        self.client.logout()
        response = self.client.get(reverse("game_list"))
        self.assertRedirects(response, "/login?next=/game/")

    def test_game_list_query(self):
        game_mastered = mommy.make(Game, master = self.loginUser,
                                       end_date = utc.localize(datetime.datetime(2022, 11, 1, 12, 0, 0)))
        mommy.make(GamePlayer, game = game_mastered, player = self.alternativeUser)
        other_game = mommy.make(Game, master = self.alternativeUser,
                               end_date = utc.localize(datetime.datetime(2022, 11, 5, 12, 0, 0)))

        response = self.client.get(reverse("game_list"))

        self.assertEqual(200, response.status_code)
        self.assertItemsEqual([self.game, game_mastered], list(response.context['games']))
        self.assertNotIn(other_game, response.context['games'])

    def test_game_list_dates_are_displayed_in_user_timezone(self):
        self.game.start_date =  utc.localize(datetime.datetime(2013, 9, 5, 23, 30, 0))
        self.game.save()

        self.loginUser.timezone = "Europe/Paris" # in september, Paris is UTC+2 (including DST)
        self.loginUser.save()

        response = self.client.get(reverse("game_list"))
        self.assertContains(response, "09/06/2013 1:30 a.m.")
        self.assertNotContains(response, "09/05/2013 11:30 p.m.")

        self.loginUser.timezone = "America/Phoenix" # Phoenix, AZ is UTC-7 and doesn't have DST
        self.loginUser.save()

        response = self.client.get(reverse("game_list"))
        self.assertContains(response, "09/05/2013 4:30 p.m.")
        self.assertNotContains(response, "09/05/2013 11:30 p.m.")

class GameCreationViewsTest(TestCase):
    fixtures = ['initial_data.json',
                'test_users.json'] # from profile app

    def setUp(self):
        self.testUserCanCreate = get_user_model().objects.get(username = 'test1')
        self.testUsersNoCreate = get_user_model().objects.exclude(user_permissions__codename = "add_game")
        self.ruleset = Ruleset.objects.get(id = 1)
        self.client.login(username = 'test1', password = 'test')

    def test_create_game_only_with_the_permission(self):
        # initially logged as testUserCanCreate
        response = self.client.get("/game/create/")
        self.assertEqual(200, response.status_code)
        self.client.logout()

        self.assertTrue(self.client.login(username = 'test9', password = 'test'))
        response = self.client.get("/game/create/")
        self.assertEqual(302, response.status_code)

    def test_create_game_without_dates_fails(self):
        response = self.client.post("/game/create/", {'ruleset': self.ruleset, 'start_date': '', 'end_date': '11/13/2012 00:15'})
        self.assertFormError(response, 'form', 'start_date', 'This field is required.')

        response = self.client.post("/game/create/", {'ruleset': self.ruleset, 'start_date':'11/10/2012 15:30', 'end_date': ''})
        self.assertFormError(response, 'form', 'end_date', 'This field is required.')

    def test_create_game_without_enough_players(self):
        response = self.client.post("/game/create/", {'ruleset': self.ruleset.id,
                                                      'start_date': '11/10/2012 18:30', 
                                                      'end_date': '11/13/2012 00:15',
                                                      'players': self.testUsersNoCreate[0].id})
        self.assertFormError(response, 'form', None, 'Please select at least 3 players (as many as there are mandatory rule cards in this ruleset).')

    def test_create_game_first_page(self):
        response = self.client.post("/game/create/", {'ruleset': self.ruleset.id,
                                                      'start_date': '11/10/2012 18:30', # user test1 is in timezone Europe/Paris, so -1 hour in winter,
                                                      'end_date': '11/13/2012 00:15',   #  so the UTC datetimes are 1 hour earlier
                                                      'players': [player.id for player in self.testUsersNoCreate]})
        self.assertRedirects(response, "/game/selectrules/")
        self.assertEqual(1, self.client.session['ruleset'])
        self.assertEqual(1352568600, self.client.session['start_date'])
        self.assertEqual(1352762100, self.client.session['end_date'])
        self.assertItemsEqual([player.id for player in self.testUsersNoCreate], self.client.session['players'])

    def test_access_select_rules_with_incomplete_session_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")
 
    def test_access_select_rules_without_enough_players_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session['start_date'] = 1352568600
        session['end_date'] = 1352762100
        session['players'] = [self.testUsersNoCreate[0].id]
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_select_rules_with_invalid_dates_redirects_to_first_page(self):
        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session['start_date'] = 1352568600
        session['end_date'] = 1352762100
        session['players'] = [self.testUsersNoCreate[0].id]
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertRedirects(response, "/game/create/")

    def test_access_select_rules(self):
        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session['start_date'] = 1352568600
        session['end_date'] = 1352762100
        session['players'] = [user.id for user in self.testUsersNoCreate]
        session.save()
        response = self.client.get("/game/selectrules/")
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'game/select_rules.html')

    def test_create_game_with_too_many_rulecards(self):
        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session['start_date'] = 1352568600
        session['end_date'] = 1352762100
        session['players'] = [user.id for user in self.testUsersNoCreate[:4]] # only 4 players
        session.save()
        response = self.client.post("/game/selectrules/",
                                    {'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG01').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG02').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG03').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG04').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG05').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG06').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG07').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG08').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG09').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG10').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG11').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG12').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG13').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG14').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG15').id): 'False'
                                    })
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'game/select_rules.html')
        self.assertEqual("Please select at most 4 rule cards (including the mandatory ones)", response.context['error'])
        self.assertEqual(4, response.context['nb_max_rulecards'])

    def test_max_rulecards_depends_on_number_of_starting_rules(self):
        self.ruleset.starting_rules = 3
        self.ruleset.save()

        session = self.client.session
        session['ruleset'] = self.ruleset.id
        session['start_date'] = 1352568600
        session['end_date'] = 1352762100
        session['players'] = [user.id for user in self.testUsersNoCreate[:4]] # only 4 players
        session.save()
        response = self.client.get("/game/selectrules/")

        self.assertEqual(6, response.context['nb_max_rulecards'])

    @override_settings(ADMINS = (('admin', 'admin@mystrade.com'),))
    def test_create_game_complete_save_and_clean_session(self):
        self.testUserCanCreate.timezone = "Indian/Maldives" # UTC+5 no DST -- we'll check that the datetimes will be kept in utc
        self.testUserCanCreate.save()
        response = self.client.post("/game/create/", {'ruleset': self.ruleset.id,
                                                      'start_date': '11/10/2012 18:30',
                                                      'end_date': '11/13/2015 00:15',
                                                      'players': [player.id for player in self.testUsersNoCreate][:4]})
        self.assertRedirects(response, "/game/selectrules/")
        response = self.client.post("/game/selectrules/",
                                    {'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG01').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG02').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG03').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG04').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG05').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG06').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG07').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG08').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG09').id): 'True',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG10').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG11').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG12').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG13').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG14').id): 'False',
                                     'rulecard_{0}'.format(RuleCard.objects.get(ruleset = self.ruleset, ref_name = 'HAG15').id): 'False'
                                    })

        created_game = Game.objects.get(master = self.testUserCanCreate.id)
        self.assertRedirects(response, "/game/{0}/".format(created_game.id))

        self.assertEqual(1, created_game.ruleset_id)
        self.assertEqual(datetime.datetime(2012, 11, 10, 13, 30, tzinfo = utc), created_game.start_date)
        self.assertEqual(datetime.datetime(2015, 11, 12, 19, 15, tzinfo = utc), created_game.end_date)
        self.assertItemsEqual(list(self.testUsersNoCreate)[:4], list(created_game.players.all()))
        self.assertListEqual([1, 2, 3, 9], [rule.id for rule in created_game.rules.all()])
        self.assertFalse('ruleset' in self.client.session)
        self.assertFalse('start_date' in self.client.session)
        self.assertFalse('end_date' in self.client.session)
        self.assertFalse('players' in self.client.session)
        self.assertFalse('profiles' in self.client.session)

        # notification emails sent
        list_recipients = [msg.to[0] for msg in mail.outbox]

        self.assertEqual(1, list_recipients.count('test2@test.com'))
        emailTest2 = mail.outbox[list_recipients.index('test2@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been created by test1'.format(created_game.id), emailTest2.subject)
        self.assertIn('Test1 has just created game #{0} with the "Original Haggle (1969)" ruleset'.format(created_game.id), emailTest2.body)
        self.assertEqual(2, emailTest2.body.count('- Rule'))
        self.assertIn("The game has already started ! Start trading here:", emailTest2.body)
        self.assertIn('/game/{0}'.format(created_game.id), emailTest2.body)

        self.assertEqual(1, list_recipients.count('admin@mystrade.com'))
        emailAdmin = mail.outbox[list_recipients.index('admin@mystrade.com')]
        self.assertEqual('[MysTrade] Game #{0} has been created by test1'.format(created_game.id), emailAdmin.subject)
        self.assertIn('Test1 has just created game #{0} with the "Original Haggle (1969)" ruleset'.format(created_game.id), emailAdmin.body)
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

class GameBoardMainTest(MystradeTestCase):

    def test_game_board_returns_a_404_if_the_game_id_doesnt_exist(self):
        response = self.client.get("/game/999999999/")
        self.assertEqual(404, response.status_code)

    def test_game_board_access_forbidden_for_users_not_related_to_the_game_except_admins(self):
        self._assertGetGamePage()

        self.login_as(self.admin)
        self._assertGetGamePage()

        self.login_as(self.master)
        self._assertGetGamePage()

        self.login_as(self.unrelated_user)
        self._assertGetGamePage(status_code = 403)

    def test_game_board_shows_starting_or_finishing_date(self):
        # Note: we add a couple of seconds to each date in the future because otherwise the timeuntil filter would sadly go
        #  from "2 days" to "1 day, 23 hours" between the instant the games' models are created and the few milliseconds it
        #  takes to call the template rendering. Sed fugit interea tempus fugit irreparabile, singula dum capti circumvectamur amore.

        # before start_date
        game1 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = 2, seconds = 2),
                               end_date = now() + datetime.timedelta(days = 4, seconds = 2))

        response = self.client.get("/game/{0}/".format(game1.id))
        self.assertContains(response, u"starting in 2\xa0days")

        # during the game
        game2 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -2),
                               end_date = now() + datetime.timedelta(days = 4, seconds = 2))

        response = self.client.get("/game/{0}/".format(game2.id))
        self.assertContains(response, u"ending in 4\xa0days")

        # after end_date
        game3 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -4),
                               end_date = now() + datetime.timedelta(days = -2))

        response = self.client.get("/game/{0}/".format(game3.id))
        self.assertContains(response, u"ended 2\xa0days ago")

        # after closing_date
        game4 = mommy.make(Game, master = self.loginUser, start_date = now() + datetime.timedelta(days = -4),
                               end_date = now() + datetime.timedelta(days = -2), closing_date = now() + datetime.timedelta(days = -1))

        response = self.client.get("/game/{0}/".format(game4.id))
        self.assertContains(response, u"closed 1\xa0day ago")

    def test_game_board_with_trade_id_displays_the_corresponding_trade(self):
        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'INITIATED', initiator_offer = mommy.make(Offer))

        response = self.client.get("/game/{0}/trade/{1}/".format(self.game.id, trade.id))

        self.assertEqual(trade.id, response.context['trade_id'])
        self.assertContains(response, "refreshTrade({0});".format(trade.id))

    def test_game_board_with_trade_id_of_another_game_doesnt_displays_the_corresponding_trade(self):
        other_game = mommy.make(Game)
        trade = mommy.make(Trade, game = other_game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'INITIATED', initiator_offer = mommy.make(Offer))

        response = self.client.get("/game/{0}/trade/{1}/".format(self.game.id, trade.id))

        self.assertIsNone(response.context['trade_id'])
        self.assertNotContains(response, "refreshTrade({0});".format(trade.id))

    def test_game_board_with_trade_id_of_other_players_doesnt_displays_the_corresponding_trade(self):
        trade = mommy.make(Trade, game = self.game, initiator = self.admin_player, responder = self.alternativeUser,
                           status = 'INITIATED', initiator_offer = mommy.make(Offer))

        response = self.client.get("/game/{0}/trade/{1}/".format(self.game.id, trade.id))

        self.assertIsNone(response.context['trade_id'])
        self.assertNotContains(response, "refreshTrade({0});".format(trade.id))

    def test_game_board_shows_online_users(self):
        response = self._assertGetGamePage()
        # the loginUser is always identified as online since the middleware has been run by the time we get to the view func
        self.assertContains(response, "updateOnlineStatus([{0}]);".format(self.loginUser.id))

        date_now = now()
        player5 = GamePlayer.objects.get(game=self.game, player__id=5)
        player5.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 20)
        player5.save()
        player6 = GamePlayer.objects.get(game=self.game, player__id=6)
        player6.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 10)
        player6.save()
        player7 = GamePlayer.objects.get(game=self.game, player__id=7)
        player7.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE - 10)
        player7.save()

        response = self._assertGetGamePage()
        # only the players who were last seen in less than SECONDS_BEFORE_OFFLINE seconds are identified as online
        self.assertContains(response, "updateOnlineStatus([{0}, 5, 6]);".format(self.loginUser.id))

    def test_game_board_cookie_set_for_active_games(self):
        self.game.start_date = now() + datetime.timedelta(days = -2)
        self.game.end_date = now() + datetime.timedelta(days = 2)
        self.game.save()

        response = self._assertGetGamePage()

        self.assertTrue(response.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual(str(self.game.id), response.cookies['mystrade-lastVisitedGame-id'].value)

    def test_game_board_cookie_not_set_for_games_not_started(self):
        self.game.start_date = now() + datetime.timedelta(days = 2)
        self.game.end_date = now() + datetime.timedelta(days = 4)
        self.game.save()

        response = self._assertGetGamePage()

        self.assertFalse(response.cookies.has_key('mystrade-lastVisitedGame-id'))

    def test_game_board_the_cookie_keeps_the_last_visited_game(self):
        self.game.start_date = now() + datetime.timedelta(days = -2)
        self.game.end_date = now() + datetime.timedelta(days = 2)
        self.game.save()

        response = self._assertGetGamePage()

        game2 = mommy.make(Game, start_date = now() + datetime.timedelta(days = -1), end_date = now() + datetime.timedelta(days = 3))
        mommy.make(GamePlayer, game = game2, player = self.loginUser)

        response = self._assertGetGamePage(game = game2)

        self.assertTrue(response.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual(str(game2.id), response.cookies['mystrade-lastVisitedGame-id'].value)

    def test_game_board_the_cookie_is_deleted_if_the_game_is_closed(self):
        # actually, a client is asked to delete a cookie by setting its expiration date to 1970/01/01
        # cookie creation
        self.game.start_date = now() + datetime.timedelta(days = -2)
        self.game.end_date = now() + datetime.timedelta(minutes = -1)
        self.game.save()

        response = self._assertGetGamePage()

        self.assertTrue(response.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual(str(self.game.id), response.cookies['mystrade-lastVisitedGame-id'].value)
        self.assertTrue(self.client.cookies.has_key('mystrade-lastVisitedGame-id'))

        # seeing a game board page for another closed game doesn't change the cookie value and doesn't delete it
        game2 = mommy.make(Game, closing_date = now() + datetime.timedelta(days = -1))
        mommy.make(GamePlayer, game = game2, player = self.loginUser)

        response = self._assertGetGamePage(game = game2)
        self.assertTrue(self.client.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertNotEqual('Thu, 01-Jan-1970 00:00:00 GMT', self.client.cookies['mystrade-lastVisitedGame-id']['expires'])
        self.assertEqual(str(self.game.id), self.client.cookies['mystrade-lastVisitedGame-id'].value)

        # seeing a game board for the lastVisitedGame once it has been closed should delete the cookie
        self.game.closing_date = now() + datetime.timedelta(seconds = -5)
        self.game.save()

        response = self._assertGetGamePage()
        self.assertTrue(response.cookies.has_key('mystrade-lastVisitedGame-id'))
        self.assertEqual('Thu, 01-Jan-1970 00:00:00 GMT', response.cookies['mystrade-lastVisitedGame-id']['expires'])

    def _assertGetGamePage(self, game = None, status_code = 200):
        if game is None:
            game = self.game
        response = self.client.get(reverse('game', args = [game.id]), follow = True)
        self.assertEqual(status_code, response.status_code)
        return response

class GameBoardZoneHandTest(MystradeTestCase):

    def test_game_board_show_commodities_owned_to_players(self):
        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser,
                          commodity = Commodity.objects.get(ruleset = 1, name = "Blue"), nb_cards = 1)

        response = self._assertGetGamePage()
        self.assertContains(response, 'title="Blue"', count = 1)

        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser,
                          commodity = Commodity.objects.get(ruleset = 1, name = "Red"), nb_cards = 4, nb_submitted_cards = 2)

        response = self._assertGetGamePage()
        self.assertContains(response, 'title="Blue"', count = 1)
        self.assertContains(response, 'title="Red"', count = 4)

    def test_game_board_doesnt_show_commodities_with_no_cards(self):
        commodity1 = mommy.make(Commodity, name = 'Commodity1', color="col1", symbol="a")
        commodity2 = mommy.make(Commodity, name = 'Commodity2', color="col2", symbol="b")
        cih1 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity1, nb_cards = 1)
        cih2 = CommodityInHand.objects.create(game = self.game, player = self.loginUser, commodity = commodity2, nb_cards = 0)

        response = self._assertGetGamePage()

        self.assertContains(response, 'title="Commodity1"', count = 1)
        self.assertNotContains(response, 'title="Commodity2"')

    def test_game_board_separate_submitted_and_nonsubmitted_commodities_to_players_who_have_submitted_their_hand(self):
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

        self.assertContains(response, 'title="Blue"', count = 1)
        self.assertContains(response, 'title="Blue -- not submitted"', count = 2)
        self.assertContains(response, 'title="Red"', count = 2)
        self.assertNotContains(response, 'title="Orange"')
        self.assertContains(response, 'title="Orange -- not submitted"', count = 1)

    def test_game_board_displays_rulecards(self):
        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = RuleCard.objects.get(ref_name = 'HAG04'),
                          abandon_date = None)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = RuleCard.objects.get(ref_name = 'HAG10'),
                          abandon_date = None)

        response = self._assertGetGamePage()

        self.assertContains(response, '<div class="rulecard_name">4</div>', count = 1)
        self.assertContains(response, '<div class="rulecard_desc">If a player has more than three white cards, all of his/her white cards lose their value.</div>', count = 1)

        self.assertContains(response, '<div class="rulecard_name">10</div>', count = 1)
        self.assertContains(response, '<div class="rulecard_desc">Each set of five different colors gives a bonus of 10 points.</div>', count = 1)

    def test_game_board_displays_former_rulecards_given_in_trades(self):
        rulecard1 = RuleCard.objects.get(ref_name = 'HAG04')
        rulecard2 = RuleCard.objects.get(ref_name = 'HAG10')
        rih1_former =           mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                           abandon_date = utc.localize(datetime.datetime(2012, 01, 11, 10, 45)))
        rih1_former_duplicate = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard1,
                                           abandon_date = utc.localize(datetime.datetime(2012, 01, 13, 18, 00)))
        rih2_current =          mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                           abandon_date = None)
        rih2_former_but_copy_of_current = \
                                mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rulecard2,
                                           abandon_date = utc.localize(datetime.datetime(2013, 01, 13, 8, 5)))

        response = self._assertGetGamePage()

        self.assertEqual([rulecard2], [rih.rulecard for rih in response.context['rulecards']])
        # multiple occurences of former rulecards are displayed, even if the rulecard is also in the current hand
        self.assertEqual([rulecard1, rulecard1, rulecard2], [rih.rulecard for rih in response.context['former_rulecards']])

    def test_game_board_displays_free_informations_from_ACCEPTED_trades(self):
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

        response = self._assertGetGamePage()

        self.assertContains(response, "Show me this 1")
        self.assertContains(response, "Show me this 2")
        self.assertNotContains(response, "I don't need to see that 1")
        self.assertNotContains(response, "I don't need to see that 3")

    def test_game_board_doesnt_display_free_informations_from_ACCEPTED_trades_of_other_games(self):
        other_game = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = 7))
        for player in get_user_model().objects.exclude(username = 'test1'): mommy.make(GamePlayer, game = other_game, player = player)

        initiator_offer1 = mommy.make(Offer)
        responder_offer1 = mommy.make(Offer, free_information = "There is no point showing this")
        trade = mommy.make(Trade, game = other_game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'ACCEPTED', initiator_offer = initiator_offer1, responder_offer = responder_offer1)

        initiator_offer2 = mommy.make(Offer, free_information = "There is no point showing that")
        responder_offer2 = mommy.make(Offer)
        trade = mommy.make(Trade, game = other_game, initiator = self.alternativeUser, responder = self.loginUser,
                           status = 'ACCEPTED', initiator_offer = initiator_offer2, responder_offer = responder_offer2)

        response = self._assertGetGamePage()

        self.assertNotContains(response, "There is no point showing this")
        self.assertNotContains(response, "There is no point showing that")

    def _assertGetGamePage(self, game = None, status_code = 200):
        if game is None:
            game = self.game
        response = self.client.get("/game/{0}/".format(game.id), follow = True)
        self.assertEqual(status_code, response.status_code)
        return response

class GameBoardTabRecentlyTest(MystradeTestCase):

    def test_tab_recently_displays_messages_for_the_game(self):
        mommy.make(Message, game = self.game, sender = self.loginUser, content = 'Show me maybe')
        mommy.make(Message, game = mommy.make(Game, end_date = now() + datetime.timedelta(days = 2)),
                   sender = self.loginUser, content = 'Do not display')

        response = self._getTabRecently()
        self.assertContains(response, "<div class=\"message_content\">Show me maybe</div>")
        self.assertNotContains(response, "<div class=\"message_content\">Do not display</div>")

    def test_tab_recently_messages_are_paginated(self):
        """ This test automatically adapts to the chosen value of EVENTS_PAGINATION in game.views """
        pagination = views.EVENTS_PAGINATION
        last_date = utc.localize(datetime.datetime(2012, 01, 10, 23, 00, 00))
        for i in range(int(2.5 * pagination)): # prepare 2 full pages and one last partial page of messages
            mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg',
                       posting_date = last_date + datetime.timedelta(hours = -i))
        # add an event of id 0 for the game start
        total_nb_of_events = int(2.5 * pagination) + 1

        last_in_page_1  = total_nb_of_events - pagination
        first_in_page_2 = total_nb_of_events - pagination - 1
        last_in_page_2  = total_nb_of_events - (2 * pagination)
        first_in_page_3 = total_nb_of_events - (2 * pagination) - 1

        somewhere_in_page_1 = total_nb_of_events - int(pagination / 2)

        # fetch page 1 (initial load)
        response = self._getTabRecently()
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = pagination) # 'pagination' messages per page
        self.assertContains(response, '$("#link_show_previous_events").on("click", function() { refreshEvents(); });')
        self.assertContains(response, '$("#link_show_more_events").on("click", function() {{ refreshEvents("{0}"); }});'
                                                                                                .format(first_in_page_2))
        # fetch page 3 (coming from page 2)
        response = self._getTabRecently("first_event={0}".format(first_in_page_3))
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = int(pagination / 2))
        self.assertContains(response, '$("#link_show_previous_events").on("click", function() {{ refreshEvents(null, "{0}"); }});'
                                                                                                .format(last_in_page_2))
        self.assertContains(response, '$("#link_show_more_events").on("click", function() { refreshEvents(); });')

        # fetch page 2 (coming from page 3)
        response = self._getTabRecently("last_event={0}".format(last_in_page_2))
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = pagination)
        self.assertContains(response, '$("#link_show_previous_events").on("click", function() {{ refreshEvents(null, "{0}"); }});'
                                                                                                .format(last_in_page_1))
        self.assertContains(response, '$("#link_show_more_events").on("click", function() {{ refreshEvents("{0}"); }});'
                                                                                                .format(first_in_page_3))

        # fetch page 1 (coming from page 2), when new events have appeared: there are less than 'pagination' events
        #  of id greater than 'somewhere_in_page_1', but we should display the whole first page anyway and
        #  not take into account the last_event
        response = self._getTabRecently("last_event={0}".format(somewhere_in_page_1))
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = pagination)
        self.assertContains(response, '$("#link_show_previous_events").on("click", function() { refreshEvents(); });') # like the default
        self.assertContains(response, '$("#link_show_more_events").on("click", function() {{ refreshEvents("{0}"); }});'
                                                                                                .format(first_in_page_2)) # like the default

    def test_tab_recently_multiple_events_at_the_exact_same_time_are_all_displayed(self):
        # The event were identified with their timestamp, but when a lot of them had the same timestamp (ex: automatic
        #  hand submitting at the close of a game) it messed up the workflow of previous/more events links.
        pagination = views.EVENTS_PAGINATION
        last_date = utc.localize(datetime.datetime(2012, 01, 10, 23, 00, 00))
        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'ACCEPTED', creation_date = last_date + datetime.timedelta(minutes = -90),
                           finalizer = self.loginUser, closing_date = last_date,
                           initiator_offer = mommy.make(Offer),
                           responder_offer = mommy.make(Offer, creation_date = last_date + datetime.timedelta(minutes = -30)))
        msg_timestamp = last_date + datetime.timedelta(hours = -1)
        for i in range(pagination): # prepare 1 full page of messages, all at the same timestamp
            mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg', posting_date = msg_timestamp)
        self.game.start_date = last_date + datetime.timedelta(hours = -2)
        self.game.save()

        # total number of events : pagination + 1 game start + 3 events for the trade
        total_nb_of_events = pagination + 1 + 3

        # let's ask for page 2. one should see two messages, the create trade and the game start
        response = self._getTabRecently("first_event={0}".format(total_nb_of_events - pagination - 1))
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = 2)
        self.assertContains(response, 'proposed a <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade.id))
        self.assertContains(response, "Game #{0} has started".format(self.game.id))

        # from page 2, let's ask for page 1, one should see 2 events for the accepted trade (finalize and reply) and (pagination-2) messages
        response = self._getTabRecently("last_event={0}".format(total_nb_of_events - pagination))
        self.assertContains(response, 'accepted a <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade.id))
        self.assertContains(response, 'replied to your <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade.id))
        self.assertContains(response, "<div class=\"message_content\">my test msg</div>", count = pagination - 2)

    def test_tab_recently_messages_from_the_game_master_stand_out(self):
        msg = mommy.make(Message, game = self.game, sender = self.master, content = 'some message')

        response = self._getTabRecently()
        self.assertContains(response, "(<strong>game master</strong>)")
        self.assertContains(response, "<div class=\"message_content admin\">")

    def test_tab_recently_events_are_separated_by_date(self):
        pagination = views.EVENTS_PAGINATION
        now_date = now()
        for i in range(int(pagination + 1)): # ('pagination' + 1) messages today
            mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg', # id 3 to pagination + 3
                       posting_date = now_date + datetime.timedelta(seconds = -i))
        # add 1 message yesterday and 1 message the day before yesterday
        mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg', # id 2
                   posting_date = now_date + datetime.timedelta(days = -1))
        mommy.make(Message, game = self.game, sender = self.loginUser, content = 'my test msg', # id 1
                   posting_date = now_date + datetime.timedelta(days = -2))
        # + implicit event of id 0 : game start -- total: 12 events

        # 'today' should not be specified when it is the first item on the first page
        response = self._getTabRecently()
        self.assertNotContains(response, '<div class="event_date">')

        # on the second page, the days should be specified for 'today', 'yesterday' and the day before yesterday, duly formatted
        response = self._getTabRecently("first_event={0}".format(11 - pagination)) # second page starts at len(events) - pagination - 1, ie. 12 - pagination - 1
        self.assertContains(response, '<div class="event_date">Today</div>')
        self.assertContains(response, '<div class="event_date">Yesterday</div>')
        # BEWARE timezone hell : now_date and all aware date variables in this test are in UTC, but the display for the user
        #   will be in the get_default_timezone(). Thus in the case when the UTC date and its corresponding localtime are
        #   not in the same day (ex: 01/01 23:30:00+00:00 is actually 02/01 01:30:00+02:00 in France), the date formatting
        #   below MUST convert from a date that has been translated to localtime beforehand !
        #   (ie. the page will display 'Jan. 02' and not 'Jan. 01')
        self.assertContains(response, '<div class="event_date">{0}</div>'
                                      .format(date_format(localtime(now_date + datetime.timedelta(days = -2)))))

    def test_tab_recently_events_include_game_start_end_and_close(self):
        self.game.end_date = now() + datetime.timedelta(hours = -2)
        self.game.closing_date = now() + datetime.timedelta(hours = -1)
        self.game.save()
        response = self._getTabRecently()
        self.assertContains(response, 'Game #{0} has started.'.format(self.game.id))
        self.assertContains(response, 'Game #{0} has ended.'.format(self.game.id))
        self.assertContains(response, 'Game #{0} is over. Scores have been calculated.'.format(self.game.id))

        self.client.logout()
        self.assertTrue(self.client.login(username = self.master.username, password = 'test'))
        response = self._getTabRecently()
        self.assertContains(response, 'Game #{0} is over. Scores have been calculated.'.format(self.game.id))

    def test_tab_recently_event_for_game_start_when_it_has_not_started_yet(self):
        self.game.start_date = now() + datetime.timedelta(hours = 3, seconds = 2) # a few seconds because otherwise timeuntil would display '2 hours, 59 minutes'
        self.game.save()

        response = self._getTabRecently()
        self.assertContains(response, u'Game #{0} will start in 3\xa0hours.'.format(self.game.id))

    def test_tab_recently_events_include_own_trades(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'INITIATED', creation_date = now() + datetime.timedelta(hours = -1),
                            initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                            status = 'INITIATED',   creation_date = now() + datetime.timedelta(hours = -2),
                            initiator_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'INITIATED',  creation_date = now() + datetime.timedelta(hours = -3),
                            initiator_offer = mommy.make(Offer))
        trade4 = mommy.make(Trade, game = self.game, initiator = self.admin_player, responder = self.alternativeUser,
                            status = 'INITIATED',  creation_date = now() + datetime.timedelta(hours = -4),
                            initiator_offer = mommy.make(Offer)) # not displayed

        response = self._getTabRecently()
        self.assertContains(response, '<a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade1.id))
        self.assertContains(response, '<a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade2.id))
        self.assertContains(response, '<a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade3.id))
        self.assertNotContains(response, '<a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade4.id))

    def test_tab_recently_events_include_replying_offers_for_own_trades(self):
        dt_trade = now() + datetime.timedelta(hours = -5)
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'REPLIED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            responder_offer = mommy.make(Offer, creation_date = dt_trade + datetime.timedelta(minutes = 30)))
        dt_trade = now() + datetime.timedelta(hours = -3)
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'CANCELLED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            responder_offer = mommy.make(Offer, creation_date = dt_trade + datetime.timedelta(minutes = 30)),
                            finalizer = self.alternativeUser, closing_date = now())
        dt_trade = now() + datetime.timedelta(hours = -1)
        trade3 = mommy.make(Trade, game = self.game, initiator = self.admin_player, responder = self.alternativeUser,
                            status = 'REPLIED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            responder_offer = mommy.make(Offer, creation_date = dt_trade + datetime.timedelta(minutes = 30)))

        response = self._getTabRecently()
        self.assertContains(response, 'replied to your <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade1.id))
        self.assertContains(response, 'replied to your <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade2.id))
        self.assertNotContains(response, '<a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade3.id))

    def test_tab_recently_events_include_final_event_for_own_trades(self):
        dt_trade = now() + datetime.timedelta(hours = -5)
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'CANCELLED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            finalizer = self.loginUser, closing_date = now())
        dt_trade = now() + datetime.timedelta(hours = -3)
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'DECLINED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            responder_offer = mommy.make(Offer, creation_date = dt_trade + datetime.timedelta(minutes = 30)),
                            finalizer = self.loginUser, closing_date = now())
        dt_trade = now() + datetime.timedelta(hours = -1)
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'ACCEPTED', creation_date = dt_trade, initiator_offer = mommy.make(Offer, creation_date = dt_trade),
                            responder_offer = mommy.make(Offer, creation_date = dt_trade + datetime.timedelta(minutes = 30)),
                            finalizer = self.loginUser, closing_date = now())

        response = self._getTabRecently()
        self.assertContains(response, 'cancelled a <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade1.id))
        self.assertContains(response, 'declined a <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade2.id))
        self.assertContains(response, 'accepted a <a class="event_link_trade" data-trade-id="{0}">trade</a>'.format(trade3.id))

        self.assertEqual("False", response.get('full_refresh', "False"))

    def test_tab_recently_events_include_accepted_trade_from_other_players(self):
        # trade1 is ACCEPTED and between two players that are not the loginUser
        initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 2))
        initiator_offer_tc = mommy.make(TradedCommodities, nb_traded_cards = 1, commodityinhand = mommy.make(CommodityInHand), offer = initiator_offer)
        initiator_offer.tradedcommodities_set.add(initiator_offer_tc)
        responder_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 1))
        trade1 = mommy.make(Trade, game = self.game, initiator = self.admin_player, responder = self.alternativeUser,
                            status = 'ACCEPTED', initiator_offer = initiator_offer, responder_offer = responder_offer,
                            finalizer = self.admin_player, closing_date = now())
        # trade2 is between two players that are not the loginUser, but it is DECLINED : should not be displayed
        trade2 = mommy.make(Trade, game = self.game, initiator = self.admin_player, responder = self.alternativeUser,
                            status = 'DECLINED', finalizer = self.admin_player, closing_date = now(),
                            initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 2)),
                            responder_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 2)))
        # trade3 is ACCEPTED, but the loginUser is the trade's initiator : should not be displayed as an 'accept_trade' event
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'ACCEPTED', finalizer = self.loginUser, closing_date = now(),
                            initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 4)),
                            responder_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 4)))
        # trade4 is ACCEPTED and between other players, but belongs to another game
        trade3 = mommy.make(Trade, game = mommy.make(Game), initiator = self.admin_player, responder = self.alternativeUser,
                            status = 'ACCEPTED', finalizer = self.admin_player, closing_date = now(),
                            initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 5)),
                            responder_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 5)))

        response = self._getTabRecently()
        self.assertContains(response, 'A successful trade has been performed:', count = 1)
        self.assertContains(response, 'gave 3 cards')
        self.assertContains(response, 'gave 1 card')
        self.assertNotContains(response, 'gave 2 cards')
        self.assertNotContains(response, 'gave 4 cards')
        self.assertNotContains(response, 'gave 5 cards')

    def test_tab_recently_events_include_accepted_trades_but_no_pending_trades_for_game_master(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'INITIATED',
                            initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 2)))
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'ACCEPTED', finalizer = self.loginUser, closing_date = now(),
                            initiator_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 3)),
                            responder_offer = mommy.make(Offer, rules = mommy.make(RuleInHand, _quantity = 4)))

        self.login_as(self.master)

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(self.game.start_date, views.FORMAT_EVENT_PERMALINK))
        self.assertNotContains(response, 'gave 2 cards')
        self.assertContains(response, 'A successful trade has been performed:', count = 1)
        self.assertContains(response, 'gave 3 cards')
        self.assertContains(response, 'gave 4 card')

        self.assertEqual("True", response.get('full_refresh', "False")) # the accepted trade provokes a full refresh

    def test_tab_recently_the_last_event_for_a_pending_trade_stands_out(self):
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'INITIATED', initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'REPLIED', initiator_offer = mommy.make(Offer), responder_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'ACCEPTED', finalizer = self.loginUser, closing_date = now(),
                            initiator_offer = mommy.make(Offer), responder_offer = mommy.make(Offer))

        response = self._getTabRecently()
        self.assertNotContains(response, 'title="Please reply to this offer..."')
        self.assertContains(response, 'title="Please accept or decline..."', count = 1)

        self.login_as(self.alternativeUser)
        response = self._getTabRecently()
        self.assertContains(response, 'title="Please reply to this offer..."', count = 1)
        self.assertNotContains(response, 'title="Please accept or decline..."')

    def test_tab_recently_events_include_hand_submit(self):
        gp = GamePlayer.objects.get(game = self.game, player = self.alternativeUser)
        gp.submit_date = now()
        gp.save()

        response = self._getTabRecently()
        self.assertContains(response, 'The game master has received the cards submitted by')

    def test_tab_recently_events_are_dated_in_the_user_timezone(self):
        self.game.start_date = utc.localize(datetime.datetime(2013, 8, 14, 20, 12, 0))
        self.game.save()

        self.loginUser.timezone = "Asia/Hong_Kong" # UTC+8 no DST
        self.loginUser.save()

        response = self._getTabRecently()
        self.assertContains(response, 'Game #{0} has started.'.format(self.game.id))
        self.assertContains(response, '<div class="event_date">Aug. 15, 2013</div>')
        self.assertContains(response, '<div class="event_time">4:12 a.m.</div>')

    def test_tab_recently_refreshes_online_users(self):
        response = self._getTabRecently()
        # the loginUser is always identified as online since the middleware has been run by the time we get to the view func
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.has_header('online_players'))
        online_players = ast.literal_eval(response['online_players'])
        self.assertItemsEqual([self.loginUser.id], online_players)

        date_now = now()
        player5 = GamePlayer.objects.get(game=self.game, player__id=5)
        player5.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 20)
        player5.save()
        player6 = GamePlayer.objects.get(game=self.game, player__id=6)
        player6.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 10)
        player6.save()
        player7 = GamePlayer.objects.get(game=self.game, player__id=7)
        player7.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE - 10)
        player7.save()

        response = self._getTabRecently()
        # only the players who were last seen in less than SECONDS_BEFORE_OFFLINE seconds are identified as online
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.has_header('online_players'))
        online_players = ast.literal_eval(response['online_players'])
        self.assertItemsEqual([self.loginUser.id, 5, 6], online_players)

    def test_tab_recently_returns_only_the_online_users_if_nothing_has_changed(self):
        date_now = now()
        player5 = GamePlayer.objects.get(game=self.game, player__id=5)
        player5.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 20)
        player5.save()
        player6 = GamePlayer.objects.get(game=self.game, player__id=6)
        player6.last_seen = date_now + datetime.timedelta(seconds = -SECONDS_BEFORE_OFFLINE + 10)
        player6.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(self.game.start_date, views.FORMAT_EVENT_PERMALINK))
        self.assertEqual(204, response.status_code)
        self.assertTrue(response.has_header('online_players'))
        online_players = ast.literal_eval(response['online_players'])
        self.assertItemsEqual([self.loginUser.id, 5, 6], online_players)

    def test_tab_recently_post_a_message_works_and_redirect_as_a_GET_request(self):
        self.assertEqual(0, Message.objects.count())

        response = self._postMessage('test message represents')
        self.assertEqual(200, response.status_code)

        self.assertEqual(1, Message.objects.count())
        try:
            msg = Message.objects.get(game = self.game, sender = self.loginUser)
            self.assertEqual('test message represents', msg.content)
        except Message.DoesNotExist:
            self.fail("Message was not created for expected game and sender")

    def test_tab_recently_post_an_empty_message_does_nothing(self):
        # and no KeyError thrown
        try:
            response = self._postMessage('')
        except KeyError:
            self.fail("Posting an empty message shouldn't result in a KeyError")
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, Message.objects.count())

    def test_tab_recently_posting_a_message_fails_for_more_than_255_characters(self):
        response = self._postMessage('A'*300)
        self.assertContains(response, 'Ensure this value has at most 255 characters (it has 300).', status_code = 422)
        self.assertEqual(0, Message.objects.count())

    def test_tab_recently_message_with_markdown_are_interpreted(self):
        response = self._postMessage('Hi *this* is __a test__ and [a link](http://example.net/)')
        self.assertEqual(200, response.status_code)

        self.assertEqual('Hi <em>this</em> is <strong>a test</strong> and <a href=\"http://example.net/\">a link</a>',
                         Message.objects.get(game = self.game, sender = self.loginUser).content)

    def test_tab_recently_bleach_strips_unwanted_tags_and_attributes(self):
        response = self._postMessage( '<script>var i=3;</script>Hi an <em class="test">image</em><img src="http://blah.jpg"/>')
        self.assertEqual(200, response.status_code)

        self.assertEqual('var i=3;\n\nHi an <em>image</em>', Message.objects.get(game = self.game, sender = self.loginUser).content)

    def test_delete_message_forbidden_when_you_are_not_the_original_sender(self):
        msg = mommy.make(Message, game = self.game, sender = self.master)

        response = self._deleteMessage(msg)
        self.assertEqual(403, response.status_code)

    def test_delete_message_forbidden_when_not_in_POST(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser)

        response = self.client.get("/game/{0}/deletemessage/".format(self.game.id),
                                   {'event_id': msg.id},
                                   follow = True, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # simulate AJAX
        self.assertEqual(403, response.status_code)

    def test_delete_message_returns_404_when_the_message_doesnt_exists_in_database(self):
        response = self._deleteMessage(Message(id = 987654321))
        self.assertEqual(404, response.status_code)

    def test_delete_message_forbidden_when_grace_period_has_expired(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser,
                         posting_date = now() + datetime.timedelta(minutes = -(Message.GRACE_PERIOD + 20))) # 20 min after the end of the grace period

        response = self._deleteMessage(msg)
        self.assertEqual(403, response.status_code)

    def test_delete_message_works_for_the_sender_during_the_grace_period(self):
        msg = mommy.make(Message, game = self.game, sender = self.loginUser,
                         posting_date = now() + datetime.timedelta(minutes = -(Message.GRACE_PERIOD - 1))) # 1 min before the end of the grace period

        response = self._deleteMessage(msg)
        self.assertEqual(200, response.status_code)

        try:
            Message.objects.get(id = msg.id)
            self.fail("Message should have been deleted")
        except Message.DoesNotExist:
            pass

    def test_full_refresh_needed_for_the_players(self):
        # trade recently accepted by the other player
        date_now = now()
        trade = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                           initiator_offer = mommy.make(Offer), responder_offer = mommy.make(Offer),
                           finalizer = self.alternativeUser, status = 'ACCEPTED', closing_date = date_now)

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("True", response.get('full_refresh'))

        # trade recently cancelled by the other player
        trade.status = 'CANCELLED'
        trade.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("True", response.get('full_refresh'))

        # trade recently declined by the other player
        trade.status = 'DECLINED'
        trade.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("True", response.get('full_refresh'))

        # game already closed
        self.game.closing_date = date_now + datetime.timedelta(seconds = -60)
        self.game.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("False", response.get('full_refresh'))

        # first load
        self.game.closing_date = date_now + datetime.timedelta(seconds = 60)
        self.game.save()

        response = self._getTabRecently()
        self.assertEqual("False", response.get('full_refresh'))

    def test_full_refresh_needed_for_the_game_master(self):
        self.login_as(self.master)

        # trade recently accepted by a player
        date_now = now()
        trade = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                           initiator_offer = mommy.make(Offer), responder_offer = mommy.make(Offer),
                           finalizer = self.alternativeUser, status = 'ACCEPTED', closing_date = date_now)

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("True", response.get('full_refresh'))

        # trade recently declined by a player
        trade.status = 'DECLINED'
        trade.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("False", response.get('full_refresh'))

        # game already closed
        trade.status = 'ACCEPTED'
        trade.save()
        self.game.closing_date = date_now + datetime.timedelta(seconds = -60)
        self.game.save()

        response = self._getTabRecently("lastEventsRefreshDate=" + strftime(date_now + datetime.timedelta(seconds = -1), views.FORMAT_EVENT_PERMALINK))
        self.assertEqual("False", response.get('full_refresh'))

        # first load
        self.game.closing_date = date_now + datetime.timedelta(seconds = 60)
        self.game.save()

        response = self._getTabRecently()
        self.assertEqual("False", response.get('full_refresh'))

    def _getTabRecently(self, querystring = None):
        url = "/game/{0}/events".format(self.game.id)
        if querystring: url += "?" + querystring
        return self.client.get(url, follow = True, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # simulate AJAX

    def _postMessage(self, message):
        return self.client.post("/game/{0}/postmessage/".format(self.game.id),
                                {'message': message},
                                follow = True, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # simulate AJAX

    def _deleteMessage(self, message):
        return self.client.post("/game/{0}/deletemessage/".format(self.game.id),
                                {'event_id': message.id},
                                follow = True, HTTP_X_REQUESTED_WITH='XMLHttpRequest') # simulate AJAX

class SubmitHandTest(MystradeTestCase):

    def test_submit_hand_displays_the_commodities_the_known_rules_and_the_received_free_informations(self):
        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make(Commodity, name = 'c3', color = 'colC')

        mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                   nb_cards = 1, nb_submitted_cards = None)
        mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                   nb_cards = 2, nb_submitted_cards = None)
        mommy.make(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                   nb_cards = 3, nb_submitted_cards = None)

        hag08 = RuleCard.objects.get(ref_name = 'HAG08')
        hag09 = RuleCard.objects.get(ref_name = 'HAG09')
        hag10 = RuleCard.objects.get(ref_name = 'HAG10')

        rih1 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag08, abandon_date = None)
        rih2 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag09, abandon_date = None)
        rih3 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag09, abandon_date = now())
        rih4 = mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag10, abandon_date = now())

        mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                   initiator_offer = mommy.make(Offer), responder_offer = mommy.make(Offer, free_information = 'this is secret'),
                   finalizer = self.loginUser, status = 'ACCEPTED', closing_date = now())

        response = self._assertGetSubmitHandPage()

        self.assertContains(response, '<span class="commodity_card', count = 6)
        self.assertContains(response, 'data-commodity-id="{0}"'.format(commodity1.id), count = 1)
        self.assertContains(response, 'data-commodity-id="{0}"'.format(commodity2.id), count = 2)
        self.assertContains(response, 'data-commodity-id="{0}"'.format(commodity3.id), count = 3)

        self.assertContains(response, '<div class="rulecard"', count = 3)
        self.assertContains(response, 'data-public-name="8"', count = 1)
        self.assertContains(response, 'data-public-name="9"', count = 1)
        self.assertContains(response, 'data-public-name="10"', count = 1)

        self.assertContains(response, 'Free informations')
        self.assertContains(response, 'this is secret')

    def test_submit_hand_is_not_allowed_when_you_re_not_a_player_in_this_game(self):
        self.game.gameplayer_set.get(player = self.loginUser).delete() # make me not a player in this game
        self._assertGetSubmitHandPage(status_code = 403)

        self.login_as(self.admin)
        self._assertGetSubmitHandPage(status_code = 403)

        self.login_as(self.master)
        self._assertGetSubmitHandPage(status_code = 403)

    def test_submit_hand_is_not_allowed_if_it_has_already_been_submitted(self):
        gameplayer = self.game.gameplayer_set.get(player = self.loginUser)
        gameplayer.submit_date = now()
        gameplayer.save()

        self._assertGetSubmitHandPage(status_code = 403)

    def test_submit_hand_is_not_allowed_once_the_game_has_ended(self):
        self.game.end_date = now() + datetime.timedelta(hours = -2)
        self.game.save()

        self._assertGetSubmitHandPage(status_code = 403)

    def test_submit_hand_should_be_called_in_AJAX(self):
        response = self.client.get("/game/{0}/submithand/".format(self.game.id), follow = True)
        self.assertEqual(403, response.status_code)

    def test_submit_hand_save_submitted_commodities_and_submit_date(self):
        self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        commodity2 = mommy.make(Commodity, name = 'c2', color = 'colB')
        commodity3 = mommy.make(Commodity, name = 'c3', color = 'colC')

        mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                   nb_cards = 1, nb_submitted_cards = None)
        mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                   nb_cards = 2, nb_submitted_cards = None)
        mommy.make(CommodityInHand, commodity = commodity3, game = self.game, player = self.loginUser,
                   nb_cards = 3, nb_submitted_cards = None)

        response = self.client.post("/game/{0}/submithand/".format(self.game.id),
                                    {'commodity_{0}'.format(commodity1.id): 1,
                                     'commodity_{0}'.format(commodity2.id): 0,
                                     'commodity_{0}'.format(commodity3.id): 2},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(200, response.status_code)

        cih1 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity1)
        self.assertEqual(1, cih1.nb_submitted_cards)
        cih2 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity2)
        self.assertEqual(0, cih2.nb_submitted_cards)
        cih3 = CommodityInHand.objects.get(game = self.game, player = self.loginUser, commodity = commodity3)
        self.assertEqual(2, cih3.nb_submitted_cards)

        self.assertIsNotNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

    def test_submit_hand_cancels_or_declines_pending_trades(self):
        commodity1 = mommy.make(Commodity, name = 'c1', color = 'colA')
        mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                   nb_cards = 2, nb_submitted_cards = None)

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

        response = self.client.post("/game/{0}/submithand/".format(self.game.id),
                                    {'commodity_{0}'.format(commodity1.id): 1},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
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

    def _assertGetSubmitHandPage(self, status_code = 200):
        response = self.client.get("/game/{0}/submithand/".format(self.game.id), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(status_code, response.status_code)
        return response

class ControlBoardViewTest(MystradeTestCase):

    def setUp(self):
        super(ControlBoardViewTest, self).setUp()
        self.game_ended = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = -2))
        mommy.make(GamePlayer, game = self.game_ended, player = self.loginUser)
        self.game_closed = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = -2),
                                          closing_date = now() + datetime.timedelta(days = -1))
        mommy.make(GamePlayer, game = self.game_closed, player = self.loginUser)

    def test_game_board_shows_scores_to_game_master_and_admins_that_are_not_players_when_game_is_active(self):
        # logged as a simple player
        response = self._assertGetGamePage()
        self.assertNotContains(response, "Current Scores")

        # game master
        self.login_as(self.master)
        response = self._assertGetGamePage()
        self.assertContains(response, "Current Scores")

        # admin not player
        self.login_as(self.admin)
        response = self._assertGetGamePage()
        self.assertContains(response, "Current Scores")

        # admin but player in this game
        self.login_as(self.admin_player)
        response = self._assertGetGamePage()
        self.assertNotContains(response, "Current Scores")

    def test_game_board_shows_scores_for_players_and_game_master_and_admins_when_game_is_closed(self):
        # logged as a player
        response = self._assertGetGamePage(self.game_closed)
        self.assertContains(response, "Final Scores")

        # admin not player
        self.login_as(self.admin)
        response = self._assertGetGamePage(self.game_closed)
        self.assertContains(response, "Final Scores")

        # game master
        self.login_as(self.master)
        response = self._assertGetGamePage(self.game_closed)
        self.assertContains(response, "Final Scores")

    def test_control_board_shows_current_scoring_during_game_for_game_master(self):
        self._prepare_game_for_scoring(self.game)

        test6 = get_user_model().objects.get(username='test6')

        # a trap we shouldn't fall in, because the game is not closed
        mommy.make(ScoreFromCommodity, game = self.game, player = self.alternativeUser, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange'),
                       nb_submitted_cards = 3, nb_scored_cards = 3, actual_value = 4, score = 12)
        mommy.make(ScoreFromCommodity, game = self.game, player = test6, commodity = Commodity.objects.get(ruleset = 1, name = 'Orange'),
                       nb_submitted_cards = 1, nb_scored_cards = 1, actual_value = 4, score = 4)

        # rulecards
        mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = RuleCard.objects.get(ref_name = 'HAG04'))
        mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = RuleCard.objects.get(ref_name = 'HAG05'),
                   abandon_date = now())

        self.login_as(self.master)
        response = self._assertGetGamePage()

        scoresheets = response.context['scoresheets']
        self.assertEqual(9, len(scoresheets))
        self.assertEqual(test6, scoresheets[0].gameplayer.player)
        self.assertEqual(18, scoresheets[0].total_score)
        self.assertEqual(self.alternativeUser, scoresheets[1].gameplayer.player)
        self.assertEqual(17, scoresheets[1].total_score) # only two orange cards scored because of HAG05

        self.assertEqual('HAG04', scoresheets[1].known_rules[0].rulecard.ref_name)
        self.assertEqual('HAG05', scoresheets[1].known_rules[1].rulecard.ref_name)
        self.assertEqual(0, len(scoresheets[0].known_rules))

        self.assertContains(response, 'Grand Total: 18 points')
        self.assertContains(response, 'Grand Total: 17 points')
        self.assertContains(response, 'data-commodity-id="{0}"'.format(Commodity.objects.get(ruleset = 1, name = "Orange").id), count = 6) # 3 each
        self.assertContains(response, 'data-commodity-id="{0}"'.format(Commodity.objects.get(ruleset = 1, name = "Blue").id), count = 5) # 2 & 3
        self.assertContains(response, 'data-commodity-id="{0}"'.format(Commodity.objects.get(ruleset = 1, name = "White").id), count = 5) # 1 & 4
        self.assertContains(response, 'title="Orange -- not scored"', count = 1)
        self.assertContains(response, 'Since there are 4 white cards (more than three), their value is set to zero.', count = 1)
        self.assertContains(response, 'Since there are 2 blue card(s), only 2 orange card(s) score.', count = 1)

    def test_control_board_warns_when_the_current_scoring_contains_random_scores(self):
        self._prepare_game_for_scoring(self.game)

        self.game.rules.add(RuleCard.objects.get(ref_name = 'HAG15')) # rule that leads to random scores when a hand has > 13 commodity cards
        cih1red = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser,
                                 nb_cards = 10, commodity = Commodity.objects.get(ruleset = 1, name = 'Red'))

        self.login_as(self.master)
        response = self._assertGetGamePage()

        self.assertTrue(response.context['random_scoring']) # the whole game scoring is tagged
        for scoresheet in response.context['scoresheets']:
            if scoresheet.player_name == 'test5':
                self.assertTrue(getattr(scoresheet, 'is_random', False)) # the player's scoresheet is tagged
                random_rule = False
                for sfr in scoresheet.scores_from_rule:
                    if getattr(sfr, 'is_random', False) and sfr.rulecard.ref_name == 'HAG15':
                        random_rule = True
                self.assertTrue(random_rule) # the score_from_rule line than introduces the randomization is tagged

        self.assertContains(response, "These scores include at least one random element")
        self.assertContains(response, "this score includes random elements")
        self.assertContains(response, 'title="this rule introduces a random element"', count = 1)

    def test_close_game_allowed_only_to_game_master_and_admins_that_are_not_players(self):
        # simple player
        self._assertPostCloseGame(self.game_ended, 403)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNone(self.game_ended.closing_date)

        # game master
        self.game_ended.closing_date = None
        self.game_ended.save()
        self.login_as(self.master)
        self._assertPostCloseGame(self.game_ended)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNotNone(self.game_ended.closing_date)

        # admin not player
        self.game_ended.closing_date = None
        self.game_ended.save()
        self.login_as(self.admin)
        self._assertPostCloseGame(self.game_ended)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNotNone(self.game_ended.closing_date)

        # admin that is player
        self.game_ended.closing_date = None
        self.game_ended.save()
        mommy.make(GamePlayer, game = self.game_ended, player = get_user_model().objects.get(username = 'admin_player'))
        self.login_as(self.admin_player)
        self._assertPostCloseGame(self.game_ended, 403)
        self.game_ended = Game.objects.get(id = self.game_ended.id)
        self.assertIsNone(self.game_ended.closing_date)

    def test_close_game_not_allowed_in_GET(self):
        response = self.client.get("/game/{0}/close/".format(self.game_ended.id), HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')
        self.assertEqual(403, response.status_code)

    def test_close_game_should_be_called_in_AJAX(self):
        response = self.client.post("/game/{0}/close/".format(self.game_ended.id), follow = True)
        self.assertEqual(403, response.status_code)

    def test_close_game_allowed_only_on_games_ended_but_not_already_closed(self):
        self.login_as(self.master)

        game_not_ended = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = 2))
        self._assertPostCloseGame(game_not_ended, 403)

        game_closed = mommy.make(Game, master = self.master, end_date = now() + datetime.timedelta(days = -3),
                                 closing_date = now() + datetime.timedelta(days = -2))
        self._assertPostCloseGame(game_closed, 403)

        self._assertPostCloseGame(self.game_ended)

    def test_close_game_sets_the_game_closing_date(self):
        self.login_as(self.master)
        self.assertIsNone(self.game_ended.closing_date)

        self._assertPostCloseGame(self.game_ended)

        game = Game.objects.get(pk = self.game_ended.id)
        self.assertIsNotNone(game.closing_date)

    def test_close_game_aborts_all_pending_trades(self):
        trade1 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, status = 'INITIATED',
                            initiator_offer = mommy.make(Offer))
        trade2 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, status = 'REPLIED',
                            initiator_offer = mommy.make(Offer))
        trade3 = mommy.make(Trade, game = self.game_ended, initiator = self.alternativeUser, finalizer = self.alternativeUser,
                            status = 'CANCELLED', initiator_offer = mommy.make(Offer),
                            closing_date = utc.localize(datetime.datetime(2012, 11, 10, 18, 30)))

        self.login_as(self.master)
        self._assertPostCloseGame(self.game_ended)

        game = Game.objects.get(pk = self.game_ended.id)
        trade1 = Trade.objects.get(pk = trade1.id)
        trade2 = Trade.objects.get(pk = trade2.id)
        trade3 = Trade.objects.get(pk = trade3.id)

        self.assertEqual('CANCELLED', trade1.status)
        self.assertEqual(self.master, trade1.finalizer)
        self.assertEqual(game.closing_date, trade1.closing_date)

        self.assertEqual('CANCELLED', trade2.status)
        self.assertEqual(self.master, trade2.finalizer)
        self.assertIsNotNone(game.closing_date, trade2.closing_date)

        self.assertEqual(self.alternativeUser, trade3.finalizer)
        self.assertEqual(utc.localize(datetime.datetime(2012, 11, 10, 18, 30)), trade3.closing_date)

    def test_close_game_submits_the_commodity_cards_of_players_who_havent_manually_submitted(self):
        gp1 = mommy.make(GamePlayer, game = self.game_ended, player = self.alternativeUser)
        test6 = get_user_model().objects.get(username='test6')
        gp2_submit_date = now() + datetime.timedelta(days = -1)
        gp2 = mommy.make(GamePlayer, game = self.game_ended, player = test6, submit_date = gp2_submit_date)

        cih1 = mommy.make(CommodityInHand, game = self.game_ended, player = self.alternativeUser, nb_cards = 6, commodity__value = 1)
        cih2 = mommy.make(CommodityInHand, game = self.game_ended, player = test6, nb_cards = 4, nb_submitted_cards = 3, commodity__value = 1)

        self.login_as(self.master)
        self._assertPostCloseGame(self.game_ended)

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

        self.login_as(self.master)
        self._assertPostCloseGame(self.game_ended)

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
        self.assertEqual(6, len(mail.outbox))
        list_recipients = [msg.to[0] for msg in mail.outbox]

        self.assertEqual(1, list_recipients.count('test6@test.com'))
        emailTest6 = mail.outbox[list_recipients.index('test6@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test1'.format(self.game_ended.id), emailTest6.subject)
        self.assertIn('Test1 has closed game #{0}'.format(self.game_ended.id), emailTest6.body)
        self.assertIn('Congratulations, you are the winner !', emailTest6.body)
        self.assertIn('You scored 18 points, divided as:', emailTest6.body)
        self.assertIn('- 3 scored Orange cards x 4 = 12 points', emailTest6.body)
        self.assertIn('- 3 scored Blue cards x 2 = 6 points', emailTest6.body)
        self.assertIn('- 4 scored White cards x 0 = 0 points', emailTest6.body)
        self.assertIn('- Rule : (4) Since there are 4 white cards (more than three), their value is set to zero.', emailTest6.body)

        self.assertEqual(1, list_recipients.count('test5@test.com'))
        emailTest5 = mail.outbox[list_recipients.index('test5@test.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test1'.format(self.game_ended.id), emailTest5.subject)
        self.assertIn('Test1 has closed game #{0}'.format(self.game_ended.id), emailTest5.body)
        self.assertIn('Congratulations, you are in the second place !', emailTest5.body)
        self.assertIn('You scored 17 points, divided as:', emailTest5.body)
        self.assertIn('- 2 scored Orange cards x 4 = 8 points', emailTest5.body)
        self.assertIn('- 2 scored Blue cards x 2 = 4 points', emailTest5.body)
        self.assertIn('- 1 scored White card x 5 = 5 points', emailTest5.body)
        self.assertIn('- Rule : (5) Since there are 2 blue card(s), only 2 orange card(s) score.', emailTest5.body)

        self.assertEqual(1, list_recipients.count('test7@test.com'))
        emailTest7 = mail.outbox[list_recipients.index('test7@test.com')]
        self.assertIn('Congratulations, you are in the third place !', emailTest7.body)
        self.assertIn('You scored 6 points', emailTest7.body)

        self.assertEqual(1, list_recipients.count('test8@test.com'))
        emailTest8 = mail.outbox[list_recipients.index('test8@test.com')]
        self.assertIn('You\'re 4th of 5 players.', emailTest8.body)
        self.assertIn('You scored 4 points', emailTest8.body)

        self.assertEqual(1, list_recipients.count('test2@test.com'))
        emailTest2 = mail.outbox[list_recipients.index('test2@test.com')]
        self.assertIn('You\'re 5th of 5 players.', emailTest2.body)
        self.assertIn('You scored 0 points', emailTest2.body)

        self.assertEqual(1, list_recipients.count('admin@mystrade.com'))
        emailAdmin = mail.outbox[list_recipients.index('admin@mystrade.com')]
        self.assertEqual('[MysTrade] Game #{0} has been closed by test1'.format(self.game_ended.id), emailAdmin.subject)
        self.assertIn('Test1 has closed game #{0}'.format(self.game_ended.id), emailAdmin.body)
        self.assertIn('Final Scores:', emailAdmin.body)
        self.assertIn('1st. test6 : 18 points', emailAdmin.body)
        self.assertIn('2nd. test5 : 17 points', emailAdmin.body)
        self.assertIn('3rd. test7 : 6 points', emailAdmin.body)
        self.assertIn('4th. test8 : 4 points', emailAdmin.body)

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

    def _assertGetGamePage (self, game = None, status_code = 200):
        if game is None:
            game = self.game
        response = self.client.get("/game/{0}/".format(game.id), follow = True)
        self.assertEqual(status_code, response.status_code)
        return response

    def _assertPostCloseGame(self, game, status_code = 200):
        response = self.client.post("/game/{0}/close/".format(game.id), HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')
        self.assertEqual(status_code, response.status_code)

class TransactionalViewsTest(TransactionTestCase):
    fixtures = ['initial_data.json',
                'test_users.json', # from profile app
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

        mommy.make(CommodityInHand, commodity = commodity1, game = self.game, player = self.loginUser,
                   nb_cards = 1, nb_submitted_cards = None)
        mommy.make(CommodityInHand, commodity = commodity2, game = self.game, player = self.loginUser,
                   nb_cards = 2, nb_submitted_cards = None)

        # prepare a pending trade to abort, and make that abort() fail -- it will be the last step of the transaction
        mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                   status = 'INITIATED', initiator_offer = mommy.make(Offer), finalizer = None)

        def mock_abort(self, whodunit, closing_date):
            self.status = 'CANCELLED'
            self.finalizer = whodunit
            self.closing_date = closing_date
            self.save()
            raise RuntimeError
        old_abort = Trade.abort
        Trade.abort = mock_abort

        try:
            response = self.client.post("/game/{0}/submithand/".format(self.game.id),
                {'commodity_{0}'.format(commodity1.id): 1,
                 'commodity_{0}'.format(commodity2.id): 1 },
                HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

            self.assertEqual(422, response.status_code)

            self.assertIsNone(GamePlayer.objects.get(game = self.game, player = self.loginUser).submit_date)

            for commodity in CommodityInHand.objects.filter(game = self.game, player = self.loginUser):
                self.assertIsNone(commodity.nb_submitted_cards)

            trade = Trade.objects.get(game = self.game, initiator = self.loginUser)
            self.assertEqual('INITIATED', trade.status)
            self.assertIsNone(trade.finalizer)
            self.assertIsNone(trade.closing_date)
        finally:
            Trade.abort = old_abort

    def test_close_game_is_transactional(self):
        def mock_persist(self):
            mommy.make(ScoreFromCommodity, game = self.gameplayer.game, player = self.gameplayer.player)
            mommy.make(ScoreFromRule, game = self.gameplayer.game, player = self.gameplayer.player)
            raise RuntimeError
        old_persist = Scoresheet.persist
        Scoresheet.persist = mock_persist

        try:
            self.client.logout()
            self.assertTrue(self.client.login(username = self.master.username, password = 'test'))

            self.game.end_date = now() + datetime.timedelta(days = -1)
            self.game.save()

            cih = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser, commodity__value = 1, nb_cards = 1)

            trade = mommy.make(Trade, game = self.game, status = 'INITIATED', initiator = self.alternativeUser,
                                   responder = get_user_model().objects.get(username = 'test6'),
                                   initiator_offer = mommy.make(Offer), finalizer = None)

            response = self.client.post("/game/{0}/close/".format(self.game.id), HTTP_X_REQUESTED_WITH = 'XMLHttpRequest')

            self.assertEqual(422, response.status_code)

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
        finally:
            Scoresheet.persist = old_persist

class FormsTest(TestCase):
    fixtures = ['initial_data.json']

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
                                 utc.localize(datetime.datetime(2012, 11, 10, 18, 30)),
                                 utc.localize(datetime.datetime(2011, 11, 10, 18, 30)))
        self.assertRaisesMessage(ValidationError, 'End date must be strictly posterior to start date.',
                                 validate_dates,
                                 utc.localize(datetime.datetime(2012, 11, 10, 18, 30)),
                                 utc.localize(datetime.datetime(2012, 11, 10, 18, 30)))
        try:
            validate_dates(utc.localize(datetime.datetime(2012, 11, 10, 18, 30)), utc.localize(datetime.datetime(2012, 11, 10, 18, 50)))
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
        nb_rules_per_player = 4
        nb_commodities_per_player = 14

        ruleset = mommy.make(Ruleset, starting_rules = nb_rules_per_player, starting_commodities = nb_commodities_per_player)
        mommy.make(Commodity, ruleset = ruleset, _quantity = 10)
        game = mommy.make(Game, ruleset = ruleset, rules = self.rules, end_date = now() + datetime.timedelta(days = 7))
        for player in self.users:
            GamePlayer.objects.create(game = game, player = player)

        deal_cards(game)

        # check that each player has the requested number of cards
        for player in self.users:
            rules = RuleInHand.objects.filter(game = game, player = player)
            self.assertEqual(nb_rules_per_player, len(rules))
            for rule in rules:
                self.assertEqual(game.start_date, rule.ownership_date)
            commodities = CommodityInHand.objects.filter(game = game, player = player)
            nb_commodities = 0
            for commodity in commodities:
                nb_commodities += commodity.nb_cards
            self.assertEqual(nb_commodities_per_player, nb_commodities)

        # check that each card has the expected number of copies in play (and that the difference between the least frequent and the most frequent is no more than 1)
        min_occurence = nb_rules_per_player*len(self.users)/len(self.rules)
        for rule in self.rules:
            nb_cards = RuleInHand.objects.filter(game = game, rulecard = rule).count()
            self.assertTrue(min_occurence <= nb_cards <= min_occurence+1)
        min_occurence = nb_commodities_per_player *len(self.users)/10
        for commodity in Commodity.objects.filter(ruleset = ruleset):
            nb_cards = CommodityInHand.objects.filter(game = game, commodity = commodity).aggregate(Sum('nb_cards'))
            self.assertTrue(min_occurence <= nb_cards['nb_cards__sum'] <= min_occurence+1)

class HelpersTest(MystradeTestCase):

    def test_rules_currently_in_hand(self):
        rmx08 = RuleCard.objects.get(ref_name='RMX08')
        rmx09 = RuleCard.objects.get(ref_name='RMX09')
        rmx10 = RuleCard.objects.get(ref_name='RMX10')
        rmx11 = RuleCard.objects.get(ref_name='RMX11')
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rmx08, abandon_date = None)
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rmx09, abandon_date = None)
        mommy.make(RuleInHand, game = self.game, player = self.alternativeUser, rulecard = rmx10, abandon_date = None)
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = rmx11,
                          abandon_date = utc.localize(datetime.datetime(2013, 11, 1, 12, 0, 0)))

        rulesinhand = rules_in_hand(self.game, self.loginUser)

        self.assertEqual([rmx08, rmx09], [r.rulecard for r in rulesinhand])

    def test_rules_formerly_in_hand(self):
        hag05 = RuleCard.objects.get(ref_name='HAG05')
        hag06 = RuleCard.objects.get(ref_name='HAG06')
        hag07 = RuleCard.objects.get(ref_name='HAG07')
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag05,
                   abandon_date = utc.localize(datetime.datetime(2013, 11, 1, 12, 0, 0)))
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag06,
                   abandon_date = utc.localize(datetime.datetime(2013, 4, 4, 12, 0, 0)))
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag06,
                   abandon_date = utc.localize(datetime.datetime(2013, 4, 6, 14, 0, 0)))
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag07,
                   abandon_date = utc.localize(datetime.datetime(2013, 1, 8, 16, 0, 0)))

        rulesinhand = rules_formerly_in_hand(self.game, self.loginUser)

        self.assertEqual([hag05, hag06, hag06, hag07], [r.rulecard for r in rulesinhand])

    def test_known_rules(self):
        hag05 = RuleCard.objects.get(ref_name='HAG05')
        hag06 = RuleCard.objects.get(ref_name='HAG06')
        hag07 = RuleCard.objects.get(ref_name='HAG07')
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag05)
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag06)
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag06,
                   abandon_date = utc.localize(datetime.datetime(2013, 4, 6, 14, 0, 0)))
        mommy.make(RuleInHand, game = self.game, player = self.loginUser, rulecard = hag07,
                   abandon_date = utc.localize(datetime.datetime(2013, 1, 8, 16, 0, 0)))

        rules = known_rules(self.game, self.loginUser)

        self.assertEqual([hag05, hag06, hag07], [r.rulecard for r in rules])

    def test_commodities_in_hand(self):
        cih1 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser,
                          commodity = Commodity.objects.get(name = 'Yellow', ruleset__id = 1), nb_cards = 2)
        cih2 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser,
                          commodity = Commodity.objects.get(name = 'Orange', ruleset__id = 1), nb_cards = 1)
        cih3 = mommy.make(CommodityInHand, game = self.game, player = self.loginUser,
                          commodity = Commodity.objects.get(name = 'White', ruleset__id = 1), nb_cards = 0)
        cih4 = mommy.make(CommodityInHand, game = self.game, player = self.alternativeUser,
                          commodity = Commodity.objects.get(name = 'Red', ruleset__id = 1), nb_cards = 3)

        commodities = commodities_in_hand(self.game, self.loginUser)

        self.assertEqual([cih2, cih1], list(commodities))

    def test_free_informations_until_now(self):
        closing_date = now()

        offer1 = mommy.make(Offer, free_information = "info1")
        trade1 = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                            status = 'ACCEPTED', initiator_offer = mommy.make(Offer), responder_offer = offer1,
                            closing_date = closing_date)

        offer2 = mommy.make(Offer, free_information = "info2")
        trade1 = mommy.make(Trade, game = self.game, initiator = self.alternativeUser, responder = self.loginUser,
                            status = 'ACCEPTED', initiator_offer = offer2, responder_offer = mommy.make(Offer),
                            closing_date = closing_date)

        free_infos = free_informations_until_now(self.game, self.loginUser)

        self.assertEqual(2, len(free_infos))
        self.assertIn({'offerer': self.alternativeUser, 'date': closing_date, 'free_information': "info1"}, free_infos)
        self.assertIn({'offerer': self.alternativeUser, 'date': closing_date, 'free_information': "info2"}, free_infos)

class OnlineStatusMiddlewareTest(MystradeTestCase):

    def test_the_requests_related_to_a_specific_game_update_the_last_seen_timestamp(self):
        self.assertIsNone(self._get_last_seen())

        self.client.get(reverse("game_list"))
        self.assertIsNone(self._get_last_seen())

        self.client.get(reverse("otherprofile", args = [self.alternativeUser.id]))
        self.assertIsNone(self._get_last_seen())

        self.client.get(reverse("game", args = [self.game.id]))
        last_seen_game_board = self._get_last_seen()
        self.assertIsNotNone(last_seen_game_board)

        self.client.get(reverse("events", args = [self.game.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        last_seen_events = self._get_last_seen()
        self.assertIsNotNone(last_seen_events)
        self.assertNotEqual(last_seen_game_board, last_seen_events)

        trade = mommy.make(Trade, game = self.game, initiator = self.loginUser, responder = self.alternativeUser,
                           status = 'INITIATED', initiator_offer = mommy.make(Offer))
        self.client.get(reverse("cancel_trade", args = [self.game.id, trade.id]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        last_seen_cancel_trade = self._get_last_seen()
        self.assertIsNotNone(last_seen_cancel_trade)
        self.assertNotEqual(last_seen_events, last_seen_cancel_trade)

    def test_the_middleware_sets_a_first_visit_attribute_if_last_seen_was_null_for_this_game(self):
        response = self.client.get(reverse("game", args = [self.game.id]))
        self.assertTrue(response.context['display_foreword'])

        response = self.client.get(reverse("game", args = [self.game.id]))
        self.assertFalse(response.context['display_foreword'])

    def _get_last_seen(self):
        return GamePlayer.objects.get(game = self.game, player = self.loginUser).last_seen
