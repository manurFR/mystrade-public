import datetime
import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import get_default_timezone
from game.models import RuleInHand, CommodityInHand, Game
from trade.forms import DeclineReasonForm, TradeForm, RuleCardFormDisplay, CommodityCardFormDisplay, OfferForm, RuleCardFormParse, BaseRuleCardsFormSet, CommodityCardFormParse, BaseCommodityCardFormSet
from trade.models import Trade, TradedCommodities, Offer

logger = logging.getLogger(__name__)

@login_required
def trades(request, game_id):
    game = get_object_or_404(Game, id = game_id)
    trades = Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game).order_by('-creation_date')
    return render(request, 'game/trades.html', {'game': game, 'trades': trades})

@login_required
def create_trade(request, game_id):
    game = get_object_or_404(Game, id = game_id)
    errors = False

    if request.method == 'POST':
        trade_form = TradeForm(request.user, game, request.POST)

        try:
            offer, selected_rules, selected_commodities = _parse_offer_forms(request, game)
            if trade_form.is_valid():
                offer.save()
                for card in selected_rules:
                    offer.rules.add(card)
                for commodity, nb_traded_cards in selected_commodities.iteritems():
                    if nb_traded_cards > 0:
                        TradedCommodities.objects.create(offer = offer, commodity = commodity, nb_traded_cards = nb_traded_cards)

                #noinspection PyUnusedLocal
                trade = Trade.objects.create(game = game, initiator = request.user, initiator_offer = offer,
                    responder = trade_form.cleaned_data['responder'])
                return HttpResponseRedirect(reverse('trades', args = [game.id]))
            else:
                offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, game, selected_rules, selected_commodities)
        except FormInvalidException as ex:
            rulecards_formset = ex.forms['rulecards_formset']
            commodities_formset = ex.forms['commodities_formset']
            if 'offer_form' in ex.forms:
                offer_form = ex.forms['offer_form']
        errors = True
    else:
        offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, game)
        trade_form = TradeForm(request.user, game)

    return render(request, 'game/trade_offer.html', {'game': game, 'trade_form': trade_form, 'offer_form': offer_form,
                                                     'rulecards_formset': rulecards_formset, 'commodities_formset': commodities_formset})

@login_required
def cancel_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if ((trade.status == 'INITIATED' and request.user == trade.initiator) or
            (trade.status == 'REPLIED' and request.user == trade.responder)):
            trade.status = 'CANCELLED'
            trade.finalizer = request.user
            trade.closing_date = datetime.datetime.now(tz = get_default_timezone())
            trade.save()
            return HttpResponseRedirect(reverse('trades', args = [game_id]))

    raise PermissionDenied

@login_required
def show_trade(request, game_id, trade_id):
    trade = get_object_or_404(Trade, id = trade_id)

    if request.user != trade.initiator and request.user != trade.responder and request.user != trade.game.master\
    and not request.user.is_staff:
        raise PermissionDenied

    if trade.status == 'INITIATED' and request.user == trade.responder:
        offer_form, rulecards_formset, commodities_formset = _prepare_offer_forms(request, trade.game)
        return render(request, 'game/trade_offer.html', {'game': trade.game, 'trade': trade, 'errors': False,
                                                         'decline_reason_form': DeclineReasonForm(), 'offer_form': offer_form,
                                                         'rulecards_formset': rulecards_formset, 'commodities_formset': commodities_formset})
    elif trade.status == 'REPLIED' and request.user == trade.initiator:
        return render(request, 'game/trade_offer.html', {'game': trade.game, 'trade': trade, 'errors': False,
                                                         'decline_reason_form': DeclineReasonForm()})
    else:
        return render(request, 'game/trade_offer.html', {'game': trade.game, 'trade': trade, 'errors': False})

@login_required
def reply_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)

        if trade.status == 'INITIATED' and request.user == trade.responder:
            try:
                offer, selected_rules, selected_commodities = _parse_offer_forms(request, trade.game)

                offer.save()
                for card in selected_rules:
                    offer.rules.add(card)
                for commodity, nb_traded_cards in selected_commodities.iteritems():
                    if nb_traded_cards > 0:
                        TradedCommodities.objects.create(offer = offer, commodity = commodity, nb_traded_cards = nb_traded_cards)

                trade.status = 'REPLIED'
                trade.responder_offer = offer
                trade.save()

                return HttpResponseRedirect(reverse('trades', args = [trade.game.id]))
            except FormInvalidException as ex:
                rulecards_formset = ex.forms['rulecards_formset']
                commodities_formset = ex.forms['commodities_formset']
                if 'offer_form' in ex.forms:
                    offer_form = ex.forms['offer_form']
                return render(request, 'game/trade_offer.html', {'game': trade.game, 'trade': trade,
                                                                 'errors': True, 'offer_form': offer_form,
                                                                 'rulecards_formset': rulecards_formset, 'commodities_formset': commodities_formset})

    raise PermissionDenied # if the method is not POST or the user is not the responder or the status is not INITIATED

