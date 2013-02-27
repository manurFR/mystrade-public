from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404

from game.deal import deal_cards
from game.forms import CreateGameForm, validate_number_of_players, validate_dates, GameCommodityCardFormDisplay
from game.models import Game, RuleInHand, CommodityInHand, GamePlayer
from scoring.models import RuleCard
from trade.forms import RuleCardFormParse, RuleCardFormDisplay
from trade.models import Offer

@login_required
def welcome(request):
    games = Game.objects.filter(Q(master = request.user) | Q(players = request.user)).distinct().order_by('-end_date')
    for game in games:
        game.list_of_players = [player.get_profile().name for player in game.players.all().order_by('id')]
    return render(request, 'game/welcome.html', {'games': games})

@login_required
def hand(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all():
        raise PermissionDenied

    rule_hand = RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = True).order_by('rulecard__ref_name')
    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_cards__gt = 0).order_by('commodity__value', 'commodity__name')

    free_informations = []
    for offer in Offer.objects.filter(free_information__isnull = False, trade_responded__game = game,
                                      trade_responded__initiator = request.user, trade_responded__status = 'ACCEPTED'):
        free_informations.append({ 'offerer': offer.trade_responded.responder,
                                   'date': offer.trade_responded.closing_date,
                                   'free_information': offer.free_information })

    for offer in Offer.objects.filter(free_information__isnull = False, trade_initiated__game = game,
                                      trade_initiated__responder = request.user, trade_initiated__status = 'ACCEPTED'):
        free_informations.append({ 'offerer': offer.trade_initiated.responder,
                                   'date': offer.trade_initiated.closing_date,
                                   'free_information': offer.free_information })

    featured_rulecards = [rh.rulecard.id for rh in rule_hand]
    former_rules = []
    for rule in RuleInHand.objects.filter(game = game, player = request.user, abandon_date__isnull = False).order_by('rulecard__ref_name'):
        if rule.rulecard.id not in featured_rulecards: # add only rulecards that are not currently in the hand and no duplicates
            former_rules.append({ 'public_name': rule.rulecard.public_name,
                                  'description': rule.rulecard.description })
            featured_rulecards.append(rule.rulecard.id)

    return render(request, 'game/hand.html',
                  {'game': game, 'rule_hand': rule_hand, 'commodity_hand': commodity_hand, 'former_rules': former_rules,
                   'free_informations' : sorted(free_informations, key = lambda offer: offer['date'], reverse = True)})

@login_required
def submit_hand(request, game_id):
    game = get_object_or_404(Game, id = game_id)

    if request.user not in game.players.all():
        raise PermissionDenied

    commodity_hand = CommodityInHand.objects.filter(game = game, player = request.user, nb_cards__gt = 0).order_by('commodity__value', 'commodity__name')

    CommodityCardsFormSet = formset_factory(GameCommodityCardFormDisplay, extra = 0)
    commodities_formset = CommodityCardsFormSet(initial=[{'commodity_id':       card.commodity.id,
                                                          'name':               card.commodity.name,
                                                          'color':              card.commodity.color,
                                                          'nb_cards':           card.nb_cards,
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
                    if form.cleaned_data['card_id'] == card.id and form.cleaned_data['selected_rule']:
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

                return HttpResponseRedirect(reverse('welcome'))
    else:
        RuleCardsFormSet = formset_factory(RuleCardFormDisplay, extra = 0)
        formset = RuleCardsFormSet(initial = [{'card_id':       card.id,
                                               'public_name':   card.public_name,
                                               'description':   card.description,
                                               'mandatory':     bool(card.mandatory)}
                                                       for card in rulecards_queryset])
        return render(request, 'game/rules.html', {'formset': formset, 'session': request.session})