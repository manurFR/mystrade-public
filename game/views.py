import logging
import datetime

import bleach
from django.http import HttpResponse
import markdown
from django.conf import settings
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q, F
from django.forms.formsets import formset_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now, utc, make_naive

from game.deal import deal_cards
from game.forms import CreateGameForm, validate_number_of_players, validate_dates, MessageForm
from game.helpers import rules_currently_in_hand, rules_formerly_in_hand, commodities_in_hand, known_rules, free_informations_until_now
from game.models import Game, CommodityInHand, GamePlayer, Message
from ruleset.models import RuleCard, Ruleset
from scoring.card_scoring import tally_scores, Scoresheet
from scoring.models import ScoreFromCommodity, ScoreFromRule
from trade.forms import RuleCardFormParse, RuleCardFormDisplay, ERROR_EMPTY_OFFER
from trade.models import Trade
from profile.helpers import UserNameCache
from trade.views import _prepare_offer_form, _parse_offer_form, FormInvalidException
from utils import utils, stats


logger = logging.getLogger(__name__)

@login_required
def welcome(request):
    games = Game.objects.filter(Q(master=request.user) | Q(players=request.user)).distinct().order_by('-closing_date', '-end_date')

    cache = UserNameCache()

    participations = dict([(gp.game_id, gp) for gp in GamePlayer.objects.filter(player = request.user)])

    for game in games:
        game.list_of_players = sorted([cache.get_name(player) for player in game.players.all()], key = lambda player: player.lower())

        if game.id in participations:
            game.hand_submitted = participations[game.id].submit_date is not None
        else:
            game.hand_submitted = False
    return render(request, 'game/welcome.html', {'games': games})

#############################################################################
##                            Game Views                                   ##
#############################################################################
EVENTS_PAGINATION = 8

@login_required
def game(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    players = sorted(game.players.all(), key = lambda player: player.name.lower())

    if request.user not in players and not game.has_super_access(request.user):
        raise PermissionDenied

    # parse message post
    if request.method == 'POST':
        message_form = MessageForm(data = request.POST)
        if message_form.is_valid() and len(message_form.cleaned_data['message']) > 0:
        # bleach allowed tags : 'a','abbr','acronym','b','blockquote','code','em','i','li','ol','strong', 'ul'
            secure_message = bleach.clean(markdown.markdown(message_form.cleaned_data['message']), strip = True)
            Message.objects.create(game = game, sender = request.user, content = secure_message)
            return redirect('game', game_id) # call again the same view method but in GET, so that a refresh doesn't re-post the message
            # else keep the bound message_form to display the erroneous message
    else:
        message_form = MessageForm()

    # game elements
    context =  {'game': game, 'players': players, 'message_form': message_form,  'maxMessageLength': Message.MAX_LENGTH}

    if request.user in players:
        rules = rules_currently_in_hand(game, request.user)

        commodities = list(commodities_in_hand(game, request.user))
        hand_submitted = request.user.gameplayer_set.get(game = game).submit_date is not None
        if hand_submitted:
            for cih in commodities:
                if cih.nb_submitted_cards == 0:
                    commodities.remove(cih)
                else:
                    cih.nb_cards = cih.nb_submitted_cards

        nb_commodities = sum([cih.nb_cards for cih in commodities])

        pending_trades = Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game,
                                              status__in = ['INITIATED', 'REPLIED']).order_by('-creation_date')

        context.update({'rules': rules, 'commodities': commodities, 'nb_commodities': nb_commodities,
                        'pending_trades': pending_trades, 'hand_submitted': hand_submitted})

    # display messages
    messages = Message.objects.filter(game = game).order_by('-posting_date')
    paginator = Paginator(messages, per_page = EVENTS_PAGINATION, orphans = 3)
    page = request.GET.get('page')
    try:
        displayed_messages = paginator.page(page)
    except PageNotAnInteger:
        displayed_messages = paginator.page(1) # If page is not an integer, deliver first page.
    except EmptyPage:
        displayed_messages = paginator.page(paginator.num_pages) # If page is out of range, deliver last page of results.

    context.update({'messages': displayed_messages})

    return render(request, 'game/game.html', context)

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

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            request.session['ruleset'] = form.cleaned_data['ruleset']
            request.session['start_date'] = form.cleaned_data['start_date']
            request.session['end_date'] = form.cleaned_data['end_date']
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

    rulecards_queryset = RuleCard.objects.filter(ruleset=ruleset).order_by('ref_name')

    error = None
    if request.method == 'POST':
        RuleCardsFormSet = formset_factory(RuleCardFormParse)
        formset = RuleCardsFormSet(request.POST)
        if formset.is_valid():
            selected_rules = []
            for card in rulecards_queryset:
                if card.mandatory:
                    selected_rules.append(card)
                    continue
                for form in formset:
                    if form.cleaned_data['card_id'] == card.id and form.cleaned_data['selected_rule']:
                        selected_rules.append(card)
                        break
            if len(selected_rules) > len(players):
                error = "Please select at most {0} rule cards (including the mandatory ones)".format(len(players))
                RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
                formset = RuleCardsFormSet(initial=[{'card_id': card.id,
                                                     'public_name': card.public_name,
                                                     'description': card.description,
                                                     'mandatory': bool(card.mandatory),
                                                     'selected_rule': bool(card in selected_rules)}
                                                    for card in rulecards_queryset])
                return render(request, 'game/select_rules.html', {'formset': formset, 'session': request.session, 'error': error})
            else:
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

                if game.is_active():
                     url = request.build_absolute_uri(reverse('trades', args = [game.id]))
                else: # game not yet started
                     url = request.build_absolute_uri(reverse('hand', args = [game.id]))

                for player in all_players.iterkeys():
                     opponents = dict(all_players) # make a copy
                     del opponents[player]
                     list_opponents = sorted(opponents.itervalues(), key = lambda opponent: opponent['name'])
                     rules = rules_currently_in_hand(game, player)
                     commodities = commodities_in_hand(game, player)
                     utils.send_notification_email('game_create', player,
                                                   {'game': game, 'opponents': list_opponents, 'rules': rules, 'commodities': commodities, 'url': url})

                # email notification for the admins
                utils.send_notification_email('game_create_admin', [admin[1] for admin in settings.ADMINS],
                                               {'game': game, 'players': sorted(all_players.itervalues(), key = lambda player: player['name']),
                                                'rules': selected_rules})

                return redirect('game', game.id)
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra=0)
        formset = RuleCardsFormSet(initial=[{'card_id': card.id,
                                             'public_name': card.public_name,
                                             'description': card.description,
                                             'mandatory': bool(card.mandatory)}
                                            for card in rulecards_queryset])
        return render(request, 'game/select_rules.html', {'formset': formset, 'session': request.session})