def _prepare_offer_forms(request, game, selected_rules = [], selected_commodities = {}):
    rule_hand = RuleInHand.objects.filter(game=game, player=request.user, abandon_date__isnull=True).order_by('rulecard__ref_name')
    commodity_hand = CommodityInHand.objects.filter(game=game, player=request.user, nb_cards__gt = 0).order_by('commodity__value', 'commodity__name')

    RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra=0)
    rulecards_formset = RuleCardsFormSet(initial=sorted(
        [{'card_id':       card.id,
          'public_name':   card.rulecard.public_name,
          'description':   card.rulecard.description,
          'reserved':      card.is_in_a_pending_trade(),
          'selected_rule': bool(card in selected_rules)}
         for card in rule_hand], key=lambda card: card['reserved']),
        prefix='rulecards')

    CommodityCardsFormSet = formset_factory(CommodityCardFormDisplay, extra=0)
    commodities_formset = CommodityCardsFormSet(initial=[{'commodity_id':      card.commodity.id,
                                                          'name':              card.commodity.name,
                                                          'color':             card.commodity.color,
                                                          'nb_cards':          card.nb_cards,
                                                          'nb_tradable_cards': card.nb_tradable_cards(),
                                                          'nb_traded_cards':   selected_commodities.get(card, 0)}
                                                         for card in commodity_hand],
        prefix='commodity')

    offer_form = OfferForm()

    return offer_form, rulecards_formset, commodities_formset

def _parse_offer_forms(request, game):
    rule_hand = RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = True).order_by('rulecard__ref_name')
    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_cards__gt = 0).order_by('commodity__value', 'commodity__name')

    RuleCardsFormSet = formset_factory(RuleCardFormParse, formset = BaseRuleCardsFormSet)
    rulecards_formset = RuleCardsFormSet(request.POST, prefix = 'rulecards')
    CommodityCardsFormSet = formset_factory(CommodityCardFormParse, formset = BaseCommodityCardFormSet)
    commodities_formset = CommodityCardsFormSet(request.POST, prefix = 'commodity')
    commodities_formset.set_game(game)
    commodities_formset.set_player(request.user)

    if not rulecards_formset.is_valid() or not commodities_formset.is_valid():
        raise FormInvalidException({'rulecards_formset' : rulecards_formset, 'commodities_formset' : commodities_formset})

    selected_rules = []
    for card in rule_hand:
        for form in rulecards_formset:
            if form.cleaned_data['card_id'] == card.id and form.cleaned_data['selected_rule']:
                selected_rules.append(card)
                break
    selected_commodities = {}
    for commodity in commodity_hand:
        for form in commodities_formset:
            if int(form.cleaned_data['commodity_id']) == commodity.commodity.id:
                selected_commodities[commodity] = form.cleaned_data['nb_traded_cards']
                break

    offer_form = OfferForm(request.POST,
        nb_selected_rules = len(selected_rules), nb_selected_commodities = sum(selected_commodities.values()))

    if not offer_form.is_valid():
        dummy, rulecards_formset, commodities_formset = _prepare_offer_forms(request, game, selected_rules, selected_commodities)
        raise FormInvalidException({'rulecards_formset' : rulecards_formset, 'commodities_formset' : commodities_formset,
                                    'offer_form' : offer_form})

    offer = Offer(free_information = offer_form.cleaned_data['free_information'],
                  comment          = offer_form.cleaned_data['comment'])

    return offer, selected_rules, selected_commodities

@login_required
def accept_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if trade.status == 'REPLIED' and request.user == trade.initiator:
            # Accepting a trade and exchanging the cards is a near-perfect textbook example of a process that must be transactional
            try:
                with transaction.commit_on_success():
                    trade.status = 'ACCEPTED'
                    trade.finalizer = request.user
                    trade.closing_date = datetime.datetime.now(tz = get_default_timezone())
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
                        cih_from_initiator = tradedcommodity_from_initiator.commodity
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
                        cih_from_responder = tradedcommodity_from_responder.commodity
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
            except BaseException as ex:
                # if anything crappy happens, rollback the transaction and do nothing else except logging
                logger.error("Error in accept_trace({}, {})".format(game_id, trade_id), exc_info = ex)

            return HttpResponseRedirect(reverse('trades', args = [game_id]))

    raise PermissionDenied

@login_required
def decline_trade(request, game_id, trade_id):
    if request.method == 'POST':
        trade = get_object_or_404(Trade, id = trade_id)
        if ((trade.status == 'INITIATED' and request.user == trade.responder) or
            (trade.status == 'REPLIED' and request.user == trade.initiator)):
            decline_reason_form = DeclineReasonForm(request.POST)
            if decline_reason_form.is_valid():
                trade.status = 'DECLINED'
                trade.finalizer = request.user
                trade.decline_reason = decline_reason_form.cleaned_data['decline_reason']
                trade.closing_date = datetime.datetime.now(tz = get_default_timezone())
                trade.save()
                return HttpResponseRedirect(reverse('trades', args = [game_id]))

    raise PermissionDenied

class FormInvalidException(Exception):
    def __init__(self, forms, *args, **kwargs):
        super(FormInvalidException, self).__init__(*args, **kwargs)
        self.forms = forms