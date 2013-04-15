import logging
from django.conf import settings
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q, F
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now

from game.deal import deal_cards
from game.forms import CreateGameForm, validate_number_of_players, validate_dates, GameCommodityCardFormDisplay, GameCommodityCardFormParse
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer
from ruleset.models import RuleCard
from scoring.card_scoring import tally_scores, Scoresheet
from scoring.models import ScoreFromCommodity, ScoreFromRule
from trade.forms import RuleCardFormParse, RuleCardFormDisplay
from trade.models import Offer, Trade
from utils import utils

logger = logging.getLogger(__name__)

@login_required
def welcome(request):
    games = Game.objects.filter(Q(master=request.user) | Q(players=request.user)).distinct().order_by('-closing_date', '-end_date')
    for game in games:
        game.list_of_players = [player.get_profile().name for player in game.players.all().order_by('id')]
        game.hand_submitted = game.gameplayer_set.filter(submit_date__isnull = False, player = request.user).count() > 0
    return render(request, 'game/welcome.html', {'games': games})

@login_required
def hand(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if request.user not in game.players.all():
        raise PermissionDenied

    # if the hand has been submitted, we will split the commodities between submitted and not submitted
    hand_submitted = game.gameplayer_set.filter(submit_date__isnull = False, player = request.user).count() > 0

    rule_hand = RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = True).order_by('rulecard__ref_name')

    # commodities are ordered only alphabetically (by their name) in order to obfuscate their actual order in value
    if hand_submitted:
        commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_submitted_cards__gt = 0).order_by('commodity__name')
    else:
        commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_cards__gt = 0).order_by('commodity__name')

    commodity_hand_not_submitted = CommodityInHand.objects.filter(game = game, player = request.user,
                                                                  nb_cards__gt = F('nb_submitted_cards')).order_by('commodity__name')
    for not_submitted in commodity_hand_not_submitted:
        not_submitted.nb_cards -= not_submitted.nb_submitted_cards

    free_informations = []
    for offer in Offer.objects.filter(free_information__isnull=False, trade_responded__game=game,
                                      trade_responded__initiator=request.user, trade_responded__status='ACCEPTED'):
        free_informations.append({'offerer': offer.trade_responded.responder,
                                  'date': offer.trade_responded.closing_date,
                                  'free_information': offer.free_information})

    for offer in Offer.objects.filter(free_information__isnull=False, trade_initiated__game=game,
                                      trade_initiated__responder=request.user, trade_initiated__status='ACCEPTED'):
        free_informations.append({'offerer': offer.trade_initiated.responder,
                                  'date': offer.trade_initiated.closing_date,
                                  'free_information': offer.free_information})

    featured_rulecards = [rh.rulecard.id for rh in rule_hand]
    former_rules = []
    for rule in RuleInHand.objects.filter(game=game, player=request.user, abandon_date__isnull=False).order_by('rulecard__ref_name'):
        if rule.rulecard.id not in featured_rulecards: # add only rulecards that are not currently in the hand and no duplicates
            former_rules.append({'public_name': rule.rulecard.public_name,
                                 'description': rule.rulecard.description})
            featured_rulecards.append(rule.rulecard.id)

    return render(request, 'game/hand.html',
        {'game': game, 'hand_submitted': hand_submitted, 'rule_hand': rule_hand, 'former_rules': former_rules,
         'commodity_hand': commodity_hand, 'commodity_hand_not_submitted': commodity_hand_not_submitted,
         'free_informations': sorted(free_informations, key=lambda offer: offer['date'], reverse=True)})

