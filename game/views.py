import logging
import datetime

import bleach
from django.http import HttpResponse, Http404
import markdown
from django.conf import settings
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now, utc, make_naive

from game.deal import deal_cards
from game.forms import CreateGameForm, validate_number_of_players, validate_dates, MessageForm
from game.helpers import rules_in_hand, rules_formerly_in_hand, commodities_in_hand, known_rules, free_informations_until_now, _check_game_access_or_PermissionDenied
from game.models import Game, CommodityInHand, GamePlayer, Message
from ruleset.models import RuleCard, Ruleset
from scoring.card_scoring import tally_scores, Scoresheet
from scoring.models import ScoreFromCommodity, ScoreFromRule
from trade.forms import ERROR_EMPTY_OFFER
from trade.models import Trade
from profile.helpers import UserNameCache
from trade.views import _prepare_offer_form, _parse_offer_form, FormInvalidException
from utils import utils, stats

logger = logging.getLogger(__name__)

@login_required
def game_list(request):
    if request.resolver_match.url_name == 'nopath' and request.COOKIES.has_key(COOKIE_LAST_VISITED_GAME_KEY):
        try: # redirect to game board only if the game exists and the user has access rights
            game = Game.objects.get(id = request.COOKIES[COOKIE_LAST_VISITED_GAME_KEY])
            _check_game_access_or_PermissionDenied(game, request.user)
            return redirect(reverse('game', args = [request.COOKIES[COOKIE_LAST_VISITED_GAME_KEY]]))
        except (Game.DoesNotExist, PermissionDenied):
            pass

    games = Game.objects.filter(Q(master = request.user) | Q(players = request.user)).distinct().order_by('-closing_date', '-end_date')

    cache = UserNameCache()

    participations = dict([(gp.game_id, gp) for gp in GamePlayer.objects.filter(player = request.user)])

    for game in games:
        game.list_of_players = sorted([cache.get_name(player) for player in game.players.all()], key = lambda player: player.lower())

        if game.id in participations:
            game.hand_submitted = participations[game.id].submit_date is not None
        else:
            game.hand_submitted = False
    return render(request, 'game/game_list.html', {'games': games})


def rules(request, lang = 'en'):
    if lang in ['en', 'fr']:
        return render(request, 'rules/{0}.html'.format(lang))

    raise Http404

#############################################################################
##                            Game Board                                   ##
#############################################################################

SECONDS_BEFORE_OFFLINE = 10 * 60
COOKIE_LAST_VISITED_GAME_KEY = "mystrade-lastVisitedGame-id"
COOKIE_LAST_VISITED_GAME_DURATION = 7 * 24 * 60 * 60 # in seconds

@login_required
def game_board(request, game_id, trade_id = None):
    game = get_object_or_404(Game, id = game_id)

    players = sorted(game.players.all(), key = lambda player: player.name.lower())

    super_access = _check_game_access_or_PermissionDenied(game, request.user, players)

    verified_trade_id = None
    if trade_id:
        try:
            if super_access:
                verified_trade_id = Trade.objects.get(id = trade_id, game = game).id
            else:
                verified_trade_id = Trade.objects.get((Q(initiator = request.user) | Q(responder = request.user)), id = trade_id, game = game).id
        except Trade.DoesNotExist:
            pass

    context = {'game': game, 'players': players, 'online_players': _online_players(game, players),
               'message_form': MessageForm(), 'maxMessageLength': Message.MAX_LENGTH,
               'trade_id': verified_trade_id, 'events_refresh_delay': EVENTS_REFRESH_DELAY}

    if request.user in players and not game.is_closed():
        hand_submitted = request.user.gameplayer_set.get(game = game).submit_date is not None
        if hand_submitted:
            commodities = CommodityInHand.objects.filter(game = game, player = request.user, nb_submitted_cards__gt = 0).order_by('commodity__name')
            commodities_not_submitted = CommodityInHand.objects.filter(game = game, player = request.user,
                                                                       nb_cards__gt = F('nb_submitted_cards')).order_by('commodity__name')
            for cih in commodities:
                cih.nb_cards = cih.nb_submitted_cards # in 'commodities', feature only the submitted cards
            for cih in commodities_not_submitted:
                cih.nb_cards -= cih.nb_submitted_cards
        else:
            commodities = commodities_in_hand(game, request.user)
            commodities_not_submitted = CommodityInHand.objects.none()

        rulecards = rules_in_hand(game, request.user)
        former_rulecards = rules_formerly_in_hand(game, request.user)

        free_informations = free_informations_until_now(game, request.user)

        context.update({'commodities': commodities, 'rulecards': rulecards, 'former_rulecards': former_rulecards,
                        'hand_submitted': hand_submitted, 'commodities_not_submitted': commodities_not_submitted,
                        'free_informations': free_informations, 'show_control_board': False})
    else:
        # Scores for the game master and the admins that are NOT players in this game, and for the players after the game is closed
        scoresheets = None
        random_scoring = False # True if at least one line of score for one player can earn a different amount of points each time we calculate the score
        rank = -1

        if game.has_started():
            if game.is_closed():
                scoresheets = _fetch_scoresheets(game)
            else:
                scoresheets = tally_scores(game) # but don't persist them
                scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)

            # enrich scoresheets
            for index, scoresheet in enumerate(scoresheets, start = 1):
                player = scoresheet.gameplayer.player
                if game.is_closed() and request.user == player:
                    rank = index
                else:
                    if len([sfr for sfr in scoresheet.scores_from_rule if getattr(sfr, 'is_random', False)]) > 0:
                        scoresheet.is_random = True
                        random_scoring = True

                if request.user not in players or game.is_closed():
                    scoresheet.known_rules = known_rules(game, player)

        context.update({'show_control_board': True, 'super_access': super_access,
                        'scoresheets': scoresheets, 'random_scoring': random_scoring, 'rank': rank})

    response = render(request, 'game/board.html', context)

    _set_lastVisitedGame_cookie_if_needed(request, response, game)

    return response

