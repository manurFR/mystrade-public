import logging
import bleach
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, NON_FIELD_ERRORS
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.timezone import now
from game.helpers import rules_currently_in_hand, commodities_in_hand
from game.models import RuleInHand, CommodityInHand, Game, GamePlayer
from trade.forms import DeclineReasonForm, TradeForm, RuleCardFormDisplay, TradeCommodityCardFormDisplay, OfferForm, RuleCardFormParse, BaseRuleCardsFormSet, TradeCommodityCardFormParse, BaseCommodityCardFormSet
from trade.models import Trade, TradedCommodities, Offer
from utils import utils, stats

logger = logging.getLogger(__name__)

@login_required
def trades(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all() and not game.has_super_access(request.user):
        raise PermissionDenied

    trades = Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game).order_by('-creation_date')

    try:
        can_create_trade = game.gameplayer_set.get(player = request.user).submit_date is None
    except GamePlayer.DoesNotExist:
        can_create_trade = False

    return render(request, 'trade/trades.html', {'game': game, 'trades': trades, 'can_create_trade': can_create_trade})

@login_required
def show_trade(request, game_id, trade_id):
    trade = get_object_or_404(Trade, id = trade_id)
    game = trade.game

    super_access = game.has_super_access(request.user)

    if request.user != trade.initiator and request.user != trade.responder and not super_access:
        raise PermissionDenied

    if trade.status == 'INITIATED' and request.user == trade.responder:
        offer_form, rulecards_formset, commodities_formset = _prepare_offer_form(request, trade.game)
        return render(request, 'trade/trade_offer.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access,
                                                          'decline_reason_form': DeclineReasonForm(), 'offer_form': offer_form,
                                                          'rulecards_formset': rulecards_formset, 'commodities_formset': commodities_formset})
    elif trade.status == 'REPLIED' and request.user == trade.initiator:
        return render(request, 'trade/trade_offer.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access,
                                                          'decline_reason_form': DeclineReasonForm()})
    else:
        return render(request, 'trade/trade_offer.html', {'game': game, 'trade': trade, 'errors': False, 'super_access': super_access})