@login_required
def submit_hand(request, game_id):
    game = get_object_or_404(Game, id=game_id)

    if request.user not in game.players.all():
        raise PermissionDenied

    # one can submit one own's hand only once
    if game.gameplayer_set.get(player = request.user).submit_date:
        raise PermissionDenied

    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_cards__gt = 0).order_by('commodity__name')

    if request.method == 'POST':
        CommodityCardsFormSet = formset_factory(GameCommodityCardFormParse)
        commodities_formset = CommodityCardsFormSet(request.POST, prefix='commodity')

        if commodities_formset.is_valid():
            try:
                with transaction.commit_on_success():
                    gameplayer = GamePlayer.objects.get(game = game, player = request.user)
                    gameplayer.submit_date = now()
                    gameplayer.save()

                    for commodity in commodity_hand:
                        for form in commodities_formset:
                            if int(form.cleaned_data['commodity_id']) == commodity.commodity.id:
                                commodity.nb_submitted_cards = form.cleaned_data['nb_submitted_cards']
                                break
                        else: # if the for loop ends without a break, ie we didn't find the commodity in the form -- shouldn't happen but here for security
                            commodity.nb_submitted_cards = commodity.nb_cards
                        commodity.save()

                    # abort pending trades
                    for trade in Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game, finalizer__isnull = True):
                        trade.abort(request.user, gameplayer.submit_date)

            except BaseException as ex:
                logger.error("Error in submit_hand({})".format(game_id), exc_info = ex)

            return HttpResponseRedirect(reverse('welcome'))
        else:
            pass # no reason to come here
    else:
        CommodityCardsFormSet = formset_factory(GameCommodityCardFormDisplay, extra=0)
        commodities_formset = CommodityCardsFormSet(initial=[{'commodity_id': card.commodity.id,
                                                              'name': card.commodity.name,
                                                              'color': card.commodity.color,
                                                              'nb_cards': card.nb_cards,
                                                              'nb_submitted_cards': card.nb_cards}
                                                             for card in commodity_hand],
            prefix='commodity')

    return render(request, 'game/submit_hand.html', {'game': game, 'commodities_formset': commodities_formset})

#############################################################################
##                              Games                                      ##
#############################################################################

@permission_required('game.add_game')
def create_game(request):
    if request.method == 'POST':
        form = CreateGameForm(request.user, request.POST)
        if form.is_valid():
            request.session['ruleset'] = form.cleaned_data['ruleset']
            request.session['start_date'] = form.cleaned_data['start_date']
            request.session['end_date'] = form.cleaned_data['end_date']
            request.session['players'] = list(form.cleaned_data['players'].all()) # convert from Queryset to list
            request.session['profiles'] = [user.get_profile() for user in request.session['players']]
            return HttpResponseRedirect(reverse('select_rules'))
    else:
        form = CreateGameForm(request.user)
    return render(request, 'game/create.html', {'form': form})

@permission_required('game.add_game')
def select_rules(request):
    if 'ruleset' not in request.session or 'start_date' not in request.session\
       or 'end_date' not in request.session or 'players' not in request.session:
        return HttpResponseRedirect(reverse('create_game'))

    ruleset = request.session['ruleset']
    start_date = request.session['start_date']
    end_date = request.session['end_date']
    players = request.session['players']

    try:
        validate_dates(start_date, end_date)
        validate_number_of_players(players, ruleset)
    except ValidationError:
        return HttpResponseRedirect(reverse('create_game'))

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
                error = "Please select at most {} rule cards (including the mandatory ones)".format(len(players))
                RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
                formset = RuleCardsFormSet(initial=[{'card_id': card.id,
                                                     'public_name': card.public_name,
                                                     'description': card.description,
                                                     'mandatory': bool(card.mandatory),
                                                     'selected_rule': bool(card in selected_rules)}
                                                    for card in rulecards_queryset])
                return render(request, 'game/rules.html', {'formset': formset, 'session': request.session, 'error': error})
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
                del request.session['profiles']

                # deal starting cards
                deal_cards(game)

                # email notification
                all_players = {}
                for player in game.players.all():
                     all_players[player] = {'name': player.get_profile().name,
                                            'url': request.build_absolute_uri(reverse('otherprofile', args=[player.id]))}

                if game.is_active():
                     url = request.build_absolute_uri(reverse('trades', args = [game.id]))
                else: # game not yet started
                     url = request.build_absolute_uri(reverse('hand', args = [game.id]))

                for player in all_players.iterkeys():
                     opponents = dict(all_players) # make a copy
                     del opponents[player]
                     list_opponents = sorted(opponents.itervalues(), key = lambda opponent: opponent['name'])
                     rules = RuleInHand.objects.filter(game = game, player = player).order_by('rulecard__ref_name')
                     commodities = CommodityInHand.objects.filter(game = game, player = player).order_by('commodity__name') # alphabetical sort to obfuscate the value order of the commodities
                     utils.send_notification_email('game_create', player,
                                                   {'game': game, 'opponents': list_opponents, 'rules': rules, 'commodities': commodities, 'url': url})

                # email notification for the admins
                utils.send_notification_email('game_create_admin', [admin[1] for admin in settings.ADMINS],
                                               {'game': game, 'players': sorted(all_players.itervalues(), key = lambda player: player['name']),
                                                'rules': selected_rules})

                return HttpResponseRedirect(reverse('welcome'))
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra=0)
        formset = RuleCardsFormSet(initial=[{'card_id': card.id,
                                             'public_name': card.public_name,
                                             'description': card.description,
                                             'mandatory': bool(card.mandatory)}
                                            for card in rulecards_queryset])
        return render(request, 'game/rules.html', {'formset': formset, 'session': request.session})