def _fetch_scoresheets(game):
    scoresheets = []
    for gameplayer in GamePlayer.objects.filter(game=game):
        scoresheets.append(Scoresheet(gameplayer,
                                      ScoreFromCommodity.objects.filter(game=game, player=gameplayer.player).order_by('commodity'),
                                      ScoreFromRule.objects.filter(game=game, player=gameplayer.player).order_by('rulecard__step', 'rulecard__public_name')))
    scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)
    return scoresheets

def _online_players(game, players):
    list_of_online_players_id = []
    date_now = now()
    for player in players:
        last_seen = player.gameplayer_set.get(game = game).last_seen
        if last_seen and date_now - last_seen <= datetime.timedelta(seconds = SECONDS_BEFORE_OFFLINE):
            list_of_online_players_id.append(str(player.id) )

    return "[" + ", ".join(list_of_online_players_id) + "]"

def _set_lastVisitedGame_cookie_if_needed(request, response, game):
    if game.has_started() and not game.is_closed():
        response.set_cookie(COOKIE_LAST_VISITED_GAME_KEY, game.id, max_age = COOKIE_LAST_VISITED_GAME_DURATION)
    elif game.is_closed():
        if request.COOKIES.has_key(COOKIE_LAST_VISITED_GAME_KEY) and request.COOKIES[COOKIE_LAST_VISITED_GAME_KEY] == str(game.id):
            response.delete_cookie(COOKIE_LAST_VISITED_GAME_KEY)

#############################################################################
##                      Events (Tab "Recently")                            ##
#############################################################################
EVENTS_PAGINATION = 8
EVENTS_REFRESH_DELAY = 3 * 60 * 1000 # ms
# EVENTS_REFRESH_DELAY = 5 * 1000 # ms # for tests
FORMAT_EVENT_PERMALINK = "%Y-%m-%dT%H:%M:%S.%f"

class Event(object):
    def __init__(self, event_type, date, sender, trade = None):
        self.event_type = event_type
        self.date = date
        self.sender = sender
        self.deletable = False
        self.trade = trade # only for trade-related events

    def has_happened(self):
        return self.date <= now()