#############################################################################
##                          Control Board                                  ##
#############################################################################
def _fetch_scoresheets(game):
    scoresheets = []
    for gameplayer in GamePlayer.objects.filter(game=game):
        scoresheets.append(Scoresheet(gameplayer,
                                      ScoreFromCommodity.objects.filter(game=game, player=gameplayer.player).order_by('commodity'),
                                      ScoreFromRule.objects.filter(game=game, player=gameplayer.player).order_by('rulecard__step', 'rulecard__public_name')))
    scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)
    return scoresheets

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

#############################################################################
##                              Redesign                                   ##
#############################################################################
@login_required
def game_board(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    players = sorted(game.players.all(), key = lambda player: player.name.lower())

    super_access = game.has_super_access(request.user)
    if request.user not in players and not super_access:
        raise PermissionDenied

    context = {'game': game, 'players': players, 'message_form': MessageForm(), 'maxMessageLength': Message.MAX_LENGTH}

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

        rulecards = rules_currently_in_hand(game, request.user)
        former_rulecards = rules_formerly_in_hand(game, request.user, current_rulecards = [r.rulecard for r in rulecards])

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

    return render(request, 'game/board.html', context)

class Event(object):
    def __init__(self, event_type, date, sender, trade = None):
        self.event_type = event_type
        self.date = date
        self.sender = sender
        self.deletable = False
        self.trade = trade # only for trade-related events

FORMAT_EVENT_PERMALINK = "%Y-%m-%dT%H:%M:%S.%f"

# noinspection PyTypeChecker
@login_required
def events(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all() and not game.has_super_access(request.user):
        raise PermissionDenied

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

        events.sort(key = lambda evt: evt.date, reverse=True)

        # Pagination by the date of the first or last event displayed
        if request.GET.get('dateprevious'):
            start_date = datetime.datetime.strptime(request.GET.get('dateprevious'), FORMAT_EVENT_PERMALINK)
            events_in_the_range = _events_in_the_range(events, start_date=start_date)
            if len(events_in_the_range) >= EVENTS_PAGINATION:
                displayed_events = events_in_the_range[-EVENTS_PAGINATION:] # take the *last* EVENTS_PAGINATION events
            else: # if there are less than EVENTS_PAGINATION events after start_date, it's the beginning of the list and we take as much events as we can
                displayed_events = events[:EVENTS_PAGINATION]
        else:
            if request.GET.get('datenext'):
                end_date = datetime.datetime.strptime(request.GET.get('datenext'), FORMAT_EVENT_PERMALINK)
            else:
                end_date = None
            displayed_events = _events_in_the_range(events, end_date = end_date)[:EVENTS_PAGINATION] # take the *first* EVENTS_PAGINATION events

        if len(displayed_events) > 0 and events.index(displayed_events[0]) > 0: # events later
            dateprevious = datetime.datetime.strftime(displayed_events[0].date, FORMAT_EVENT_PERMALINK)
        else:
            dateprevious = None

        if len(displayed_events) > 0 and displayed_events[-1].date > events[-1].date: # events earlier
            datenext = datetime.datetime.strftime(displayed_events[-1].date, FORMAT_EVENT_PERMALINK)
        else:
            datenext = None

        return render(request, 'game/events.html',
                      {'game': game, 'events': displayed_events, 'datenext': datenext, 'dateprevious': dateprevious})

    raise PermissionDenied

def _events_in_the_range(events, start_date = None, end_date = None):
    if start_date is None:
        start_date = datetime.datetime.min
    if end_date is None:
        end_date = datetime.datetime.max

    start_index = None
    range = []
    for index, evt in enumerate(events):
        if start_date < make_naive(evt.date, utc) < end_date:
            if start_index is not None:
                range.append(evt)
            else:
                start_index = index
                range = [evt]
    return range

@login_required
def post_message(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all() and not game.has_super_access(request.user):
        raise PermissionDenied

    if request.is_ajax() and request.method == 'POST':
        message_form = MessageForm(data = request.POST)
        if message_form.is_valid() and len(message_form.cleaned_data['message']) > 0:
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