#############################################################################
##                          Control Board                                  ##
#############################################################################
TRADES_PAGINATION = 10

@login_required
def control_board(request, game_id):
    game = get_object_or_404(Game, id = game_id)
    data = {'game': game}

    if request.user == game.master or request.user.is_staff:
        if game.is_closed():
            data['scoresheets'] = _fetch_scoresheets(game)
        elif game.is_active():
            scoresheets = tally_scores(game) # but don't persist them
            scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)
            random_scoring = False
            for scoresheet in scoresheets:
                if len([sfr for sfr in scoresheet.scores_from_rule if getattr(sfr, 'is_random', False)]) > 0:
                    scoresheet.is_random = True
                    random_scoring = True
            data['scoresheets'] = scoresheets
            # means at least one line of score for one player can earn a different amount of points each time we calculate the score
            data['random_scoring'] = random_scoring

        paginator = Paginator(Trade.objects.filter(game = game).order_by('-closing_date', '-creation_date'),
                              per_page = TRADES_PAGINATION, orphans = 1)
        page = request.GET.get('page')
        try:
            trades = paginator.page(page)
        except PageNotAnInteger:
            trades = paginator.page(1) # If page is not an integer, deliver first page.
        except EmptyPage:
            trades = paginator.page(paginator.num_pages) # If page is out of range, deliver last page of results.
        data['trades'] = trades

        return render(request, 'game/control.html', data)

    raise PermissionDenied

@login_required
def player_score(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all() or not game.is_closed():
        raise PermissionDenied

    scoresheets = _fetch_scoresheets(game)
    for index, scoresheet in enumerate(scoresheets, start = 1):
        if scoresheet.gameplayer.player == request.user:
            rank = index

    return render(request, 'game/player_score.html', {'game': game, 'scoresheets': scoresheets, 'rank': rank})

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

    if request.method == 'POST' and (request.user == game.master or request.user.is_staff):
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
                        for cih in CommodityInHand.objects.filter(game = game, nb_cards__gt = 0, player = gameplayer.player):
                            cih.nb_submitted_cards = cih.nb_cards
                            cih.save()
                        gameplayer.submit_date = game.closing_date
                        gameplayer.save()

                    # calculate and save scores
                    scoresheets = tally_scores(game)
                    for scoresheet in scoresheets:
                        scoresheet.persist()

                    # email notification
                    scoresheets.sort(key = lambda scoresheet: scoresheet.total_score, reverse = True)
                    for rank, scoresheet in enumerate(scoresheets, 1):
                        utils.send_notification_email('game_close', scoresheet.gameplayer.player,
                                                      {'game': game, 'rank': rank, 'nb_players': len(scoresheets), 'scoresheet': scoresheet,
                                                       'url': request.build_absolute_uri(reverse('player_score', args = [game.id]))})

                    # email notification for the admins
                    utils.send_notification_email('game_close_admin', [admin[1] for admin in settings.ADMINS],
                                                  {'game': game, 'scoresheets': scoresheets,
                                                   'url': request.build_absolute_uri(reverse('control', args = [game.id]))})

            except BaseException as ex:
                logger.error("Error in close_game({})".format(game_id), exc_info = ex)

            return HttpResponseRedirect(reverse('control', args = [game_id]))

    raise PermissionDenied