# noinspection PyTypeChecker
@login_required
def events(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    _check_game_access_or_PermissionDenied(game, request.user)

    if request.is_ajax():
        # Make a list of all events to display
        events = list(Message.objects.filter(game = game))

        events.append(Event('game_start', game.start_date, game.master))
        if game.has_ended():
            events.append(Event('game_end', game.end_date, game.master))
            if game.is_closed():
                events.append(Event('game_close', game.closing_date, game.master))

        for trade in Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game):
            events.append(Event('create_trade', trade.creation_date, trade.initiator, trade))
            if trade.responder_offer:
                events.append(Event('reply_trade', trade.responder_offer.creation_date, trade.responder, trade))
            if trade.finalizer:
                events.append(Event('finalize_trade', trade.closing_date, trade.finalizer, trade))

        for trade in Trade.objects.filter(game = game, status = 'ACCEPTED').exclude(initiator = request.user).exclude(responder = request.user):
            events.append(Event('accept_trade', trade.closing_date, trade.initiator, trade))

        for gameplayer in game.gameplayer_set.filter(submit_date__isnull = False):
            events.append(Event('submit_hand', gameplayer.submit_date, gameplayer.player))

        # The events are sorted by chronological order, and all manipulation will be done in this order.
        # Only once the subset of events to display is selected will the list be reversed to show them in inverse chronological order.

        # sort by date, then by user's name for events with the same date
        events.sort(key = lambda evt: evt.sender.name) # secondary key first
        events.sort(key = lambda evt: evt.date) # primary key at the end

        # Display only a page of events
        if request.GET.get('last_event'):
            page_requested = True
            last_event_to_display = int(request.GET.get('last_event'))
            events_in_the_range = events[last_event_to_display:]
            if len(events_in_the_range) >= EVENTS_PAGINATION:
                displayed_events = events_in_the_range[:EVENTS_PAGINATION] # take the *first* EVENTS_PAGINATION events
            else: # if there are less than EVENTS_PAGINATION events to display, a full page is displayed anyway
                displayed_events = events[-EVENTS_PAGINATION:]
        elif request.GET.get('first_event'):
            page_requested = True
            first_event_to_display = int(request.GET.get('first_event'))
            events_in_the_range = events[:first_event_to_display + 1]
            displayed_events = events_in_the_range[-EVENTS_PAGINATION:] # take the *last* EVENTS_PAGINATION events
        else:
            page_requested = False
            events_in_the_range = events
            displayed_events = events_in_the_range[-EVENTS_PAGINATION:] # take the *last* EVENTS_PAGINATION events

        # define the ids (excluded) of the starting/last event to be displayed in next/previous page
        if len(displayed_events) > 0 and events.index(displayed_events[-1]) < len(events) - 1: # there are later events, to be displayed in the previous pages
            last_event = events.index(displayed_events[-1]) + 1
        else:
            last_event = None

        if len(displayed_events) > 0 and events.index(displayed_events[0]) > 0: # there were earlier events, to be displayed in the next pages
            first_event = events.index(displayed_events[0]) - 1
        else:
            first_event = None

        # is it the first fetch of the events since the game board has loaded? -- otherwise it's a later periodic refresh
        first_load = 'lastEventsRefreshDate' not in request.GET

        new_events = []
        if not first_load:
            lastEventsRefreshDate = datetime.datetime.strptime(request.GET.get('lastEventsRefreshDate'), FORMAT_EVENT_PERMALINK)
            for event in displayed_events:
                if make_naive(event.date, utc) > lastEventsRefreshDate:
                    event.highlight = True
                    new_events.append(event)

        # HERE we eventually reverse the list to display events in inverse chronological order
        displayed_events.reverse()

        if first_load or page_requested or new_events:
            response = render(request, 'game/events.html',
                          {'game': game, 'events': displayed_events, 'first_event': first_event, 'last_event': last_event,
                           'lastEventsRefreshDate': datetime.datetime.strftime(now(), FORMAT_EVENT_PERMALINK)})
        else:
            response = HttpResponse(status = 204) # 204 = No Content

        response['full_refresh'] = _full_refresh_needed(game, first_load, new_events, request.user)
        response['online_players'] = _online_players(game, game.players.all())
        return response

    raise PermissionDenied

def _full_refresh_needed(game, first_load, new_events, me):
    """ For a player, let's ask for an immediate refresh of the whole game board if:
         - it's not the first display of recent events after loading the game board;
         - and among the new events, there is at least one trade finalized by the other player
           (because if ACCEPTED it will modify the hand and/or free informations of the current player,
            and if CANCELLED or DECLINED it will free the card from their pending trade)

        For the game master watching the score board, the criteria are:
         - it's not the first display of recent events after loading the game board;
         - there is at least an ACCEPTED trade in the new events (since the scores may have been modified by this trade).
    """
    if not first_load and not game.is_closed():
        if me in game.players.all():
            for event in new_events:
                if event.event_type == 'finalize_trade' and event.trade.finalizer != me:
                    return "True"
        else: # game master and admins
            for event in new_events:
                if event.event_type == 'accept_trade':
                    return "True"
    return "False"

#############################################################################
##                          Public Messages                                ##
#############################################################################

