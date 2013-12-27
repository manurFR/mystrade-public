import logging
import bleach
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, NON_FIELD_ERRORS
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from game.helpers import rules_in_hand, commodities_in_hand, _check_game_access_or_PermissionDenied
from game.models import RuleInHand, CommodityInHand, Game, GamePlayer
from trade.forms import FinalizeReasonForm, TradeForm, OfferForm
from trade.models import Trade, TradedCommodities, Offer
from utils import utils, stats

logger = logging.getLogger(__name__)

#############################################################################
##                       "Show all trades" list                            ##
#############################################################################
TRADE_PAGINATION = 8

@login_required
def trade_list(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    super_access = _check_game_access_or_PermissionDenied(game, request.user)

    if request.is_ajax():
        # the players can only see their own trades, whereas the game master can see all trades
        trade_list = Trade.objects.filter(game = game).order_by('-creation_date')
        if not super_access:
            trade_list = list(trade_list.filter(Q(initiator = request.user) | Q(responder = request.user)))

            # since sort() is guaranteed to be stable, this second sort will only push pending trades at the start,
            #   keeping the sorting by (reverse) chronological creation_date otherwise
            trade_list.sort(key = Trade.is_pending, reverse = True)

        paginator = Paginator(trade_list, TRADE_PAGINATION, orphans = 1)

        page = request.GET.get('page')
        try:
            trades = paginator.page(page)
        except PageNotAnInteger:
            trades = paginator.page(1)
        except EmptyPage:
            trades = paginator.page(paginator.num_pages) # If page is out of range (e.g. 9999), deliver last page of results.

        return render(request, 'trade/trade_list.html', {'game': game, 'trade_list': trades})

    raise PermissionDenied

#############################################################################
##                            Show Trade                                   ##
#############################################################################

@login_required
def show_trade(request, game_id, trade_id):
    trade = get_object_or_404(Trade, id = trade_id)

    if trade.game_id != int(game_id):
        raise PermissionDenied
    game = trade.game

    super_access = game.has_super_access(request.user)

    if request.user != trade.initiator and request.user != trade.responder and not super_access:
        raise PermissionDenied

    if request.is_ajax():
        if trade.status == 'INITIATED' and request.user == trade.responder:
            offer_form = _prepare_offer_form(request, trade.game)
            return render(request, 'trade/trade.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access,
                                                        'finalize_reason_form': FinalizeReasonForm(), 'offer_form': offer_form})
        elif trade.status == 'REPLIED' and request.user == trade.initiator:
            return render(request, 'trade/trade.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access,
                                                        'finalize_reason_form': FinalizeReasonForm()})
        else:
            return render(request, 'trade/trade.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access})

    raise PermissionDenied

#############################################################################
##                           Create Trade                                  ##
#############################################################################

@login_required
def create_trade(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    # Trade creation is not allowed for :
    #  - players who have already submitted their hand
    #  - all site users who are not players in this game (including the game master and admins who are not players)
    try:
        if GamePlayer.objects.get(game = game, player = request.user).submit_date:
            raise PermissionDenied
    except GamePlayer.DoesNotExist:
        raise PermissionDenied

    if request.is_ajax() and game.is_active():
        errors = False
        if request.method == 'POST':
            trade_form = TradeForm(request.user, game, request.POST)

            try:
                offer, selected_commodities, selected_rulecards = _parse_offer_form(request, game)

                if trade_form.is_valid():
                    offer.save()
                    for cih, nb_traded_cards in selected_commodities.iteritems():
                        if nb_traded_cards > 0:
                            TradedCommodities.objects.create(offer = offer, commodityinhand = cih, nb_traded_cards = nb_traded_cards)
                    for rih in selected_rulecards:
                        offer.rules.add(rih)

                    trade = Trade.objects.create(game = game, initiator = request.user, initiator_offer = offer,
                                                              responder = trade_form.cleaned_data['responder'])

                    # email notification
                    _trade_event_notification(request, trade)

                    return HttpResponse()
                else:
                    errors = True
                    offer_form = _prepare_offer_form(request, game, offer, selected_commodities, selected_rulecards)
            except FormInvalidException as ex:
                errors = True
                offer_form = _prepare_offer_form(request, game, ex.formdata['offer'], ex.formdata['selected_commodities'], ex.formdata['selected_rules'])
                offer_form._errors = {NON_FIELD_ERRORS: ex.formdata['offer_errors']}
        else:
            trade_form = TradeForm(request.user, game)
            offer_form = _prepare_offer_form(request, game)

        return render(request, 'trade/trade.html', {'game': game, 'trade_form': trade_form, 'offer_form': offer_form, 'errors': errors},
                      status = 422 if errors else 200)

    raise PermissionDenied

#############################################################################
##                           Trade Actions                                 ##
#############################################################################

@login_required
def cancel_trade(request, game_id, trade_id):
    if request.is_ajax() and request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if (trade.game_id == int(game_id) and trade.game.is_active() and
            ((trade.status == 'INITIATED' and request.user == trade.initiator) or
             (trade.status == 'REPLIED' and request.user == trade.responder))):
            trade.status = 'CANCELLED'
            trade.finalizer = request.user
            trade.closing_date = now()
            trade.save()

            # email notification                               x
            _trade_event_notification(request, trade)

            return HttpResponse()

    raise PermissionDenied

@login_required
def reply_trade(request, game_id, trade_id):
    if request.is_ajax() and request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)

        if (trade.game_id == int(game_id) and trade.game.is_active() and
           trade.status == 'INITIATED' and request.user == trade.responder):
            try:
                offer, selected_commodities, selected_rulecards = _parse_offer_form(request, trade.game)

                offer.save()
                for cih, nb_traded_cards in selected_commodities.iteritems():
                    if nb_traded_cards > 0:
                        TradedCommodities.objects.create(offer = offer, commodityinhand = cih, nb_traded_cards = nb_traded_cards)
                for rih in selected_rulecards:
                    offer.rules.add(rih)

                trade.status = 'REPLIED'
                trade.responder_offer = offer
                trade.save()

                # email notification
                _trade_event_notification(request, trade)

                return HttpResponse()
            except FormInvalidException as ex:
                status_code = 422
                offer_form = _prepare_offer_form(request, trade.game, ex.formdata['offer'], ex.formdata['selected_commodities'], ex.formdata['selected_rules'])
                offer_form._errors = {NON_FIELD_ERRORS: ex.formdata['offer_errors']}

                return render(request, 'trade/trade.html', {'game': trade.game, 'trade': trade, 'offer_form': offer_form, 'errors': True}, status = status_code)

    raise PermissionDenied

@login_required
def accept_trade(request, game_id, trade_id):
    if request.is_ajax() and request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if (trade.game_id == int(game_id) and trade.game.is_active() and
            trade.status == 'REPLIED' and request.user == trade.initiator):
            # Accepting a trade and exchanging the cards is a near-perfect textbook example of a process that must be transactional
            try:
                with transaction.commit_on_success():
                    finalize_reason_form = FinalizeReasonForm(request.POST)
                    if finalize_reason_form.is_valid():
                        trade.status = 'ACCEPTED'
                        trade.finalizer = request.user
                        trade.finalize_reason = bleach.clean(finalize_reason_form.cleaned_data['finalize_reason'], tags = [], strip = True)
                        trade.closing_date = now()
                        trade.save()

                        # Exchange rule cards
                        for rule_from_initiator in trade.initiator_offer.rulecards:
                            RuleInHand.objects.create(game = trade.game, player = trade.responder, rulecard = rule_from_initiator.rulecard,
                                                      ownership_date = trade.closing_date, previous_owner = trade.initiator)
                            rule_from_initiator.abandon_date = trade.closing_date
                            rule_from_initiator.next_owner = trade.responder
                            rule_from_initiator.save()
                        for rule_from_responder in trade.responder_offer.rulecards:
                            RuleInHand.objects.create(game = trade.game, player = trade.initiator, rulecard = rule_from_responder.rulecard,
                                                      ownership_date = trade.closing_date, previous_owner = trade.responder)
                            rule_from_responder.abandon_date = trade.closing_date
                            rule_from_responder.next_owner = trade.initiator
                            rule_from_responder.save()

                        # Exchange commodity cards
                        for tradedcommodity_from_initiator in trade.initiator_offer.tradedcommodities:
                            cih_from_initiator = tradedcommodity_from_initiator.commodityinhand
                            try:
                                cih_for_responder = CommodityInHand.objects.get(game = trade.game, player = trade.responder,
                                                                                commodity = cih_from_initiator.commodity)
                            except CommodityInHand.DoesNotExist:
                                cih_for_responder = CommodityInHand(game = trade.game, player = trade.responder,
                                                                    commodity = cih_from_initiator.commodity, nb_cards = 0)
                            cih_for_responder.nb_cards += tradedcommodity_from_initiator.nb_traded_cards
                            cih_for_responder.save()
                            cih_from_initiator.nb_cards -= tradedcommodity_from_initiator.nb_traded_cards
                            cih_from_initiator.save()

                        for tradedcommodity_from_responder in trade.responder_offer.tradedcommodities:
                            cih_from_responder = tradedcommodity_from_responder.commodityinhand
                            try:
                                cih_for_initiator = CommodityInHand.objects.get(game = trade.game, player = trade.initiator,
                                                                                commodity = cih_from_responder.commodity)
                            except CommodityInHand.DoesNotExist:
                                cih_for_initiator = CommodityInHand(game = trade.game, player = trade.initiator,
                                                                    commodity = cih_from_responder.commodity, nb_cards = 0)
                            cih_for_initiator.nb_cards += tradedcommodity_from_responder.nb_traded_cards
                            cih_for_initiator.save()
                            cih_from_responder.nb_cards -= tradedcommodity_from_responder.nb_traded_cards
                            cih_from_responder.save()

                        # record score stats after each completed trade
                        stats.record(trade.game, trade = trade)

                        # email notification
                        _trade_event_notification(request, trade)
                    else:
                        raise FormInvalidException({'form': 'finalize_reason_form'})
            except BaseException as ex:
                # if anything crappy happens, rollback the transaction and do nothing else except logging
                logger.error("Error in accept_trace({0}, {1})".format(game_id, trade_id), exc_info = ex)

            return HttpResponse()

    raise PermissionDenied

@login_required
def decline_trade(request, game_id, trade_id):
    if request.is_ajax() and request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if (trade.game_id == int(game_id) and trade.game.is_active() and
            ((trade.status == 'INITIATED' and request.user == trade.responder) or
            (trade.status == 'REPLIED' and request.user == trade.initiator))):
            finalize_reason_form = FinalizeReasonForm(request.POST)
            if finalize_reason_form.is_valid():
                trade.status = 'DECLINED'
                trade.finalizer = request.user
                trade.finalize_reason = bleach.clean(finalize_reason_form.cleaned_data['finalize_reason'], tags = [], strip = True)
                trade.closing_date = now()
                trade.save()

                # email notification
                _trade_event_notification(request, trade)

                return HttpResponse()

    raise PermissionDenied

def _prepare_offer_form(request, game, offer = None, selected_commodities = {}, selected_rulecards = []):
    commodity_hand = commodities_in_hand(game, request.user)
    rule_hand = [rule for rule in rules_in_hand(game, request.user) if not rule.is_in_a_pending_trade()]

    initial = {}
    for cih in commodity_hand:
        initial.update({'commodity_{0}'.format(cih.commodity_id): selected_commodities.get(cih, 0)})
    for rih in rule_hand:
        initial.update({'rulecard_{0}'.format(rih.id): (rih in selected_rulecards)})

    if offer:
        initial.update({'free_information': offer.free_information,
                        'comment':          offer.comment})

    return OfferForm(commodities = commodity_hand, rulecards = rule_hand, initial = initial)

def _parse_offer_form(request, game):
    commodity_hand = commodities_in_hand(game, request.user)
    rule_hand = rules_in_hand(game, request.user) # include rules reserved for another trade as they are errors that have to be detected

    offer_form = OfferForm(request.POST, commodities = commodity_hand, rulecards = rule_hand)
    offer_valid = offer_form.is_valid() # fill the cleaned_data array

    errors = offer_form.non_field_errors()

    selected_commodities = {}
    for cih in commodity_hand:
        nb_selected_cards = offer_form.cleaned_data['commodity_{0}'.format(cih.commodity_id)]
        selected_commodities[cih] = nb_selected_cards
        if nb_selected_cards > cih.nb_tradable_cards():
            errors.append(u"A commodity card in a pending trade can not be offered in another trade.")

    selected_rules = []
    for rih in rule_hand:
        if offer_form.cleaned_data['rulecard_{0}'.format(rih.id)]:
            selected_rules.append(rih)
            if rih.is_in_a_pending_trade():
                errors.append(u"A rule card in a pending trade can not be offered in another trade.")

    offer = Offer(free_information = bleach.clean(offer_form.cleaned_data['free_information'], tags = [], strip = True) or None, # 'or None' necessary to insert null (not empty) values
                  comment          = bleach.clean(offer_form.cleaned_data['comment'], tags = [], strip = True) or None)

    if not offer_valid or errors:
        raise FormInvalidException({'offer': offer,
                                    'selected_commodities': selected_commodities,
                                    'selected_rules': selected_rules,
                                    'offer_errors': errors})

    return offer, selected_commodities, selected_rules

def _trade_event_notification(request, trade):
    notification_templates = {'INITIATED': 'trade_offer',
                              'CANCELLED': 'trade_cancel',
                              'REPLIED':   'trade_reply',
                              'ACCEPTED':  'trade_accept',
                              'DECLINED':  'trade_decline'}
    template = notification_templates[trade.status]

    if request.user == trade.initiator:
        recipient = trade.responder
    else:
        recipient = trade.initiator

    utils.send_notification_email(template, recipient,
                                  {'game': trade.game, 'trade': trade, 'player_timezone': recipient.timezone,
                                   'url': request.build_absolute_uri(reverse('game_with_trade', args = [trade.game_id, trade.id]))})

class FormInvalidException(Exception):
    def __init__(self, formdata, *args, **kwargs):
        super(FormInvalidException, self).__init__(*args, **kwargs)
        self.formdata = formdata