@login_required
def create_trade(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    # Trade creation is not allowed for :
    #  - players who have already submitted their hand to the game master
    #  - all site users who are not players in this game (including the game master and admins who are not players)
    try:
        if GamePlayer.objects.get(game = game, player = request.user).submit_date:
            raise PermissionDenied
    except GamePlayer.DoesNotExist:
        raise PermissionDenied

    if request.is_ajax():
        status_code = 200
        if request.method == 'POST':
            new_trade_form = TradeForm(request.user, game, request.POST)

            try:
                offer, selected_commodities, selected_rulecards = _parse_offer_form(request, game)

                if new_trade_form.is_valid():
                    offer.save()
                    for rih in selected_rulecards:
                        offer.rules.add(rih)
                    for cih, nb_traded_cards in selected_commodities.iteritems():
                        if nb_traded_cards > 0:
                            TradedCommodities.objects.create(offer = offer, commodityinhand = cih, nb_traded_cards = nb_traded_cards)

                    trade = Trade.objects.create(game = game, initiator = request.user, initiator_offer = offer,
                                                              responder = new_trade_form.cleaned_data['responder'])

                    # email notification
                    _trade_event_notification(request, trade)

                    return HttpResponse()
                else:
                    status_code = 422
                    new_offer_form = _prepare_offer_form(request, game, offer, selected_commodities, selected_rulecards)
            except FormInvalidException as ex:
                status_code = 422
                new_offer_form = _prepare_offer_form(request, game, ex.formdata['offer'], ex.formdata['selected_commodities'], ex.formdata['selected_rules'])
                new_offer_form._errors = {NON_FIELD_ERRORS: ex.formdata['offer_errors']}

            # try:
            #     offer, selected_rules, selected_commodities = _parse_offer_forms(request, game)
            #     if trade_form.is_valid():
            #         offer.save()
            #         for card in selected_rules:
            #             offer.rules.add(card)
            #         for commodityinhand, nb_traded_cards in selected_commodities.iteritems():
            #             if nb_traded_cards > 0:
            #                 TradedCommodities.objects.create(offer = offer, commodityinhand = commodityinhand, nb_traded_cards = nb_traded_cards)
            #
            #         trade = Trade.objects.create(game = game, initiator = request.user, initiator_offer = offer,
            #                                      responder = trade_form.cleaned_data['responder'])
            #
            #         # email notification
            #         _trade_event_notification(request, trade)
            #
            #         return redirect('trades', game.id)
            #     else:
            #         offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, game, selected_rules, selected_commodities, offer)
            # except FormInvalidException as ex:
            #     offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, game,
            #                                                                               ex.formdata['selected_rules'],
            #                                                                               ex.formdata['selected_commodities'],
            #                                                                               ex.formdata['offer'])
            #     rulecards_formset._non_form_errors = ex.formdata['rulecards_errors']
            #     commodities_formset._non_form_errors = ex.formdata['commodities_errors']
            #     offer_form._errors = {NON_FIELD_ERRORS: ex.formdata['offer_errors']}

        else:
            new_trade_form = TradeForm(request.user, game)
            new_offer_form = _prepare_offer_form(request, game)

        return render(request, 'trade/trade.html', {'game': game, 'new_trade_form': new_trade_form, 'new_offer_form': new_offer_form},
                      status = status_code)

    raise PermissionDenied

@login_required
def cancel_trade(request, game_id, trade_id):
    if request.method == 'POST':
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

            return redirect('trades', game_id)

    raise PermissionDenied

@login_required
def reply_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)

        if (trade.game_id == int(game_id) and trade.game.is_active() and
           trade.status == 'INITIATED' and request.user == trade.responder):
            try:
                offer, selected_rules, selected_commodities = _parse_offer_form(request, trade.game)

                offer.save()
                for card in selected_rules:
                    offer.rules.add(card)
                for commodityinhand, nb_traded_cards in selected_commodities.iteritems():
                    if nb_traded_cards > 0:
                        TradedCommodities.objects.create(offer = offer, commodityinhand = commodityinhand, nb_traded_cards = nb_traded_cards)

                trade.status = 'REPLIED'
                trade.responder_offer = offer
                trade.save()

                # email notification
                _trade_event_notification(request, trade)

                return redirect('trades', trade.game_id)
            except FormInvalidException as ex:
                offer_form, rulecards_formset, commodities_formset = _prepare_offer_form(request, trade.game,
                                                                                          ex.formdata['selected_rules'],
                                                                                          ex.formdata['selected_commodities'],
                                                                                          ex.formdata['offer'])
                rulecards_formset._non_form_errors = ex.formdata['rulecards_errors']
                commodities_formset._non_form_errors = ex.formdata['commodities_errors']
                offer_form._errors = {NON_FIELD_ERRORS: ex.formdata['offer_errors']}

                return render(request, 'trade/trade_offer.html', {'game': trade.game, 'trade': trade,
                                                                  'errors': True, 'offer_form': offer_form,
                                                                  'rulecards_formset': rulecards_formset, 'commodities_formset': commodities_formset})

    raise PermissionDenied # if the method is not POST or the user is not the responder or the status is not INITIATED or the game has ended

@login_required
def accept_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if (trade.game_id == int(game_id) and trade.game.is_active() and
            trade.status == 'REPLIED' and request.user == trade.initiator):
            # Accepting a trade and exchanging the cards is a near-perfect textbook example of a process that must be transactional
            try:
                with transaction.commit_on_success():
                    trade.status = 'ACCEPTED'
                    trade.finalizer = request.user
                    trade.closing_date = now()
                    trade.save()

                    # Exchange rule cards
                    for rule_from_initiator in trade.initiator_offer.rules.all():
                        RuleInHand.objects.create(game = trade.game, player = trade.responder, rulecard = rule_from_initiator.rulecard,
                            ownership_date = trade.closing_date)
                        rule_from_initiator.abandon_date = trade.closing_date
                        rule_from_initiator.save()
                    for rule_from_responder in trade.responder_offer.rules.all():
                        RuleInHand.objects.create(game = trade.game, player = trade.initiator, rulecard = rule_from_responder.rulecard,
                            ownership_date = trade.closing_date)
                        rule_from_responder.abandon_date = trade.closing_date
                        rule_from_responder.save()

                    # Exchange commodity cards
                    for tradedcommodity_from_initiator in trade.initiator_offer.tradedcommodities_set.all():
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

                    for tradedcommodity_from_responder in trade.responder_offer.tradedcommodities_set.all():
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
            except BaseException as ex:
                # if anything crappy happens, rollback the transaction and do nothing else except logging
                logger.error("Error in accept_trace({0}, {1})".format(game_id, trade_id), exc_info = ex)

            return redirect('trades', game_id)

    raise PermissionDenied