@login_required
def post_message(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    _check_game_access_or_PermissionDenied(game, request.user)

    if request.is_ajax() and request.method == 'POST':
        message_form = MessageForm(data = request.POST)
        if message_form.is_valid():
            if len(message_form.cleaned_data['message']) > 0:
                # bleach allowed tags : 'a','abbr','acronym','b','blockquote','code','em','i','li','ol','strong', 'ul'
                secure_message = bleach.clean(markdown.markdown(message_form.cleaned_data['message']), strip = True)
                Message.objects.create(game = game, sender = request.user, content = secure_message)
            return HttpResponse()
        else:
            return HttpResponse(message_form.errors['message'], status = 422)

    raise PermissionDenied

@login_required
def delete_message(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.is_ajax() and request.method == 'POST':
        message = get_object_or_404(Message, game = game, id = request.POST['event_id'])

        if message.sender == request.user and message.deletable:
            message.delete()
            return HttpResponse()

    raise PermissionDenied

#############################################################################
##                            Submit Hand                                  ##
#############################################################################

@login_required
def submit_hand(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if request.user not in game.players.all() or game.has_ended() or not request.is_ajax():
        raise PermissionDenied

    # one can submit one own's hand only once
    if game.gameplayer_set.get(player = request.user).submit_date:
        raise PermissionDenied

    if request.method == 'POST':
        try:
            offer, selected_commodities, selected_rulecards = _parse_offer_form(request, game)
            with transaction.commit_on_success():
                gameplayer = GamePlayer.objects.get(game = game, player = request.user)
                gameplayer.submit_date = now()
                gameplayer.save()

                for commodity, nb_selected_cards in selected_commodities.iteritems():
                    commodity.nb_submitted_cards = nb_selected_cards
                    commodity.save()

                # abort pending trades
                for trade in Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game, finalizer__isnull = True):
                    trade.abort(request.user, gameplayer.submit_date)

                return HttpResponse()
        except FormInvalidException as ex:
            if ERROR_EMPTY_OFFER in ex.formdata['offer_errors']:
                message = "At least one commodity card should be offered."
            else:
                message = "Internal error. Please try again."
                logger.error("Error in submit_hand({0})".format(game_id), exc_info = ex)

            return HttpResponse(message, status = 422)
        except BaseException as ex:
            logger.error("Error in submit_hand({0})".format(game_id), exc_info = ex)
            return HttpResponse("Internal error. Please try again.", status = 422)
    else:
        commodities = commodities_in_hand(game, request.user)
        rulecards = known_rules(game, request.user)

        free_informations = free_informations_until_now(game, request.user)

        offer_form = _prepare_offer_form(request, game,
                                         # all commodities in hand are selected initially
                                         selected_commodities = dict([(cih, cih.nb_cards) for cih in commodities]))

        return render(request, 'game/submit_hand.html',
                      {'game': game, 'commodities': commodities, 'rulecards': rulecards,
                       'free_informations': free_informations, 'offer_form': offer_form})

#############################################################################
##                           Create Game                                   ##
#############################################################################
MIN_COPIES_OF_EACH_RULECARD = 2

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            request.session['ruleset'] = form.cleaned_data['ruleset']
            request.session['start_date'] = form.cleaned_data['start_date'].astimezone(utc)
            request.session['end_date'] = form.cleaned_data['end_date'].astimezone(utc)
            request.session['players'] = sorted(form.cleaned_data['players'].all(), key = lambda player: player.name) # convert from Queryset to list
            return redirect('select_rules')
    else:
        form = CreateGameForm(request.user)
    return render(request, 'game/create.html', {'form': form, 'rulesets': Ruleset.objects.all()})

@permission_required('game.add_game')
def select_rules(request):
    if 'ruleset' not in request.session or 'start_date' not in request.session\
       or 'end_date' not in request.session or 'players' not in request.session:
        return redirect('create_game')

    ruleset = request.session['ruleset']
    start_date = request.session['start_date']
    end_date = request.session['end_date']
    players = request.session['players']

    try:
        validate_dates(start_date, end_date)
        validate_number_of_players(players, ruleset)
    except ValidationError:
        return redirect('create_game')

    rulecards = RuleCard.objects.filter(ruleset = ruleset).order_by('ref_name')

    # We'll have           (A) nb_max_rulecards * MIN_COPIES_OF_EACH_RULECARD     cards in play on one hand,
    #  and we will have    (B) len(players) * starting_rules                      cards dealt at the beginning on the other hand.
    # Those two numbers should be the same, but if it's not possible, the second one must be higher: (A) <= (B).
    # Which gives:         nb_max_rulecards <= len(players) * starting_rules / MIN_COPIES_OF_EACH_RULECARD
    nb_max_rulecards = int(len(players) * float(ruleset.starting_rules) / MIN_COPIES_OF_EACH_RULECARD)

    if request.method == 'POST':
        selected_rules = []
        for rulecard in rulecards:
            if rulecard.mandatory:
                selected_rules.append(rulecard)
                continue
            key = "rulecard_{0}".format(rulecard.id)
            if key in request.POST and request.POST[key] == "True":
                selected_rules.append(rulecard)
                rulecard.selected = True

        if len(selected_rules) > nb_max_rulecards:
            error = "Please select at most {0} rule cards (including the mandatory ones)".format(nb_max_rulecards)
            return render(request, 'game/select_rules.html', {'rulecards': rulecards, 'session': request.session,
                                                              'nb_max_rulecards': nb_max_rulecards, 'error': error})

        game = Game.objects.create(ruleset    = ruleset,
                                   master     = request.user,
                                   start_date = start_date,
                                   end_date   = end_date)
        for player in players:
            GamePlayer.objects.create(game = game, player = player)
        for rule in selected_rules:
            game.rules.add(rule)
        del request.session['ruleset']
        del request.session['start_date']
        del request.session['end_date']
        del request.session['players']

        # deal starting cards
        deal_cards(game)

        # record score stats at the game creation
        stats.record(game)

        # email notification
        all_players = {}
        for player in game.players.all():
             all_players[player] = {'name': player.name,
                                    'url': request.build_absolute_uri(reverse('otherprofile', args=[player.id]))}

        for player in all_players.iterkeys():
             opponents = dict(all_players) # make a copy
             del opponents[player]
             list_opponents = sorted(opponents.itervalues(), key = lambda opponent: opponent['name'])
             rules = rules_in_hand(game, player)
             commodities = commodities_in_hand(game, player)
             utils.send_notification_email('game_create', player,
                                           {'game': game, 'opponents': list_opponents, 'rules': rules, 'commodities': commodities,
                                            'player_timezone': player.timezone,
                                            'url': request.build_absolute_uri(reverse('game', args=[game.id]))})

        # email notification for the admins
        utils.send_notification_email('game_create_admin', [admin[1] for admin in settings.ADMINS],
                                       {'game': game, 'players': sorted(all_players.itervalues(), key = lambda player: player['name']),
                                        'rules': selected_rules})

        return redirect('game', game.id)
    else:
        return render(request, 'game/select_rules.html', {'rulecards': rulecards, 'session': request.session,
                                                          'nb_max_rulecards': nb_max_rulecards})

#############################################################################
##                            Close Game                                   ##
#############################################################################
@login_required
def close_game(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.is_ajax() and request.method == 'POST' and game.has_super_access(request.user):
        if game.end_date <= now() and game.closing_date is None :
            try:
                with transaction.commit_on_success():
                    game.closing_date = now()
                    game.save()

                    # abort pending trades
                    for trade in Trade.objects.filter(game = game, finalizer__isnull = True):
                        trade.abort(request.user, game.closing_date)

                    # automatically submit all commodity cards of players who haven't manually submitted their hand
                    for gameplayer in GamePlayer.objects.filter(game = game, submit_date__isnull = True):
                        for cih in commodities_in_hand(game, gameplayer.player):
                            cih.nb_submitted_cards = cih.nb_cards
                            cih.save()
                        gameplayer.submit_date = game.closing_date
                        gameplayer.save()

                    # calculate and save scores
                    scoresheets = tally_scores(game)
                    for scoresheet in scoresheets:
                        scoresheet.persist()

                    # record score stats when game is closed
                    stats.record(game, scoresheets = scoresheets)

                    # email notification
                    scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)
                    for rank, scoresheet in enumerate(scoresheets, 1):
                        utils.send_notification_email('game_close', scoresheet.gameplayer.player,
                                                      {'game': game, 'rank': rank, 'nb_players': len(scoresheets), 'scoresheet': scoresheet,
                                                       'player_timezone': scoresheet.gameplayer.player.timezone,
                                                       'url': request.build_absolute_uri(reverse('game', args = [game.id]))})

                    # email notification for the admins
                    utils.send_notification_email('game_close_admin', [admin[1] for admin in settings.ADMINS],
                                                  {'game': game, 'scoresheets': scoresheets,
                                                   'url': request.build_absolute_uri(reverse('game', args = [game.id]))})
            except BaseException as ex:
                logger.error("Error in close_game({0})".format(game_id), exc_info = ex)
                return HttpResponse(status = 422)

            return HttpResponse()

    raise PermissionDenied