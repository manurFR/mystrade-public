from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404

from game.deal import deal_cards
from game.forms import CreateGameForm, CreateTradeForm, validate_number_of_players, \
    validate_dates, RuleCardFormDisplay, RuleCardFormParse, CommodityCardFormParse, CommodityCardFormDisplay
from game.models import Game, RuleInHand, CommodityInHand, Trade, TradedCommodities
from scoring.models import RuleCard

@login_required
def welcome(request):
    games = Game.objects.filter(Q(master = request.user) | Q(players = request.user)).distinct().order_by('-end_date')
    for game in games:
        game.list_of_players = [player.get_profile().name for player in game.players.all().order_by('id')]
    return render(request, 'game/welcome.html', {'games': games})

@login_required
def hand(request, game_id):
    game = get_object_or_404(Game, id = game_id)
    rule_hand = RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = True).order_by('rulecard__ref_name')
    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user).order_by('commodity__value', 'commodity__name')
    return render(request, 'game/hand.html',
                  {'game': game, 'rule_hand': rule_hand, 'commodity_hand': commodity_hand})

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
    if 'ruleset' not in request.session or 'start_date' not in request.session \
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

    rulecards_queryset = RuleCard.objects.filter(ruleset = ruleset).order_by('ref_name')

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
                    if int(form.cleaned_data['card_id']) == card.id and form.cleaned_data['selected_rule']:
                        selected_rules.append(card)
                        break
            if len(selected_rules) > len(players):
                error = "Please select at most {} rule cards (including the mandatory ones)".format(len(players))
                RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
                formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                                       'public_name':   card.public_name,
                                                       'description':   card.description,
                                                       'mandatory':     bool(card.mandatory),
                                                       'selected_rule': bool(card in selected_rules)}
                                                            for card in rulecards_queryset])
                return render(request, 'game/rules.html', {'formset': formset, 'session': request.session, 'error': error})
            else:
                game = Game.objects.create(ruleset    = ruleset,
                                           master     = request.user,
                                           start_date = start_date,
                                           end_date   = end_date)
                for user in players:
                    game.players.add(user)
                for rule in selected_rules:
                    game.rules.add(rule)
                del request.session['ruleset']
                del request.session['start_date']
                del request.session['end_date']
                del request.session['players']
                del request.session['profiles']

                # deal starting cards
                deal_cards(game)

                return HttpResponseRedirect(reverse('welcome'))
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                               'public_name':   card.public_name,
                                               'description':   card.description,
                                               'mandatory':     bool(card.mandatory)}
                                                       for card in rulecards_queryset])
        return render(request, 'game/rules.html', {'formset': formset, 'session': request.session})

#############################################################################
##                              Trades                                     ##
#############################################################################

@login_required
def trades(request, game_id):
    game = get_object_or_404(Game, id = game_id)
    trades = Trade.objects.filter(Q(initiator = request.user) | Q(responder = request.user), game = game).order_by('-creation_date')
    return render(request, 'game/trades.html', {'game': game, 'trades': trades})

@login_required
def create_trade(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    rule_hand = RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = True).order_by('rulecard__ref_name')
    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user).order_by('commodity__value', 'commodity__name')
    if request.method == 'POST':
        RuleCardsFormSet = formset_factory(RuleCardFormParse)
        rulecards_formset = RuleCardsFormSet(request.POST, prefix = 'rulecards')
        CommodityCardsFormSet = formset_factory(CommodityCardFormParse)
        commodities_formset = CommodityCardsFormSet(request.POST, prefix = 'commodity')

        if rulecards_formset.is_valid() and commodities_formset.is_valid():
            selected_rules = []
            for card in rule_hand:
                for form in rulecards_formset:
                    if int(form.cleaned_data['card_id']) == card.rulecard.id and form.cleaned_data['selected_rule']:
                        selected_rules.append(card)
                        break
            nb_commodities = {}
            for commodity in commodity_hand:
                for form in commodities_formset:
                    if int(form.cleaned_data['commodity_id']) == commodity.commodity.id:
                        nb_commodities[commodity] = form.cleaned_data['nb_traded_cards']
                        break

            trade_form = CreateTradeForm(request.user, game, request.POST,
                                         nb_selected_rules = len(selected_rules), nb_selected_commodities = sum(nb_commodities.values()))

            if trade_form.is_valid():
                trade = Trade.objects.create(game = game, initiator = request.user,
                                             responder = trade_form.cleaned_data['responder'],
                                             comment   = trade_form.cleaned_data['comment'])
                for card in selected_rules:
                    trade.rules.add(card)
                for commodity, nb_traded_cards in nb_commodities.iteritems():
                    if nb_traded_cards > 0:
                        traded_commodities = TradedCommodities.objects.create(
                            trade = trade, commodity = commodity, nb_traded_cards = nb_traded_cards)

                return HttpResponseRedirect(reverse('trades', args = [game.id]))
            else:
                RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
                rulecards_formset = RuleCardsFormSet(initial = [{'card_id':       card.rulecard.id,
                                                                 'public_name':   card.rulecard.public_name,
                                                                 'description':   card.rulecard.description,
                                                                 'selected_rule': bool(card in selected_rules)}
                                                                for card in rule_hand],
                                                     prefix = 'rulecards')
                CommodityCardsFormSet = formset_factory(CommodityCardFormDisplay, extra = 0)
                commodities_formset = CommodityCardsFormSet(initial = [{'commodity_id':     card.commodity.id,
                                                                        'name':             card.commodity.name,
                                                                        'color':            card.commodity.color,
                                                                        'nb_cards':         card.nb_cards,
                                                                        'nb_traded_cards':  nb_commodities[card]}
                                                                       for card in commodity_hand],
                                                            prefix = 'commodity')
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        rulecards_formset = RuleCardsFormSet(initial = [{'card_id':       card.rulecard.id,
                                                         'public_name':   card.rulecard.public_name,
                                                         'description':   card.rulecard.description}
                                                        for card in rule_hand],
                                             prefix = 'rulecards')
        CommodityCardsFormSet = formset_factory(CommodityCardFormDisplay, extra = 0)
        commodities_formset = CommodityCardsFormSet(initial = [{'commodity_id':     card.commodity.id,
                                                                'name':             card.commodity.name,
                                                                'color':            card.commodity.color,
                                                                'nb_cards':         card.nb_cards,
                                                                'nb_traded_cards':  0}
                                                               for card in commodity_hand],
                                                    prefix = 'commodity')
        trade_form = CreateTradeForm(request.user, game)

    return render(request, 'game/create_trade.html', {'game': game, 'trade_form': trade_form,
                                                      'rulecards_formset': rulecards_formset,
                                                      'commodities_formset': commodities_formset})