@login_required
def decline_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if (trade.game_id == int(game_id) and trade.game.is_active() and
            ((trade.status == 'INITIATED' and request.user == trade.responder) or
            (trade.status == 'REPLIED' and request.user == trade.initiator))):
            decline_reason_form = DeclineReasonForm(request.POST)
            if decline_reason_form.is_valid():
                trade.status = 'DECLINED'
                trade.finalizer = request.user
                trade.decline_reason = bleach.clean(decline_reason_form.cleaned_data['decline_reason'], tags = [], strip = True)
                trade.closing_date = now()
                trade.save()

                # email notification
                _trade_event_notification(request, trade)

                return redirect('trades', game_id)

    raise PermissionDenied

def _prepare_offer_form(request, game, offer = None, selected_commodities = {}, selected_rulecards = []):
    commodity_hand = commodities_in_hand(game, request.user)
    rule_hand = [rule for rule in rules_currently_in_hand(game, request.user) if not rule.is_in_a_pending_trade()]

    # RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra=0)
    # rulecards_formset = RuleCardsFormSet(initial=sorted([{'card_id':       card.id,
    #                                                       'public_name':   card.rulecard.public_name,
    #                                                       'description':   card.rulecard.description,
    #                                                       'reserved':      card.is_in_a_pending_trade(),
    #                                                       'selected_rule': bool(card in selected_rules)}
    #                                                      for card in rule_hand], key=lambda card: card['reserved']),
    #                                      prefix='rulecards')
    #
    # CommodityCardsFormSet = formset_factory(TradeCommodityCardFormDisplay, extra=0)
    # commodities_formset = CommodityCardsFormSet(initial=[{'commodity_id':      card.commodity_id,
    #                                                       'name':              card.commodity.name,
    #                                                       'color':             card.commodity.color,
    #                                                       'nb_cards':          card.nb_cards,
    #                                                       'nb_tradable_cards': card.nb_tradable_cards(),
    #                                                       'nb_traded_cards':   selected_commodities.get(card, 0)}
    #                                                      for card in commodity_hand],
    #                                             prefix='commodity')

    initial = {}
    for cih in commodity_hand:
        initial.update({'commodity_{0}'.format(cih.commodity_id): selected_commodities.get(cih, 0)})
    for rih in rule_hand:
        initial.update({'rulecard_{0}'.format(rih.id): (rih in selected_rulecards)})

    if offer:
        initial.update({'free_information': offer.free_information,
                        'comment':          offer.comment})

    return OfferForm(commodities = commodity_hand, rulecards = rule_hand,
                     initial = initial)

def _parse_offer_form(request, game):
    commodity_hand = commodities_in_hand(game, request.user)
    rule_hand = [rule for rule in rules_currently_in_hand(game, request.user) if not rule.is_in_a_pending_trade()]

    # RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
    # rulecards_formset = RuleCardsFormSet(request.POST, prefix = 'rulecards')
    # CommodityCardsFormSet = formset_factory(TradeCommodityCardFormParse, formset = BaseCommodityCardFormSet)
    # commodities_formset = CommodityCardsFormSet(request.POST, prefix = 'commodity')
    # commodities_formset.set_game(game)
    # commodities_formset.set_player(request.user)

    # fill the cleaned_data arrays
    # rulecards_valid = rulecards_formset.is_valid()
    # commodities_valid = commodities_formset.is_valid()

    offer_form = OfferForm(request.POST, commodities = commodity_hand, rulecards = rule_hand)
    offer_valid = offer_form.is_valid() # fill the cleaned_data array

    selected_commodities = {}
    for cih in commodity_hand:
        selected_commodities[cih] = offer_form.cleaned_data['commodity_{0}'.format(cih.commodity_id)]
    selected_rules = [rih for rih in rule_hand if offer_form.cleaned_data['rulecard_{0}'.format(rih.id)]]

    # offer_form = OfferForm(request.POST,
    #                        nb_selected_rules = len(selected_rules), nb_selected_commodities = sum(selected_commodities.values()))

    offer = Offer(free_information = bleach.clean(offer_form.cleaned_data['free_information'], tags = [], strip = True) or None, # 'or None' necessary to insert null (not empty) values
                  comment          = bleach.clean(offer_form.cleaned_data['comment'], tags = [], strip = True) or None)

    if not offer_valid:
        raise FormInvalidException({'offer': offer,
                                    'selected_commodities': selected_commodities,
                                    'selected_rules': selected_rules,
                                    'offer_errors': offer_form.non_field_errors()})

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
                                  {'game': trade.game, 'trade': trade,
                                   'url': request.build_absolute_uri(reverse('show_trade', args = [trade.game_id, trade.id]))})

class FormInvalidException(Exception):
    def __init__(self, formdata, *args, **kwargs):
        super(FormInvalidException, self).__init__(*args, **kwargs)
        self.formdata = formdata
